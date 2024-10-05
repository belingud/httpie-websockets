import os
from functools import lru_cache
from unittest.mock import Mock
from urllib.parse import urlparse

import requests


class MockTask:
    def __init__(self):
        self.cancel = Mock()
        self.done = Mock(return_value=False)

    def __await__(self):
        yield


@lru_cache(maxsize=3)
def get_proxy(limit=10, timeout=5000):
    url = "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/countries/HK/data.txt"
    resp = requests.get(url)
    resp.raise_for_status()
    os.environ.pop("HTTP_PROXY", None)
    os.environ.pop("HTTPS_PROXY", None)
    os.environ.pop("ALL_PROXY", None)
    os.environ.pop("http_proxy", None)
    os.environ.pop("https_proxy", None)
    os.environ.pop("all_proxy", None)
    data = resp.text.splitlines()
    return [urlparse(proxy) for proxy in data]
