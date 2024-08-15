# conftest.py
import subprocess  # noqa: F401
import typing as t
from multiprocessing import Process
from pathlib import Path

import pytest

websocket_task: t.Optional[Process] = None
test_root = Path(__file__).parent
ws_server_file = test_root / "ws_server.py"
compose_file = test_root / "docker-compose.yml"


@pytest.fixture(scope="session", autouse=True)
def docker_compose():
    print("++++++++++++++++++++++++++starting ws container+++++++++++++++++++++++++++++")

    yield

    print("++++++++++++++++++++++++++stopping ws container+++++++++++++++++++++++++++++")
