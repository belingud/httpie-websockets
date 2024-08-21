import io
import json
import logging
import os
import platform
import ssl
import struct
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Mapping, Optional, TextIO, Union
from urllib.parse import ParseResult, urlparse

import websocket
from httpie.client import DEFAULT_UA
from httpie.plugins import TransportPlugin
from httpie.ssl_ import HTTPieCertificate
from requests.adapters import BaseAdapter
from requests.models import PreparedRequest, Response
from requests.structures import CaseInsensitiveDict
from websocket import ABNF, STATUS_ABNORMAL_CLOSED

__version__ = "0.5.2"
__author__ = "belingud"
__license__ = "MIT"

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(filename)s:%(lineno)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger.setLevel(os.getenv("HTTPIE_WS_LOG_LEVEL", "WARNING").upper())

try:
    import python_socks  # noqa: F401
except ImportError:
    logger.debug("pyton-socks not installed, websocket proxy will not work")

if platform.system().lower() == "windows":
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


def normalize_url(url, default_scheme="http") -> ParseResult:
    """
    Normalize a URL by adding `http` as default if it's missing.
    Supported schemes: http, socks4, socks4a, socks5, socks5h
    Examples:
        'example.com' -> 'http://example.com'
        '//example.com' -> 'http://example.com'
        '://example.com' -> 'http://example.com'
        'http://example.com' -> 'http://example.com'
        'socks5://example.com' -> 'socks5://example.com'
        'https://example.com' -> 'https://example.com'

    Args:
        url (str): The URL to normalize.
        default_scheme (str, optional): The default scheme to use if the URL doesn't have one. Defaults to "http".

    Returns:
        ParseResult: The parsed URL.
    """
    if "." not in url:
        try:
            url.index("localhost")
        except ValueError:
            return urlparse("")
    if url.startswith("://"):
        url = f"{default_scheme}{url}"
    elif url.startswith("//"):
        url = f"{default_scheme}:{url}"
    elif not url.startswith(
        ("http://", "https://", "socks4://", "socks4a://", "socks5://", "socks5h://")
    ):
        url = f"{default_scheme}://{url}"

    parsed_url = urlparse(url)

    if not parsed_url.scheme or not parsed_url.netloc:
        return urlparse("")

    return parsed_url


class AdapterError(Exception):
    """Custom exception for adapter errors."""

    def __init__(self, code: int, msg: str) -> None:
        self.code = code
        self.msg = msg

    def __str__(self) -> str:
        return f"{self.code}: {self.msg}"


class WSThread(threading.Thread):
    def stop(self):
        """Force stop a sub-thread."""
        self._tstate_lock.release()
        self._stop()


