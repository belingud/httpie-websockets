# conftest.py
import pytest


@pytest.fixture(scope="session", autouse=True)
def docker_compose():
    yield
