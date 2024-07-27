import sys
from unittest.mock import patch

import pytest

from httpie_websockets import _read_stdin, IS_WINDOWS


@pytest.mark.skipif(not IS_WINDOWS, reason="Requires Windows platform")
def test_read_stdin_windows(monkeypatch):
    with patch("msvcrt.kbhit", return_value=True):
        with patch("msvcrt.getwche", side_effect=list("test_input") + ["\r"]):
            assert _read_stdin() == "test_input"


@pytest.mark.skipif(IS_WINDOWS, reason="Requires non-Windows platform")
def test_read_stdin_non_windows(monkeypatch):
    with patch("select.select", return_value=([sys.stdin], [], [])):
        with patch("sys.stdin.readline", return_value="test_input\n"):
            assert _read_stdin() == "test_input"
