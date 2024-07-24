import asyncio

import pytest

from httpie_websockets import WebsocketAdapter
from tests import MockTask


@pytest.fixture
def websocket_adapter():
    return WebsocketAdapter()


@pytest.mark.asyncio
async def test_cancel_all_tasks(mocker, websocket_adapter):
    # Create mock tasks
    task1 = MockTask()
    task2 = MockTask()

    task2.done.return_value = True

    # Mock the asyncio.all_tasks function to return the mock tasks
    mocker.patch("asyncio.all_tasks", return_value={task1, task2}, autospec=True)

    # Call the method
    await websocket_adapter.cancel_all_tasks()

    # Check that only the task that wasn't done was cancelled and awaited
    task1.cancel.assert_called_once()
    task2.cancel.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_all_tasks_with_cancelled_error(mocker, websocket_adapter):
    # Create a mock task
    task = MockTask()

    # Make task raise CancelledError
    task.cancel.side_effect = asyncio.CancelledError

    # Mock the asyncio.all_tasks function to return the mock task
    mocker.patch("asyncio.all_tasks", return_value={task}, autospec=True)

    # Call the method
    await websocket_adapter.cancel_all_tasks()

    # Check that the task was cancelled
    task.cancel.assert_called_once()
