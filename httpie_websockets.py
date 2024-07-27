import asyncio
import io
import platform
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import AnyStr, AsyncIterable, Iterable, Optional

import requests
import websockets
from httpie.plugins import TransportPlugin
from requests.adapters import BaseAdapter
from requests.models import PreparedRequest, Response
from requests.structures import CaseInsensitiveDict

__version__ = "0.3.0"
IS_WINDOWS = platform.system().lower() == "windows"
if IS_WINDOWS:
    import msvcrt

    def _read_stdin():
        if msvcrt.kbhit():
            input_buffer = ""
            while True:
                char = msvcrt.getwche()
                if char == "\r":  # Enter key
                    print()
                    break
                input_buffer += char
            return input_buffer.strip()
        return None
else:
    import select

    def _read_stdin():
        r, _, _ = select.select([sys.stdin], [], [], 1)
        if sys.stdin in r:
            return sys.stdin.readline().strip()
        return None


class AdapterError(Exception):
    """Custom exception for adapter errors."""

    def __init__(self, code: int, msg: str) -> None:
        """Initialize the AdapterError exception.

        Args:
            code (int): The error code.
            msg (str): The error message.
        """
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        """Return the string representation of the exception.

        Returns:
            str: The error code and message.
        """
        return f"{self.code}: {self.msg}"


