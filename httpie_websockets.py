import asyncio
import sys
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import AnyStr, AsyncIterable, Iterable, Optional

import requests
import websockets
from httpie.plugins import TransportPlugin
from requests.adapters import BaseAdapter
from requests.models import Request, Response

warnings.simplefilter("ignore", category=RuntimeWarning)
__version__ = "0.0.2"


class WebsocketAdapter(BaseAdapter):
    def __init__(self, queue_size: int = 1024):
        super().__init__()
        self._msg_queue = asyncio.Queue(queue_size)
        self._running = False
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        # tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._send_task: Optional[asyncio.Task] = None
        self._run_task: Optional[asyncio.Task] = None

        # websocket loop
        self._ws_loop = asyncio.new_event_loop()
        self._ws_thread = threading.Thread(
            target=self.start_loop, args=(self._ws_loop,), name="LoopThread"
        )
        self._loop_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="WSAdapter")
        self._ws_loop.set_default_executor(self._loop_executor)

        # std
        self._stdout = sys.stdout
        self._std_lock = threading.Lock()

    @property
    def running(self):
        return self._running

    def start_loop(self, thread_loop):
        """
        Start the loop in a separate thread
        Args:
            thread_loop: asyncio event loop
        """
        asyncio.set_event_loop(thread_loop)
        thread_loop.run_forever()

    async def _connect(self, websocket_url: str):
        """
        Connect to the websocket if not already connected
        Args:
            websocket_url(str): the url of the websocket
        """
        if not self._websocket or not self._websocket.open:
            self._websocket = await websockets.connect(websocket_url)

    async def _receive(self):
        """
        Receive messages from the websocket
        """
        while self._running:
            try:
                message = await self._websocket.recv()
                self._write_stdout(message)
            except websockets.exceptions.ConnectionClosed as e:
                self._write_stdout(f"Connection closed with code: {e.code}, reason: {e.reason}")
                break
            except asyncio.CancelledError:
                break

    async def _send_messages(self):
        """
        Send messages to the websocket
        """
        while self._running:
            try:
                message = await self._msg_queue.get()
                if message:
                    if not isinstance(message, (bytes, str, Iterable, AsyncIterable)):
                        raise TypeError(
                            f"Message must be bytes, str, Iterable, or AsyncIterable, got {type(message)}"
                        )
                    await self._websocket.send(message)
            except websockets.exceptions.ConnectionClosed:
                self._write_stdout(f"Connection closed with code: {e.code}, reason: {e.reason}")
                break
            except asyncio.CancelledError:
                break

    async def _run(self, websocket_url: str):
        await self._connect(websocket_url)
        self._receive_task = asyncio.create_task(self._receive())
        self._receive_task.set_name("ReceiveTask")
        self._send_task = asyncio.create_task(self._send_messages())
        self._send_task.set_name("SendTask")
        await asyncio.gather(self._receive_task, self._send_task, return_exceptions=True)

    def send(self, request, **kwargs):
        self._running = True
        websocket_url = request.url
        self._write_stdout(f"> {websocket_url}")
        self._write_stdout("Type a message and press enter to send it")
        self._write_stdout("Type 'exit' to close the connection")

        try:
            self._ws_thread.start()
            self._run_task = self._run(websocket_url)
            asyncio.run_coroutine_threadsafe(self._run_task, self._ws_loop)
            while True:
                msg = input()
                if msg.lower() == "exit":
                    break
                asyncio.run_coroutine_threadsafe(self.put(msg), self._ws_loop).result()
        except KeyboardInterrupt:
            self._write_stdout("\nKeyboardInterrupt received. Closing connection...")
            self.close()
        return self.dummy_response(request)

    def _write_stdout(self, msg: AnyStr):
        """
        Write message to stdout
        Args:
            msg:
        """
        if not self._running:
            return
        with self._std_lock:
            self._stdout.write(msg)
            self._stdout.write("\n")
            self._stdout.flush()

    def dummy_response(self, request: Request) -> Response:
        """
        Create a dummy response for requests send method
        Args:
            request:

        Returns: requests.Response
        """
        r = Response()
        r.status_code = 200
        r._content = b""
        r.request = request
        r.url = request.url
        return r

    def close(self):
        self._running = False
        try:
            asyncio.run_coroutine_threadsafe(self._close(), self._ws_loop).result()
            self._ws_loop.call_soon_threadsafe(self._ws_loop.stop)
            self._ws_thread.join()
            self._loop_executor.shutdown(wait=False)
            self._ws_loop.close()
        except (Exception, KeyboardInterrupt):
            pass

    async def _close(self):
        if self._websocket and self._websocket.open:
            await self._websocket.close()
        await self.cancel_all_tasks()

    async def cancel_all_tasks(self):
        for task in asyncio.all_tasks(self._ws_loop):
            if not task.done():
                try:
                    task.cancel()
                    await task
                except asyncio.CancelledError:
                    pass

    async def put(self, msg):
        await self._msg_queue.put(msg)


class WebsocketPlugin(TransportPlugin):
    name = "websocket"
    package_name = "httpie_websockets"
    prefix = "ws://"
    description = "WebSocket transport plugin for HTTPie"

    def get_adapter(self):
        return WebsocketAdapter()


class WebsocketSPlugin(TransportPlugin):
    package_name = "httpie_websockets"
    name = "websocket-s"
    prefix = "wss://"
    description = "Secure WebSocket transport plugin for HTTPie"

    def get_adapter(self):
        return WebsocketAdapter()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="python -m httpie_websocket")
    parser.add_argument("url")
    args = parser.parse_args()

    adapter = WebsocketAdapter()
    with requests.Session() as session:
        session.mount("ws://", adapter)
        session.mount("wss://", adapter)
        session.request("WEBSOKET", args.url)
