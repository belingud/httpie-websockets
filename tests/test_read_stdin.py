import sys
from unittest.mock import MagicMock

import pytest

from httpie_websockets import WebsocketAdapter


@pytest.fixture
def mock_select(mocker):
    return mocker.patch("select.select")


@pytest.fixture
def mock_stdin(mocker):
    return mocker.patch("sys.stdin", new_callable=MagicMock)


def test_read_stdin_no_input(mock_select, mock_stdin):
    # Create an instance of WebsocketAdapter
    adapter = WebsocketAdapter()

    # Mock select.select to simulate no input
    mock_select.return_value = ([], [], [])

    # Call the method and check the result
    result = adapter.read_stdin()
    assert result is None


def test_read_stdin_with_input(mock_select, mock_stdin):
    # Create an instance of WebsocketAdapter
    adapter = WebsocketAdapter()

    # Mock select.select to simulate input
    mock_select.return_value = ([sys.stdin], [], [])

    # Mock sys.stdin to simulate user input
    mock_stdin.readline.return_value = "test input\n"

    # Call the method and check the result
    result = adapter.read_stdin()
    assert result == "test input"
