from concurrent.futures import CancelledError
from unittest.mock import MagicMock, patch

import pytest
from websockets.exceptions import ConnectionClosed

from httpie_websockets import WebsocketAdapter


class TestWebsocketAdapter:
    def setup_method(self):
        self.adapter = WebsocketAdapter()
        self.adapter._running = True
        self.adapter._ws_client = MagicMock()
        self.adapter._ws_client.recv = MagicMock()
        self.adapter._ws_client.protocol.state = 1

    def teardown_method(self):
        self.adapter.close()

    @patch("httpie_websockets.WebsocketAdapter._write_stdout")
    def test_listening_connection_closed(self, mock_write_stdout):
        self.adapter._ws_client.recv.side_effect = ConnectionClosed(None, None)

        self.adapter._listening()

        mock_write_stdout.assert_called_once_with(
            "Connection closed when listening with code: 1006, reason: "
        )

    @patch("httpie_websockets.WebsocketAdapter._write_stdout")
    def test_listening_timeout_error(self, mock_write_stdout):
        self.adapter._ws_client.recv.side_effect = EOFError

        self.adapter._listening()

        mock_write_stdout.assert_not_called()

    @patch("httpie_websockets.WebsocketAdapter._write_stdout")
    def test_listening_exception(self, mock_write_stdout):
        self.adapter._ws_client.recv.side_effect = RuntimeError

        self.adapter._listening()

        mock_write_stdout.assert_called_once_with("Another WS receiver is already running: ")

    @patch("httpie_websockets.WebsocketAdapter._write_stdout")
    def test_listening_cancelled_error(self, mock_write_stdout):
        self.adapter._ws_client.recv.side_effect = CancelledError

        self.adapter._listening()

        mock_write_stdout.assert_not_called()

    @patch("httpie_websockets.WebsocketAdapter._write_stdout")
    def test_listening_unexpected_error(self, mock_write_stdout):
        self.adapter._ws_client.recv.side_effect = Exception("test")

        self.adapter._listening()

        mock_write_stdout.assert_called_once_with("Unexpected error while listening: test")


if __name__ == "__main__":
    pytest.main()
