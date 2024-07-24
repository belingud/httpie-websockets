from unittest.mock import MagicMock

import pytest

from httpie_websockets import WebsocketAdapter


@pytest.fixture
def websocket_adapter():
    return WebsocketAdapter()


def test_write_stdout_running(websocket_adapter, mocker):
    # Mock sys.stdout
    websocket_adapter._running = True
    mock_stdout = mocker.patch("sys.stdout", new_callable=MagicMock)
    websocket_adapter._stdout = mock_stdout

    # Call the method
    websocket_adapter._write_stdout("test message")

    # Check if the message was written to stdout
    mock_stdout.write.assert_any_call("test message")
    mock_stdout.write.assert_any_call("\n")
    mock_stdout.flush.assert_called_once()


def test_write_stdout_not_running(websocket_adapter, mocker):
    # Set the running flag to False
    websocket_adapter._running = False

    # Mock sys.stdout
    mock_stdout = mocker.patch("sys.stdout", new_callable=MagicMock)
    websocket_adapter._stdout = mock_stdout

    # Call the method
    websocket_adapter._write_stdout("test message")

    # Check if the message was not written to stdout
    mock_stdout.write.assert_not_called()
    mock_stdout.flush.assert_not_called()
