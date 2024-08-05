from unittest.mock import AsyncMock, patch

import pytest

from httpie_websockets import AdapterError, WebsocketAdapter


@pytest.mark.asyncio
async def test_connect():
    adapter = WebsocketAdapter()

    mock_connect = AsyncMock()
    with patch("websockets.connect", new=mock_connect):
        test_url = "ws://example.com"

        await adapter._connect(test_url)

    mock_connect.assert_awaited_once_with(test_url, close_timeout=4)

    assert adapter._websocket is not None
    assert adapter.connected


def test_connect_ok():
    adapter = WebsocketAdapter()
    adapter._connect("wss://echo.websocket.org")
    assert adapter._websocket is not None
    assert adapter.connected
    adapter.close()


def test_connect_error():
    adapter = WebsocketAdapter()
    with pytest.raises(AdapterError):
        adapter._connect("ws://example.com")
    assert adapter._websocket is None
    assert not adapter.connected
