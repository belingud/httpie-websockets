from unittest import mock

import pytest
from websocket import WebSocketException

from httpie_websockets import WebsocketAdapter


def test_send_msg_success():
    # Create an instance of WebsocketAdapter
    adapter = WebsocketAdapter()

    # Mock the websocket object
    adapter._ws = mock.Mock()

    # Mock the send_text method to return a specific length
    message = "test message"
    adapter._ws.send_text.return_value = len(message)

    # Call the send_msg method
    result = adapter.send_msg(message)

    # Assert that the send_text method was called with the correct message
    adapter._ws.send_text.assert_called_once_with(message)

    # Assert that the return value matches the length of the message
    assert result == len(message)


def test_send_msg_no_websocket():
    # Create an instance of WebsocketAdapter without initializing _ws
    adapter = WebsocketAdapter()

    # Try sending a message without a WebSocket connection
    with pytest.raises(Exception) as exc_info:
        adapter.send_msg("test message")

    # Assert that an exception is raised
    assert "WebSocket not initialized" in str(exc_info.value)


def test_send_msg_websocket_exception():
    # Create an instance of WebsocketAdapter
    adapter = WebsocketAdapter()

    # Mock the websocket object
    adapter._ws = mock.Mock()

    # Mock the send_text method to raise a WebSocketException
    adapter._ws.send_text.side_effect = WebSocketException("Test Exception")

    # Try sending a message and expect an exception
    with pytest.raises(WebSocketException) as exc_info:
        adapter.send_msg("test message")

    # Assert that the exception message is correct
    assert "Test Exception" in str(exc_info.value)
