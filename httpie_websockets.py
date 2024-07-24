import asyncio
import io
import select
import sys
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import AnyStr, AsyncIterable, Iterable, Optional

import requests
import websockets
from httpie.plugins import TransportPlugin
from requests.adapters import BaseAdapter
from requests.models import PreparedRequest, Response
from requests.structures import CaseInsensitiveDict

warnings.simplefilter("ignore", category=RuntimeWarning)
__version__ = "0.2.0"


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
            target=self.start_loop, args=(self._ws_loop,), name="WSThread"
        )
        self._loop_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="WSAdapter")
        self._ws_loop.set_default_executor(self._loop_executor)

        # std
        self._stdout = sys.stdout
        self._stdout_lock = threading.Lock()

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
                self._write_stdout(
                    f"Connection closed with code: {e.code}, reason: {e.reason}\n"
                    f"Cleaning, press Ctrl+C again to exit force."
                )
                self._running = False
                await self.put(None)
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
                if message is None:
                    self._running = False
                    break
                if message:
                    if not isinstance(message, (bytes, str, Iterable, AsyncIterable)):
                        raise TypeError(
                            f"Message must be bytes, str, Iterable, or AsyncIterable, got {type(message)}"
                        )
                    await self._websocket.send(message)
            except websockets.exceptions.ConnectionClosed as e:
                self._write_stdout(f"Connection closed with code: {e.code}, reason: {e.reason}")
                self._running = False
                break
            except asyncio.CancelledError:
                break

    async def _run(self, websocket_url: str):
        """
        Connect to the websocket, run ReceiveTask and SendTask
        Args:
            websocket_url:
        """
        await self._connect(websocket_url)
        self._receive_task = asyncio.create_task(self._receive())
        self._send_task = asyncio.create_task(self._send_messages())
        try:
            await asyncio.gather(self._receive_task, self._send_task)
        except Exception:  # noqa
            pass

    def read_stdin(self) -> Optional[str]:
        """
        Read input from stdin
        Returns: striped str

        """
        r, w, e = select.select([sys.stdin], [], [], 0.5)
        if not r:
            return
        return sys.stdin.readline().strip()

    def send(self, request, **kwargs):
        websocket_url = request.url
        self._ws_thread.start()
        try:
            asyncio.run_coroutine_threadsafe(self._connect(websocket_url), self._ws_loop).result()
        except OSError:
            self.close()
            return self.dummy_response(request, 500, "Cannot connect to server")
        self._running = True
        self._write_stdout(f"> {websocket_url}")
        self._write_stdout("Type a message and press enter to send it")
        self._write_stdout("Type 'exit' to close the connection")

        try:
            self._run_task = self._run(websocket_url)
            asyncio.run_coroutine_threadsafe(self._run_task, self._ws_loop)

            # Read input messages and put them in the queue
            while self._running:
                msg = self.read_stdin()
                if not msg:
                    continue
                if msg.lower() == "exit":
                    break
                asyncio.run_coroutine_threadsafe(self.put(msg), self._ws_loop).result()
        except KeyboardInterrupt:
            self._write_stdout(
                "\nKeyboardInterrupt received. Cleaning up, press Ctrl+C again to exit force."
            )
            # ensure send message task quits
            asyncio.run_coroutine_threadsafe(self.put(None), self._ws_loop).result()
        finally:
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
        with self._stdout_lock:
            self._stdout.write(msg)
            self._stdout.write("\n")
            self._stdout.flush()

    def dummy_response(
        self, request: PreparedRequest, status_code: int = 200, msg: str = ""
    ) -> Response:
        """
        Create a dummy response for requests send method
        Args:
            request:
            status_code(int):
            msg(str): Message to show on stdout

        Returns: requests.Response
        """
        r = Response()
        r.status_code = status_code
        r.request = request
        close_code = self._websocket.close_code if self._websocket else 1000
        reason = self._websocket.close_reason if self._websocket else msg
        headers = CaseInsensitiveDict(self._websocket.response_headers) if self._websocket else CaseInsensitiveDict({})
        r.headers = headers
        r._content = r.reason = reason
        r.raw = io.BytesIO(
            msg.encode("utf-8")
            if msg
            else f"""Close Code: {close_code}\nReason: {reason}""".encode("utf-8")
        )
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
        except Exception:  # noqa
            pass

    async def _close(self):
        if self._websocket and self._websocket.open:
            await self._websocket.close(code=1000, reason="Closed by user")
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
    session = requests.Session()
    session.mount("ws://", adapter)
    session.mount("wss://", adapter)
    session.request("WEBSOKET", args.url)
    session.close()
