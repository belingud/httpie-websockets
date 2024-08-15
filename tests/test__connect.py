from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import websocket
from httpie.ssl_ import HTTPieCertificate
from requests.models import Request

from httpie_websockets import AdapterError, WebsocketAdapter


def test_connect_already_connected():
    adapter = WebsocketAdapter()
    request = Request(url="wss://echo.websocket.org").prepare()
    adapter._connect(request)
    assert adapter.connected is True


def test_connect_no_proxy():
    adapter = WebsocketAdapter()
    request = Request(url="wss://echo.websocket.org").prepare()
    adapter._connect(request)
    assert adapter._ws is not None


def test_connect_with_proxy():
    adapter = WebsocketAdapter()
    request = Request(url="wss://echo.websocket.org").prepare()
    proxies = {"http": "http://103.106.219.219:8080"}
    proxies = {"socks5": "socks5://147.182.203.142:12345"}
    adapter._connect(request, proxies=proxies)
    assert adapter._ws is not None


def test_connect_verify_false():
    adapter = WebsocketAdapter()
    request = Request(url="wss://echo.websocket.org").prepare()
    adapter._connect(request, verify=False)
    assert adapter._ws is not None


def test_connect_verify_true_cert_httpiecertificate():
    adapter = WebsocketAdapter()
    request = Request(url="ws://echo.websocket.org").prepare()
    cert = MagicMock(spec=HTTPieCertificate)
    cert.key_file = "path/to/keyfile"
    cert.cert_file = "path/to/certfile"
    cert.key_password = "password"
    adapter._connect(request, verify=True, cert=cert)
    assert adapter._ws is not None


def test_connect_verify_true_cert_str():
    adapter = WebsocketAdapter()
    request = Request(url="wss://echo.websocket.org").prepare()
    test_path = Path(__file__).resolve().parent
    cert = test_path / "ssl" / "cert.pem"
    adapter._connect(request, verify=True, cert=cert)
    assert adapter._ws is not None


def test_connect_exception():
    adapter = WebsocketAdapter()
    request = Request(url="wss://echo.websocket.org").prepare()
    with patch.object(
        websocket, "WebSocket", side_effect=websocket.WebSocketException("Test exception")
    ):
        with pytest.raises(AdapterError):
            adapter._connect(request)
