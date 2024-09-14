import random
from pathlib import Path
from unittest.mock import patch

import pytest
import websocket
from requests.models import Request

from httpie_websockets import AdapterError, WebsocketAdapter
from tests import get_proxy


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
    all_proxies = get_proxy()
    if not all_proxies:
        pytest.skip("[SKIP] test function: test_connect_with_proxy. No proxy available from API.")
    choice_one = random.choice(all_proxies)
    _proxy = {choice_one.scheme: choice_one.geturl()}
    try:
        adapter._connect(request, proxies=_proxy)
    except AdapterError as e:
        if "proxy" in e.msg:
            pytest.skip(f"[SKIP] test function: test_connect_with_proxy. Proxy err: {e.msg}")
    assert adapter._ws is not None


def test_connect_verify_false():
    adapter = WebsocketAdapter()
    request = Request(url="wss://echo.websocket.org").prepare()
    adapter._connect(request, verify=False)
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
