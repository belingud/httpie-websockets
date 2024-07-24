import asyncio
from unittest.mock import Mock

import pytest

from httpie_websockets import WebsocketAdapter


@pytest.fixture
def websocket_adapter():
    return WebsocketAdapter()


@pytest.mark.asyncio
async def test_put_get_message(websocket_adapter):
    test_msg = "test message"

    # Call the put method with the test message
    await websocket_adapter.put(test_msg)

    # Retrieve the message from the queue
    retrieved_msg = await websocket_adapter._msg_queue.get()

    # Check if the message put into the queue is the same as the test message
    assert retrieved_msg == test_msg


@pytest.mark.asyncio
async def test_queue_put_called_once():
    # 创建 WebsocketAdapter 实例
    adapter = WebsocketAdapter()

    # 模拟 asyncio.Queue
    mock_queue = Mock()
    mock_queue.put = Mock(wraps=asyncio.Queue().put)
    adapter._msg_queue = mock_queue

    # 测试消息
    test_message = "Hello, World!"

    # 调用 put 方法
    await adapter.put(test_message)

    # 验证 put 方法是否被调用
    mock_queue.put.assert_called_once_with(test_message)
