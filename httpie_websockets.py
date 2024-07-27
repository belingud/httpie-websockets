import asyncio
import io
import os
import sys
from typing import Any, AnyStr, AsyncIterable, Coroutine, Iterable, Optional

import requests
import websockets
from httpie.plugins import TransportPlugin
from requests.adapters import BaseAdapter
from requests.models import PreparedRequest, Response
from requests.structures import CaseInsensitiveDict

__version__ = "0.2.1"


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

        self._loop = asyncio.new_event_loop()
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._send_task: Optional[asyncio.Task] = None
        self._run_task: Optional[asyncio.Task] = None

        self._stdout = sys.stdout
        self._stdout_lock = asyncio.Lock()

    @property
    def running(self) -> bool:
        """Check if the adapter is running.

        Returns:
            bool: True if the adapter is running, False otherwise.
        """
        return self._running

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
                self._websocket = await websockets.connect(websocket_url)
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
                await self._write_stdout(message)
            except websockets.ConnectionClosed as e:
                await self._write_stdout(f"Connection closed with code: {e.code}, reason: {e.reason}")
                self._running = False
                await self.put(None)
                break
            except RuntimeError as e:
                # RuntimeError: If two coroutines call :meth:`recv` concurrently.
                # Another coroutine is already receiving a message
                # Should not happen since _receive is called only once.
                await self._write_stdout(str(e))
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
                        # As a command-line program, this should not happen, just in case
                        raise TypeError(
                            f"Message must be bytes, str, Iterable, or AsyncIterable, got {type(message)}"
                        )
                    await self._websocket.send(message)
            except websockets.ConnectionClosed as e:
                await self._write_stdout(f"Connection closed with code: {e.code}, reason: {e.reason}")
                self._running = False
                break
            except asyncio.CancelledError:
                break

    async def _start_receive_send(self) -> None:
        """Connect to the WebSocket, run ReceiveTask and SendTask.
        """
        self._receive_task = asyncio.create_task(self._receive())
        self._send_task = asyncio.create_task(self._send_messages())

    async def async_read_stdin(self) -> Optional[str]:
        """Read input from stdin asynchronously.

        Returns:
            Optional[str]: The input read from stdin, or None if no input is available.
        """
        if sys.stdin.closed:
            print("stdin closed??????")
            sys.stdin = os.fdopen(0, 'r')
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)
        try:
            line = await asyncio.wait_for(reader.readline(), timeout=0.5)
            return line.decode().strip() if line else None
        except asyncio.TimeoutError:
            return None
        except asyncio.CancelledError:
            return 'exit'

    async def _async_send(self) -> None:
        """Asynchronous send method to handle WebSocket communication.
        """
        await self._start_receive_send()

        while self._running:
            msg = await self.async_read_stdin()
            if not msg:
                continue
            if msg.lower() in self.EXIT_KEY_WORDS:
                break
            assert self._running, f"Websocket closed, message {msg} not sent"
            await self.put(msg)

    async def async_send(self, request: PreparedRequest) -> Response:
        """Asynchronous send method to handle WebSocket communication.

        Args:
            request (PreparedRequest): The request to send.

        Returns:
            Response: The response details from the WebSocket.
        """
        try:
            await self._connect(request.url)
        except AdapterError as e:
            self.close()
            return self.dummy_response(request, e.code, e.msg)
        self._running = True
        await self._write_stdout(f"> {request.url}")
        await self._write_stdout("Type a message and press enter to send it")
        await self._write_stdout(
            f"Type {', '.join(repr(i) for i in self.EXIT_KEY_WORDS)} or press Ctrl+C to close the connection"
        )

        await self._async_send()

    def run_coro(self, coro: Coroutine) -> Any:
        """Run a coroutine and return the result.
        If coro is not a coroutine, it is returned as is.

        Args:
            coro (Coroutine): The coroutine to run.
        """
        if not isinstance(coro, Coroutine):
            return coro
        return self._loop.run_until_complete(coro)

    def send(self, request: PreparedRequest, **kwargs) -> Response:
        """Send a request to the WebSocket.

        Args:
            request (PreparedRequest): The request to send.

        Returns:
            Response: The response details from the WebSocket.
        """
        try:
            self.run_coro(self.async_send(request))
        except KeyboardInterrupt:
            self.run_coro(self._write_stdout(
                "\nKeyboardInterrupt received. Cleaning up, press Ctrl+C again to exit force."
            ))
            self.run_coro(self.put(None))
        finally:
            self.close()
        return self.dummy_response(request)

    async def _write_stdout(self, msg: AnyStr) -> None:
        """Write message to stdout.

        Args:
            msg (AnyStr): The message to write.
        """
        if not self._running:
            return
        async with self._stdout_lock:
            self._stdout.write(msg)
            self._stdout.write("\n")
            self._stdout.flush()

    def dummy_response(
        self, request: PreparedRequest, status_code: int = 200, msg: str = ""
    ) -> Response:
        """Create a dummy response for requests send method.

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
        self._running = False
        try:
            self.run_coro(self._close())
        except Exception:  # noqa
            pass

    async def _close(self) -> None:
        """Close the WebSocket connection."""
        self._running = False
        if self._websocket and self._websocket.open:
            try:
                self._websocket.close_timeout = 1
                await self._websocket.close(code=1000, reason="Closed by user")
            except Exception:  # noqa
                pass
        for task in asyncio.all_tasks():
            if not task.done():
                try:
                    task.cancel()
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
