import struct
from unittest.mock import MagicMock, PropertyMock, patch

from websocket import (
    ABNF,
    WebSocketConnectionClosedException,
    WebSocketTimeoutException,
)

from httpie_websockets import WebsocketAdapter  # 请替换为实际的模块名称


def test_receive_message():
    with patch.object(WebsocketAdapter, 'connected', new_callable=PropertyMock) as mock_connected:
        mock_connected.side_effect = [True, False]
        adapter = WebsocketAdapter()
        adapter._running = True
        adapter._ws = MagicMock()
        adapter._ws.recv_data.side_effect = [(ABNF.OPCODE_TEXT, "Test message")]
        adapter._write_stdout = MagicMock()
        adapter._receive()
    adapter._write_stdout.assert_called_with("Test message")


def test_receive_close_message():
    close_code = 1000
    close_message = "Normal Closure"
    msg = struct.pack("!H", close_code) + close_message.encode("utf8")

    with patch.object(WebsocketAdapter, 'connected', new_callable=PropertyMock) as mock_connected:
        mock_connected.side_effect = [True, False]
        adapter = WebsocketAdapter()
        adapter._running = True
        adapter._ws = MagicMock()
        adapter._ws.recv_data.side_effect = [(ABNF.OPCODE_CLOSE, msg)]
        adapter._write_stdout = MagicMock()
        adapter._receive()

    assert adapter._close_code == close_code
    assert adapter._close_msg == close_message


def test_receive_timeout():
    with patch.object(WebsocketAdapter, 'connected', new_callable=PropertyMock) as mock_connected:
        mock_connected.side_effect = [True, False]
        adapter = WebsocketAdapter()
        adapter._running = True
        adapter._ws = MagicMock()
        adapter._ws.recv_data.side_effect = WebSocketTimeoutException()
        adapter._write_stdout = MagicMock()
        adapter._receive()


def test_receive_connection_closed():
    with patch.object(WebsocketAdapter, 'connected', new_callable=PropertyMock) as mock_connected:
        mock_connected.side_effect = [True, False]
        adapter = WebsocketAdapter()
        adapter._running = True
        adapter._ws = MagicMock()
        adapter._ws.recv_data.side_effect = WebSocketConnectionClosedException("Connection closed")
        adapter._write_stdout = MagicMock()
        adapter._receive()

    adapter._write_stdout.assert_called_with("Connection closed: Connection closed")