class WebsocketAdapter(BaseAdapter):
    """Adapter for handling WebSocket connections."""

    __slots__ = ("_running", "_ws", "_ws_thread", "_stdout", "_stdout_lock", "_msgs_bytes")

    ACTIVELY_CLOSE_REASON: bytes = b"KeyboardInterrupt"

    def __init__(self):
        super().__init__()
        self._running = False

        self._ws: Optional[websocket.WebSocket] = None
        self._ws_thread: WSThread = WSThread(target=self._run, name="WSThread")
        self._ws_thread.daemon = True

        self._stdout: TextIO = sys.stdout
        self._stdout_lock: threading.Lock = threading.Lock()

        # ws info
        self._close_code: Optional[int] = None
        self._close_msg: Optional[str] = None

        # store messages in bytes for download, httpie `--download` option
        self._msgs_bytes: tempfile.TemporaryFile
        if sys.version_info >= (3, 12):
            self._msgs_bytes: tempfile.TemporaryFile = tempfile.NamedTemporaryFile(
                mode="w+b", delete=True, delete_on_close=True
            )
        else:
            self._msgs_bytes: tempfile.TemporaryFile = tempfile.NamedTemporaryFile(
                mode="w+b", delete=True
            )

    @property
    def connected(self) -> bool:
        return bool(self._ws and self._ws.connected)

    @property
    def close_code(self) -> int:
        return self._close_code or 0

    @property
    def close_msg(self) -> str:
        return self._close_msg or ""

    def convert2ws_headers(self, headers: Mapping) -> list[str]:
        """Convert HTTP headers to WebSocket headers.

        Args:
            headers (Mapping): HTTP headers.

        Returns:
            list[str]: WebSocket headers.
        """
        if not headers:
            return []
        headers = dict(headers)
        ws_headers = []

        # Below headers already generated by websocket in handshake => _get_handshake_headers
        # https://github.com/websocket-client/websocket-client/blob/master/websocket/_handshake.py#L83
        ignore_keys = [
            "upgrade",
            "connection",
            "origin",
            "host",
            "sec-websocket-key",
            "sec-websocket-version",
        ]
        has_ua = False
        for k, v in headers.items():
            if k.lower() == "user-agent":
                has_ua = True
            if k.lower() in ignore_keys:
                continue
            if isinstance(v, bytes):
                v = v.decode("utf-8")
            ws_headers.append(f"{k}: {v}")
        if not has_ua:
            ws_headers.append(f"User-Agent: {headers.get('User-Agent', DEFAULT_UA)}")
        return ws_headers

    def _connect(self, request: PreparedRequest, **kwargs) -> None:
        """Connect to the WebSocket if not already connected.

        Args:
            request (PreparedRequest): The request object.
            **kwargs: Additional keyword arguments.
        """
        if self.connected:
            return
        options: dict[str, Any] = {}

        proxy = kwargs.get("proxies")
        if proxy:
            ignored = []
            proxy_url = None
            for idx, (_, host_port) in enumerate(proxy.items()):
                proxy_url = normalize_url(url=host_port, default_scheme="http")
                if idx > 0:
                    ignored.append(proxy_url.geturl())
                    continue
                options["http_proxy_host"] = proxy_url.hostname
                options["http_proxy_port"] = proxy_url.port
                options["proxy_type"] = proxy_url.scheme
            if ignored:
                msg = "\033[93mWarning: "
                if proxy_url:
                    msg += f"Using proxy {proxy_url.geturl()}. "
                ignored = {i.decode("utf-8") if isinstance(i, bytes) else i for i in ignored}
                msg += f"Proxy {', '.join(ignored)} is ignored because multiple proxies are not supported.\033[0m"
                self._write_stdout(msg)

        # --verify=yes/no
        verify = kwargs.get("verify", True)
        # IMPORTANT: httpie plugin not support specify ssl version and ciphers
        cert: Optional[Union[HTTPieCertificate, str]] = kwargs.get("cert")
        if not verify:
            options["sslopt"] = {"cert_reqs": ssl.CERT_NONE}
            if cert:
                self._write_stdout(
                    "\033[93mWarning: --cert is ignored because --verify is disabled.\033[0m"
                )
        else:
            if isinstance(cert, HTTPieCertificate):
                if cert.key_file:
                    options["keyfile"] = Path(str(cert.key_file)).expanduser().resolve().as_posix()
                if cert.key_file:
                    options["certfile"] = (
                        Path(str(cert.cert_file)).expanduser().resolve().as_posix()
                    )
                if cert.key_password:
                    options["password"] = cert.key_password
            elif isinstance(cert, str):
                options["sslopt"] = {
                    "cert_reqs": ssl.CERT_REQUIRED,
                    "ca_certs": Path(cert).expanduser().resolve().as_posix(),
                }
        try:
            self._ws: websocket.WebSocket = websocket.WebSocket(sslopt=options.get("sslopt"))
            self._ws.connect(
                request.url,
                header=self.convert2ws_headers(request.headers),
                timeout=kwargs.get("timeout", 3),
                redirect_limit=30,  # HTTPie default
                http_proxy_host=options.get("http_proxy_host"),
                http_proxy_port=options.get("http_proxy_port"),
                proxy_type=options.get("proxy_type"),
                keyfile=options.get("keyfile"),
                certfile=options.get("certfile"),
                password=options.get("password"),
            )
        except (websocket.WebSocketException, OSError) as e:
            raise AdapterError(500, f"Cannot connect to websocket: {str(e)}") from None

    def _receive(self):
        """Receive messages from the WebSocket."""
        while self._running and self.connected:
            try:
                resp_opcode, msg = self._ws.recv_data()
                if resp_opcode == ABNF.OPCODE_CLOSE and len(msg) >= 2:
                    # received a close message
                    self._close_code = struct.unpack("!H", msg[0:2])[0]
                    self._close_msg = msg[2:]
                    if isinstance(self._close_msg, bytes):
                        self._close_msg = self._close_msg.decode(encoding="utf8")
                else:
                    if isinstance(msg, bytes):
                        msg = msg.decode("utf8")
                    self._write_stdout(msg)
                    self._save_msg(f"< {msg}")
            except websocket.WebSocketTimeoutException:
                continue
            except websocket.WebSocketConnectionClosedException as e:
                self._write_stdout(f"Connection closed: {str(e)}")
                continue
                # break
            except OSError:
                continue
                # break

    def _run(self):
        """Run the WebSocket communication."""
        try:
            self._receive()
        except Exception as e:
            self._write_stdout(f"Error: {str(e)}")

    def send(
        self,
        request,
        stream=False,
        timeout=None,
        verify: Union[bool, str] = True,
        cert=None,
        proxies=None,
    ):
        """Send a request to the WebSocket.

        Will receive a string if only passed `--cert=path/to/cert`,
        or a HTTPieCertificate object if `--cert-key` passed, like `--cert=path/to/cert --cert-key=path/to/key`

        Args:
            request (PreparedRequest): The request object.
            stream (bool): Whether to stream the response.
            timeout (float): The timeout in seconds.
            verify (Union[bool, str]): Whether to verify the SSL certificate.
            cert (Union[HTTPieCertificate, str]): The path to the SSL certificate.
            proxies (dict): The proxies to use.

        Returns:
            Response: Handshake response info.
        """
        self._running = True
        logger.debug(
            f"ws connecting. stream: {stream}, verify: {verify}, proxy: {proxies}, timeout: {timeout}"
        )
        logger.debug(f"received headers: {request.headers}")

        try:
            self._connect(
                request, stream=stream, timeout=timeout, verify=verify, cert=cert, proxies=proxies
            )
        except AdapterError as e:
            self.close()
            return self.dummy_response(request, e.code, e.msg)

        self._ws_thread.start()
        time.sleep(0.3)
        self._write_stdout(
            f"> Connected to {request.url}\n"
            "Type a message and press enter to send it\n"
            "Press Ctrl+C to close the connection"
        )

        try:
            while self._running and self.connected:
                msg = _read_stdin()
                if not msg:
                    continue
                if not self._running or not self.connected:
                    self._write_stdout(f"Websocket closed, message not sent: {msg}")
                    break
                self._save_msg(f"> {msg}")
                self.send_msg(msg)
        except KeyboardInterrupt:
            self._write_stdout("\nOops! Disconnecting. Need to force quit? Press again!")
            self._close_code = STATUS_ABNORMAL_CLOSED
            self._close_msg = self.ACTIVELY_CLOSE_REASON.decode("utf8")
        finally:
            self.close()

        return self.dummy_response(request)

    def _write_stdout(self, msg: str, newline: bool = True) -> None:
        """Write message to stdout."""
        if not self._running:
            return
        if isinstance(msg, bytes):
            msg = msg.decode("utf8")
        if newline:
            msg += "\n"
        with self._stdout_lock:
            self._stdout.write(msg)
            self._stdout.flush()

    def _save_msg(self, msg: Union[str, bytes], newline: bool = True) -> None:
        """Save message tmp file."""
        if isinstance(msg, str):
            msg = msg.encode("utf8")
        if newline:
            msg += b"\n"
        self._msgs_bytes.write(msg)

    def iter_content(self, chunk_size=1, decode_unicode=False):
        """Iterate over the content of the response
        This method for httpie --download option
        Return all messages of send and receive in bytes
        """
        self._msgs_bytes.seek(0)
        while True:
            chunk = self._msgs_bytes.read(chunk_size)
            if not chunk:
                break
            yield chunk

    def dummy_response(
        self, request: PreparedRequest, status_code: int = 200, msg: str = ""
    ) -> Response:
        """Create a dummy response for requests send method."""
        r = Response()
        r.status_code = status_code
        r.request = request
        r.reason = msg
        r.encoding = "utf-8"
        r.headers = CaseInsensitiveDict(self._ws.getheaders() if self._ws else {})
        r._content = msg.encode("utf8") if msg else b""
        r.raw = io.BytesIO(
            msg.encode("utf8")
            if msg
            else (
                f"Websocket connection info:\nClose Code: {self.close_code}\nClose Msg: {self.close_msg}".encode(
                    "utf8"
                )
            )
        )
        r.iter_content = self.iter_content
        r.encoding = "utf-8"
        r.url = request.url or ""
        return r

    def close(self) -> None:
        """Close the WebSocket connection and clean up resources."""
        if self._running is False:
            return
        self._running = False
        if self._ws and self._ws.connected:
            self._ws.close(status=STATUS_ABNORMAL_CLOSED, reason=self.ACTIVELY_CLOSE_REASON)
        if self._ws_thread.is_alive():
            self._ws_thread.join(5)
            self._ws_thread.stop()

    def send_msg(self, message: str) -> int:
        if not self._ws:
            raise requests.exceptions.RequestException("WebSocket not initialized")
        length: int = self._ws.send_text(message)
        logger.debug(f"Sent message: {message}, frame length: {length}")
        return length


class BaseWebsocketPlugin(TransportPlugin):
    """Base class for WebSocket transport plugins."""

    package_name = "httpie_websockets"
    description = "WebSocket transport plugin for HTTPie"

    def get_adapter(self) -> WebsocketAdapter:
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
    parser.add_argument("--proxy", help="proxy url")
    args = parser.parse_args()

    proxy_u = urlparse(args.proxy)
    proxies = {"http": proxy_u.geturl(), "https": proxy_u.geturl()}

    adapter = WebsocketAdapter()
    session = requests.Session()
    session.mount("ws://", adapter)
    session.mount("wss://", adapter)
    # resp = session.request("WEBSOCKET", args.url, proxies={"socks5": "//195.209.188.101:58543"})
    resp = session.request("WEBSOCKET", args.url, proxies=proxies)
    print("\n".join(f"{k}: {v}" for k, v in resp.headers.items()), end="\n\n")
    try:
        print(json.dumps(resp.text, indent=4))
    except json.JSONDecodeError:
        print(resp.text)
    session.close()
