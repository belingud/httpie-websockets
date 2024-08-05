import io
import platform
import queue
import sys
import threading
from concurrent.futures import CancelledError, ThreadPoolExecutor
from typing import AnyStr, AsyncIterable, Iterable, Optional

from httpie.plugins import TransportPlugin
from requests.adapters import BaseAdapter
from requests.models import PreparedRequest, Response
from requests.structures import CaseInsensitiveDict
from websockets.exceptions import (
    AbortHandshake,
    ConnectionClosed,
    InvalidHandshake,
    InvalidStatusCode,
    InvalidURI,
)
from websockets.protocol import State
from websockets.sync.client import ClientConnection, connect

__version__ = "0.4.0"
__author__ = "belingud"
__license__ = "MIT"
if platform.system().lower() == "windows":
    import msvcrt

    def _read_stdin():
        """Read input for Windows"""
        if msvcrt.kbhit():
            input_buffer = ""
            while True:
                char = msvcrt.getwche()
                if char == "\r":  # Enter key
                    print(file=sys.stdout)
                    break
                input_buffer += char
            return input_buffer.strip()
        return None
else:
    import select

    def _read_stdin():
        """Read input for Linux"""
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

    def __init__(self, queue_size: int = 1024):
        """Initialize the WebsocketAdapter.

        Args:
            queue_size (int, optional): The size of the queue. Defaults to 1024.
        """
        super().__init__()
        self._input_qsize = queue_size
        self._input_queue = queue.Queue(self._input_qsize)

        self._running = False
        self._ws_client: Optional[ClientConnection] = None

        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="WSAdapter")

        # stdout
        self._stdout = sys.stdout
        self._stdout_lock = threading.Lock()

    @property
    def connected(self) -> bool:
        """Check if the websocket is open"""
        return self._ws_client is not None and self._ws_client.protocol.state in (State.OPEN,)

    def _connect(self, url, **kwargs):
        """Connect to the WebSocket server.

        Args:
            url (str): The URL of the WebSocket server.
            **kwargs: Additional keyword arguments to pass to the WebSocket client.
        """
        try:
            self._ws_client = connect(url, close_timeout=4, **kwargs)
        except TimeoutError:
            # Connection timed out
            raise AdapterError(500, "Connection timed out") from None
        except OSError:
            # Connect failed
            raise AdapterError(500, "Cannot connect to websocket") from None
        except InvalidStatusCode as e:
            # Exceptions with status_code and custom msg
            raise AdapterError(e.status_code, str(e)) from None
        except AbortHandshake as e:
            # Exceptions with status and body
            raise AdapterError(e.status, e.body.decode()) from None
        except (InvalidHandshake, InvalidURI) as e:
            # Exceptions without status_code
            raise AdapterError(500, str(e)) from None

    def _listening(self):
        """
        Receive messages from the websocket
        """
        while self._running and self.connected:
            try:
                msg = self._ws_client.recv()
                self._write_stdout(msg)
            except TimeoutError:
                continue
            except EOFError:
                break
            except ConnectionClosed as e:
                self._write_stdout(
                    f"Connection closed when listening with code: {e.code}, reason: {e.reason}"
                )
                self.put(None)
                break
            except RuntimeError as e:
                print('RuntimeError: If two coroutines call :meth:`recv` concurrently.')
                self._write_stdout(f"Another WS receiver is already running: {e}")
                self.put(None)
                break
            except CancelledError:
                break
            except Exception as e:
                self._write_stdout(f"Unexpected error while listening: {e}")
                self.put(None)
                break

    def _sending(self):
        """
        Send messages to the websocket
        """
        while self._running and self.connected:
            try:
                msg = self._input_queue.get(timeout=1)
                if msg is None:
                    break
                if msg:
                    if not isinstance(msg, (bytes, str, Iterable, AsyncIterable)):
                        # As a command-line program, this should not happen, just in case
                        raise TypeError(
                            f"Message must be bytes, str, Iterable, or AsyncIterable, got {type(msg)}"
                        )
                    self._ws_client.send(msg)
            except queue.Empty:
                continue
            except TimeoutError:
                continue
            except EOFError:
                break
            except ConnectionClosed as e:
                # RuntimeError: If two coroutines call :meth:`recv` concurrently.
                # Another coroutine is already receiving a message
                # Should not happen since _receive is called only once.
                self._write_stdout(
                    f"Connection closed when sending with code: {e.code}, reason: {e.reason}"
                )
                break
            except CancelledError:
                break
            except Exception as e:
                self._write_stdout(f"Unexpected error when sending: {e}")
                break

    def read_stdin(self) -> Optional[str]:
        """Read input from stdin synchronously.

        Returns:
            Optional[str]: The input read from stdin, or None if no input is available.
        """
        if not self._running:
            return None
        return _read_stdin()

    def send(
        self,
        request: PreparedRequest,
        stream=False,
        timeout=None,
        verify=True,
        cert=None,
        proxies=None,
    ) -> Response:
        """Send a request to the WebSocket.

        Args:
            request (PreparedRequest): The request to send.
            stream:
            timeout:
            verify:
            cert:
            proxies:

        Returns:
            Response: The response details from the WebSocket.
        """
        try:
            # Establish websocket connection
            self._connect(request.url)
        except AdapterError as e:
            self.close()
            return self.dummy_response(request, e.code, e.msg)

        self._running = True
        self._executor.submit(self._listening)
        self._executor.submit(self._sending)
        self._write_stdout(
            f"> Connected to {request.url}\n"
            "Type a message and press enter to send it\n"
            "Press Ctrl+C to close the connection"
        )
        try:
            # Read input messages and put them in the queue
            while self._running and self.connected:
                msg = self.read_stdin()
                if not msg:
                    continue
                if not self._running or not self.connected:
                    self._write_stdout(f"Websocket closed, message {msg} not sent")
                    break
                self.put(msg)
        except KeyboardInterrupt:
            self._write_stdout(
                "KeyboardInterrupt received. Cleaning up, press Ctrl+C again to exit force."
            )
            self.put(None)
        finally:
            self.close()
        return self.dummy_response(request)

    def dummy_response(self, request, status_code: int = 200, msg: str = ""):
        r = Response()
        r.status_code = status_code
        r.request = request
        close_code = self._ws_client.protocol.close_code if self._ws_client else 1000
        reason = self._ws_client.protocol.close_reason if self._ws_client else msg
        headers = (
            CaseInsensitiveDict(self._ws_client.response.headers)
            if self._ws_client
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

    def _write_stdout(self, msg: AnyStr, newline: bool = True) -> None:
        """
        Write a message to stdout.
        Args:
            msg(AnyStr): The message to write.
            newline(bool): Whether to add a newline character at the end of the message.
        """
        if not isinstance(msg, (str, bytes)):
            msg = str(msg)
        if not msg:
            return
        with self._stdout_lock:
            self._stdout.write(msg)
            newline and self._stdout.write("\n")
            self._stdout.flush()

    def put(self, msg: Optional[AnyStr]) -> None:
        """Put a message into the message queue.

        Args:
            msg (Optional[AnyStr]): The message to put into the queue.
        """
        if not self._running:
            return
        self._input_queue.put(msg)

    def close(self):
        if self._running is False:
            return
        self._running = False
        if self._ws_client:
            self._ws_client.close(code=1000, reason="Closed by user")
        self._executor.shutdown(cancel_futures=True)
        # clear queue
        waiting_msgs = []
        while True:
            try:
                waiting = self._input_queue.get_nowait()
                if waiting is not None:
                    waiting_msgs.append(waiting)
            except queue.Empty:
                break
        if waiting_msgs:
            self._write_stdout(f"Dropped messages: {tuple(waiting_msgs)}")


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

    import requests

    parser = argparse.ArgumentParser(prog="python -m httpie_websocket")
    parser.add_argument("url")
    parser.add_argument(
        "-v", "--version", action="version", version=f"httpie-websocket version: {__version__}"
    )
    args = parser.parse_args()

    adapter = WebsocketAdapter()
    session = requests.Session()
    session.mount("ws://", adapter)
    session.mount("wss://", adapter)
    resp = session.request("WEBSOCKET", args.url)
    session.close()
