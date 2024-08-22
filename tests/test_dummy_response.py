import io
from unittest import mock

from requests import PreparedRequest

from httpie_websockets import WebsocketAdapter  # 替换为实际模块名称


def test_dummy_response_default():
    adapter = WebsocketAdapter()

    request = PreparedRequest()
    request.url = "ws://localhost:8080"

    response = adapter.dummy_response(request)

    assert response.status_code == 200
    assert response.url == "ws://localhost:8080"
    assert response.reason == ""
    assert response.encoding == "utf-8"
    assert response.headers == {}
    assert response.content == b""
    assert isinstance(response.raw, io.BytesIO)


def test_dummy_response_with_status_and_msg():
    adapter = WebsocketAdapter()

    request = PreparedRequest()
    request.url = "ws://localhost:8080"

    adapter._close_code = 1000
    adapter._close_msg = "Normal Closure"

    response = adapter.dummy_response(request, status_code=400, msg="Error message")

    assert response.status_code == 400
    assert response.reason == "Error message"
    assert response.content == b"Error message"
    assert isinstance(response.raw, io.BytesIO)
    assert response.raw.read() == b"Error message"
    assert response.url == "ws://localhost:8080"


def test_dummy_response_with_ws_headers():
    adapter = WebsocketAdapter()

    request = PreparedRequest()
    request.url = "ws://localhost:8080"

    adapter._ws = mock.Mock()
    adapter._ws.getheaders.return_value = {"Content-Type": "application/json"}

    response = adapter.dummy_response(request)

    assert response.headers == {"Content-Type": "application/json"}
    assert response.status_code == 200
    assert response.reason == ""
    assert response.content == b""
    assert isinstance(response.raw, io.BytesIO)
    assert response.url == "ws://localhost:8080"


def test_dummy_response_with_close_info():
    adapter = WebsocketAdapter()

    request = PreparedRequest()
    request.url = "ws://localhost:8080"

    adapter._close_code = 1001
    adapter._close_msg = "Going away"

    response = adapter.dummy_response(request)

    expected_content = (
        "Websocket connection info:\n" "Close Code: 1001\n" "Close Msg: Going away"
    ).encode("utf8")

    assert response.raw.read() == expected_content
    assert response.content == b""
    assert response.url == "ws://localhost:8080"
