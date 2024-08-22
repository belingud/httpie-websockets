from unittest.mock import MagicMock

import pytest

from httpie_websockets import WebsocketAdapter


@pytest.fixture
def websocket_adapter():
    return WebsocketAdapter()


def test_write_stdout_success():
    adapter = WebsocketAdapter()
    adapter._running = True
    mock_stdout = MagicMock()
    adapter._stdout = mock_stdout

    adapter._write_stdout("test message")

    mock_stdout.write.assert_called_once_with("test message\n")

    # mock_stdout.flush.assert_called_once()


def test_write_stdout_bytes_message():
    adapter = WebsocketAdapter()
    adapter._running = True
    mock_stdout = MagicMock()
    adapter._stdout = mock_stdout

    adapter._write_stdout(b"test bytes message")

    mock_stdout.write.assert_called_once_with("test bytes message\n")

    mock_stdout.flush.assert_called_once()


def test_write_stdout_no_newline():
    adapter = WebsocketAdapter()
    adapter._running = True
    mock_stdout = MagicMock()
    adapter._stdout = mock_stdout

    adapter._write_stdout("test message", newline=False)

    mock_stdout.write.assert_called_once_with("test message")

    mock_stdout.flush.assert_called_once()


def test_write_stdout_running(websocket_adapter, mocker):
    # Mock sys.stdout
    websocket_adapter._running = True
    mock_stdout = mocker.patch("sys.stdout", new_callable=MagicMock)
    websocket_adapter._stdout = mock_stdout

    # Call the method
    websocket_adapter._write_stdout("test message")

    # Check if the message was written to stdout
    mock_stdout.write.assert_any_call("test message\n")
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
