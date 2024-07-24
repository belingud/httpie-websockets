from unittest.mock import AsyncMock, patch

import pytest

from httpie_websockets import WebsocketAdapter


@pytest.mark.asyncio
async def test_connect():
    adapter = WebsocketAdapter()

    mock_connect = AsyncMock()
    with patch("websockets.connect", new=mock_connect):
        test_url = "ws://example.com"

        await adapter._connect(test_url)

    mock_connect.assert_awaited_once_with(test_url)

    assert adapter._websocket is not None
    assert adapter._websocket.open
