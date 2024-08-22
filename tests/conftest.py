# conftest.py

import pytest


@pytest.fixture(scope="session", autouse=True)
def docker_compose():
    print("++++++++++++++++++++++++++starting ws container+++++++++++++++++++++++++++++")

    yield

    print("++++++++++++++++++++++++++stopping ws container+++++++++++++++++++++++++++++")
