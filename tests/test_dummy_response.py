from unittest.mock import Mock
from requests.models import PreparedRequest
from httpie_websockets import WebsocketAdapter


def test_dummy_response():
    adapter = WebsocketAdapter()
    mock_websocket = Mock()
    adapter._websocket = mock_websocket
    mock_websocket.close_code = 1000
    mock_websocket.close_reason = "Closed by user"

    request = PreparedRequest()
    request.url = "ws://example.com"

    resp = adapter.dummy_response(request)
    assert resp.status_code == 200
    assert resp.reason == "Closed by user"
    assert resp._content == "Closed by user"
    assert resp.raw.read() == b"Close Code: 1000\nReason: Closed by user"
    assert resp.url == request.url
