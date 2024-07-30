# test_receive.py
import asyncio
from unittest.mock import MagicMock, Mock

import pytest
import websockets

from httpie_websockets import WebsocketAdapter


async def echo(websocket: websockets.WebSocketServerProtocol, path: str) -> None:
    async for message in websocket:
        await websocket.send(message)


@pytest.fixture
def websocket_adapter():
    adapter = WebsocketAdapter()
    adapter._running = True
    adapter._websocket = None  # Will be set during the test
    adapter._write_stdout = MagicMock()
    return adapter


@pytest.fixture
async def websocket():
    async with websockets.serve(echo, "localhost", 8765):
        async with websockets.connect("ws://localhost:8765") as websocket:
            yield websocket


@pytest.mark.asyncio
async def test_receive(websocket_adapter: WebsocketAdapter, websocket: websockets.WebSocketServerProtocol):
    print('>>>>>>>>', websocket, type(websocket))
    websocket_adapter._websocket = websocket

    # Start the _receive coroutine
    receive_task = asyncio.create_task(websocket_adapter._receive())

    # Send a test message to the WebSocket server
    test_message = "test message"
    await websocket.send(test_message)

    # Allow the coroutine to process
    await asyncio.sleep(0.1)

    # Check that the _write_stdout method was called with the test message
    websocket_adapter._write_stdout.assert_called_once_with(test_message)

    # Cancel the task to exit the while loop
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_receive_connection_closed(websocket_adapter, websocket):
    websocket_adapter._websocket = websocket
    sent = rcvd = Mock()
    rcvd.code = 1000
    sent.reason = "test"
    # Mock the websocket to raise ConnectionClosed
    websocket_adapter._websocket.recv = MagicMock(
        side_effect=websockets.exceptions.ConnectionClosed(rcvd, sent)
    )

    await websocket_adapter._receive()

    # Check that the _write_stdout method was called with the connection closed message
    assert websocket_adapter._write_stdout.call_count == 1
    call_args = websocket_adapter._write_stdout.call_args[0][0]
    assert "Connection closed when listening with code: 1000, reason: test" in call_args



@pytest.mark.asyncio
async def test_receive_cancelled_error(websocket_adapter, websocket):
    websocket_adapter._websocket = websocket

    # Mock the websocket to raise CancelledError
    websocket_adapter._websocket.recv = MagicMock(side_effect=asyncio.CancelledError)

    # Ensure no exceptions are raised
    try:
        await websocket_adapter._receive()
    except asyncio.CancelledError:
        pytest.fail("CancelledError was not handled properly")
