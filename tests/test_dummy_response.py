from unittest.mock import Mock

from requests.models import PreparedRequest

from httpie_websockets import WebsocketAdapter


def test_dummy_response():
    adapter = WebsocketAdapter()
    mock_websocket = Mock()
    adapter._ws_client = mock_websocket
    mock_websocket.protocol.close_code = 1000
    mock_websocket.protocol.close_reason = "Closed by user"
    mock_websocket.response.headers = {
        "connection": "upgrade",
        "upgrade": "websocket",
        "sec-websocket-accept": "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=",
        "sec-websocket-extensions": "permessage-deflate; client_no_context_takeover; client_max_window_bits",
        "sec-websocket-version": "13",
        "date": "Wed, 24 Jul 2024 15:42:28 GMT",
        "server": "nginx",
    }

    request = PreparedRequest()
    request.url = "ws://example.com"

    resp = adapter.dummy_response(request)
    assert resp.status_code == 200
    assert resp.reason == "Closed by user"
    assert resp._content == "Closed by user"
    assert resp.raw.read() == b"Close Code: 1000\nReason: Closed by user"
    assert resp.url == request.url
