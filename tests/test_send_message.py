import asyncio

import pytest
import websockets.exceptions

from httpie_websockets import WebsocketAdapter


@pytest.mark.asyncio
async def test_send_messages():
    adapter = WebsocketAdapter()
    adapter._running = True
    adapter._msg_queue = asyncio.Queue()
    received = []

    async def echo(_websocket: websockets.WebSocketServerProtocol, path: str) -> None:
        async for msg in _websocket:
            received.append(msg)
            await _websocket.send(msg)

    server = await websockets.serve(echo, "localhost", 8765)

    async with websockets.connect("ws://localhost:8765") as websocket:
        adapter._websocket = websocket

        test_messages = ["Message 1", "Message 2"]

        for message in test_messages:
            await adapter._msg_queue.put(message)
        await adapter._msg_queue.put(None)

        send_task = asyncio.create_task(adapter._send_messages())

        await asyncio.sleep(1)

        send_task.cancel()
        try:
            await send_task
        except asyncio.CancelledError:
            pass

        assert received == test_messages

    assert not adapter._websocket.open

    server.close()
    await server.wait_closed()
