import asyncio
import io
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
import websockets

from httpie_websockets import WebsocketAdapter


def test_connect_success():
    adapter = WebsocketAdapter()
    adapter._stdout = io.StringIO()
    request = MagicMock()
    adapter._running = True
    request.url = "ws://localhost:8765/ws"
    try:
        adapter._connect(request.url)
    except Exception as e:
        print("error when connect>>>>>>>")
        print(e)
        raise e
    adapter._executor.submit(adapter._listening)
    adapter._executor.submit(adapter._sending)
    msg = "Hello"
    adapter.put(msg)
    print('::::::::::::', adapter._stdout.read())
    assert msg in adapter._stdout.read()
    adapter.close()


@pytest.mark.asyncio
async def test_connect_failure(websocket_server):
    adapter = WebsocketAdapter()
    request = MagicMock()
    request.url = "ws://localhost:8766"  # Invalid URL
    response = adapter.send(request)
    assert response.status_code == 500
    adapter.close()


@pytest.mark.asyncio
async def test_send_receive_messages(websocket_server):
    adapter = WebsocketAdapter()
    request = MagicMock()
    request.url = "ws://localhost:8765"
    response = adapter.send(request)
    assert response.status_code == 200

    # Mock stdin
    with patch("sys.stdin", new=StringIO("Hello\n")):
        msg = adapter.read_stdin()
        assert msg == "Hello"

    # Send message to server
    adapter.put("Hello")

    # Receive message from server
    async def receive_message():
        async with websockets.connect("ws://localhost:8765") as websocket:
            message = await websocket.recv()
            assert message == "Echo: Hello"

    await receive_message()
    adapter.close()


@pytest.mark.asyncio
async def test_close_connection(websocket_server):
    adapter = WebsocketAdapter()
    request = MagicMock()
    request.url = "ws://localhost:8765"
    response = adapter.send(request)
    assert response.status_code == 200

    adapter.close()
    assert not adapter.connected


@pytest.mark.asyncio
async def test_read_stdin_while_sending(websocket_server):
    adapter = WebsocketAdapter()
    request = MagicMock()
    request.url = "ws://localhost:8765"
    response = adapter.send(request)
    assert response.status_code == 200

    # Mock stdin
    with patch("sys.stdin", new=StringIO("Hello\n")):
        # Create an event to simulate waiting for input
        input_event = asyncio.Event()

        async def read_input():
            while True:
                msg = adapter.read_stdin()
                if msg:
                    input_event.set()
                    break
                await asyncio.sleep(0.1)

        # Start the input reading task
        input_task = asyncio.create_task(read_input())

        # Wait for the input event to be set
        await input_event.wait()

        # Ensure the input was read correctly
        assert input_task.result() == "Hello"

        # Send message to server
        asyncio.run_coroutine_threadsafe(adapter.put("Hello"), adapter._ws_loop).result()

        # Receive message from server
        async def receive_message():
            async with websockets.connect("ws://localhost:8765") as websocket:
                message = await websocket.recv()
                assert message == "Echo: Hello"

        await receive_message()
        adapter.close()
