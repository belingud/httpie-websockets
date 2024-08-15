import pytest
from httpie.client import DEFAULT_UA

from httpie_websockets import WebsocketAdapter


@pytest.fixture
def adapter():
    return WebsocketAdapter()


def test_empty_headers(adapter):
    headers = {}
    expected = []
    assert adapter.convert2ws_headers(headers) == expected


def test_ignore_keys(adapter):
    headers = {
        "Upgrade": "websocket",
        "Connection": "keep-alive",
        "Origin": "http://example.com",
        "Host": "example.com",
        "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
        "Sec-WebSocket-Version": "13",
    }
    expected = [f"User-Agent: {headers.get('User-Agent', DEFAULT_UA)}"]
    assert adapter.convert2ws_headers(headers) == expected


def test_non_ignore_keys(adapter):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    expected = [
        "Content-Type: application/json",
        "Accept: application/json",
        f"User-Agent: {DEFAULT_UA}",
    ]
    assert adapter.convert2ws_headers(headers) == expected


def test_bytes_value(adapter):
    headers = {
        "Content-Type": b"application/json",
    }
    expected = [
        "Content-Type: application/json",
        f"User-Agent: {DEFAULT_UA}",
    ]
    assert adapter.convert2ws_headers(headers) == expected


def test_no_user_agent(adapter):
    headers = {"Key": "Value"}
    expected = ["Key: Value", f"User-Agent: {DEFAULT_UA}"]
    assert adapter.convert2ws_headers(headers) == expected


def test_user_agent(adapter):
    headers = {
        "User-Agent": "My User Agent",
    }
    expected = [
        "User-Agent: My User Agent",
    ]
    assert adapter.convert2ws_headers(headers) == expected
