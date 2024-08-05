# conftest.py
import subprocess
import sys
from multiprocessing import Process
from pathlib import Path

import pytest

websocket_task: Process = None
test_root = Path(__file__).parent
ws_server_file = test_root / "ws_server.py"
compose_file = test_root / "docker-compose.yml"


@pytest.fixture(scope="session", autouse=True)
def docker_compose():
    print("++++++++++++++++++++++++++starting ws container+++++++++++++++++++++++++++++")
    subprocess.call(["docker-compose", "-f", str(compose_file), "up", "--build", "-d"])

    yield

    print("++++++++++++++++++++++++++stopping ws container+++++++++++++++++++++++++++++")
    # down = subprocess.run(
    #     [
    #         "docker-compose",
    #         "-f",
    #         str(compose_file),
    #         "down",
    #         "--rmi",
    #         "all",
    #         "--volumes",
    #         "--remove-orphans",
    #     ],
    #     check=True,
    # )
    sys.exit()