class WebsocketAdapter(BaseAdapter):
    """Adapter for handling WebSocket connections."""

    EXIT_KEY_WORDS = ("exit", "quit")

    def __init__(self, queue_size: int = 1024):
        """Initialize the WebsocketAdapter.

        Args:
            queue_size (int): The size of the message queue.
        """
        super().__init__()
        self._msg_queue = asyncio.Queue(queue_size)
        self._running = False

        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        # tasks
        self._receive_task: Optional[asyncio.Task] = None
        self._send_task: Optional[asyncio.Task] = None

        # websocket loop
        self._ws_loop = asyncio.new_event_loop()
        self._ws_thread = threading.Thread(
            target=self.start_loop, args=(self._ws_loop,), name="WSThread"
        )
        # websocket connection is running in an executor
        self._ws_loop.set_default_executor(ThreadPoolExecutor(max_workers=5, thread_name_prefix="WSAdapter"))

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

    async def _connect(self, websocket_url: str) -> None:
        """
        Connect to the websocket if not already connected
        Args:
            websocket_url(str): the url of the websocket
        Raises:
            AdapterError: if the connection fails, raise AdapterError with code and msg
        """
        if not self._websocket or not self._websocket.open:
            try:
                self._websocket = await websockets.connect(websocket_url, close_timeout=4)
            except OSError:
                # Connect failed
                raise AdapterError(500, "Cannot connect to websocket") from None
            except websockets.InvalidStatusCode as e:
                # Exceptions with status_code and custom msg
                raise AdapterError(e.status_code, str(e)) from None
            except websockets.AbortHandshake as e:
                # Exceptions with status and body
                raise AdapterError(e.status, e.body.decode()) from None
            except (websockets.InvalidHandshake, websockets.InvalidURI) as e:
                # Exceptions without status_code
                raise AdapterError(500, str(e)) from None
            except asyncio.TimeoutError:
                # Connection timed out
                raise AdapterError(500, "Connection timed out") from None

    async def _receive(self):
        """
        Receive messages from the websocket
        """
        while self._running:
            try:
                message = await self._websocket.recv()
                self._write_stdout(message)
            except websockets.ConnectionClosed as e:
                self._write_stdout(f"Connection closed with code: {e.code}, reason: {e.reason}")
                await self.put(None)
                break
            except RuntimeError as e:
                # RuntimeError: If two coroutines call :meth:`recv` concurrently.
                # Another coroutine is already receiving a message
                # Should not happen since _receive is called only once.
                self._write_stdout(str(e))
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
                    break
                if message:
                    if not isinstance(message, (bytes, str, Iterable, AsyncIterable)):
                        # As a command-line program, this should not happen, just in case
                        raise TypeError(
                            f"Message must be bytes, str, Iterable, or AsyncIterable, got {type(message)}"
                        )
                    await self._websocket.send(message)
            except websockets.ConnectionClosed as e:
                self._write_stdout(f"Connection closed with code: {e.code}, reason: {e.reason}")
                break
            except asyncio.CancelledError:
                break

    async def _run_tasks(self):
        self._receive_task = asyncio.create_task(self._receive(), name="_receive_task")
        self._send_task = asyncio.create_task(self._send_messages(), name="_send_task")
        try:
            await asyncio.gather(self._receive_task, self._send_task)
        except Exception: # noqa
            # No stdout
            pass

    def read_stdin(self) -> Optional[str]:
        """Read input from stdin synchronously.

        Returns:
            Optional[str]: The input read from stdin, or None if no input is available.
        """
        if not self._running:
            return None
        return _read_stdin()

    def send(self, request, **kwargs):
        """Send a request to the WebSocket.

        Args:
            request (PreparedRequest): The request to send.

        Returns:
            Response: The response details from the WebSocket.
        """
        websocket_url = request.url
        self._ws_thread.start()
        try:
            asyncio.run_coroutine_threadsafe(self._connect(websocket_url), self._ws_loop).result()
        except AdapterError as e:
            self.close()
            return self.dummy_response(request, e.code, e.msg)
        self._running = True
        self._write_stdout(f"> {websocket_url}")
        self._write_stdout("Type a message and press enter to send it")
        self._write_stdout(
            f"Type {', '.join(repr(i) for i in self.EXIT_KEY_WORDS)} or press Ctrl+C to close the connection"
        )

        try:
            asyncio.run_coroutine_threadsafe(self._run_tasks(), self._ws_loop)

            # Read input messages and put them in the queue
            while self._running:
                msg = self.read_stdin()
                if not msg:
                    continue
                if msg.lower() in self.EXIT_KEY_WORDS:
                    break
                if not self._running:
                    self._write_stdout(f"Websocket closed, message {msg} not sent")
                    break
                asyncio.run_coroutine_threadsafe(self.put(msg), self._ws_loop).result()
        except KeyboardInterrupt:
            self._write_stdout(
                "\nKeyboardInterrupt received. Cleaning up, press Ctrl+C again to exit force."
            )
            # Ensure send message task quits
            asyncio.run_coroutine_threadsafe(self.put(None), self._ws_loop).result()
        finally:
            self.close()
        return self.dummy_response(request)

    def _write_stdout(self, msg: AnyStr):
        """
        Write message to stdout
        Args:
            msg (AnyStr): The message to write.
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
            request (PreparedRequest): The request to respond to.
            status_code (int): The status code of the response.
            msg (str): The message to include in the response.

        Returns:
            Response: The dummy response.
        """
        r = Response()
        r.status_code = status_code
        r.request = request
        close_code = self._websocket.close_code if self._websocket else 1000
        reason = self._websocket.close_reason if self._websocket else msg
        headers = (
            CaseInsensitiveDict(self._websocket.response_headers)
            if self._websocket
            else CaseInsensitiveDict({})
        )
        r.headers = headers
        r._content = r.reason = reason
        r.raw = io.BytesIO(
            msg.encode("utf-8")
            if msg
            else f"""Close Code: {close_code}\nReason: {reason}""".encode("utf-8")
        )
        r.url = request.url
        return r

    def close(self) -> None:
        """Close the WebSocket connection and clean up resources."""
        if self._running is False:
            return
        self._running = False
        try:
            asyncio.run_coroutine_threadsafe(self._close(), self._ws_loop).result()
        except Exception:  # noqa
            # No stacktrace in stdout
            pass
        finally:
            self._ws_loop.call_soon_threadsafe(self._ws_loop.stop)
            self._ws_thread.join()
            self._ws_loop.close()

    async def _close(self):
        if self._websocket and self._websocket.open:
            await self._websocket.close(code=1000, reason="Closed by user")
            await self._websocket.wait_closed()
        for task in asyncio.all_tasks(self._ws_loop):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    async def put(self, msg: Optional[AnyStr]) -> None:
        """Put a message into the message queue.

        Args:
            msg (Optional[AnyStr]): The message to put into the queue.
        """
        await self._msg_queue.put(msg)


class BaseWebsocketPlugin(TransportPlugin):
    """Base class for WebSocket transport plugins."""

    package_name = "httpie_websockets"
    description = "WebSocket transport plugin for HTTPie"

    def get_adapter(self) -> WebsocketAdapter:
        """Get the WebSocket adapter.

        Returns:
            WebsocketAdapter: The WebSocket adapter.
        """
        return WebsocketAdapter()


class WebsocketPlugin(BaseWebsocketPlugin):
    """Plugin for handling WebSocket connections over HTTP."""

    name = "websocket"
    prefix = "ws://"


class WebsocketSPlugin(BaseWebsocketPlugin):
    """Plugin for handling secure WebSocket connections over HTTPS."""

    name = "websocket-s"
    prefix = "wss://"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(prog="python -m httpie_websocket")
    parser.add_argument("url")
    args = parser.parse_args()

    adapter = WebsocketAdapter()
    session = requests.Session()
    session.mount("ws://", adapter)
    session.mount("wss://", adapter)
    session.request("WEBSOCKET", args.url)
    session.close()
