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
    url = (
        "https://api.proxyscrape.com/v3/free-proxy-list/get?"
        f"request=getproxies&country=hk&skip=0&proxy_format=protocolipport&format=json&limit={limit}&"
        f"anonymity=Elite&timeout={timeout}"
    )
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return [urlparse(proxy["proxy"]) for proxy in data['proxies']]
