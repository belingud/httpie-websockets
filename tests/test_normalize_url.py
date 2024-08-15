from urllib.parse import urlparse

from httpie_websockets import normalize_url

# def test_normalize_url():
#     test_cases = [
#         ("//119.95.252.172:8080", "http://119.95.252.172:8080"),
#         ("://119.95.252.172:8080", "http://119.95.252.172:8080"),
#         ("http://119.95.252.172:8080", "http://119.95.252.172:8080"),
#         ("https://119.95.252.172:8080", "https://119.95.252.172:8080"),
#         ("119.95.252.172:8080", "http://119.95.252.172:8080"),
#         ("socks4://119.95.252.172:8080", "socks4://119.95.252.172:8080"),
#         ("socks5://119.95.252.172:8080", "socks5://119.95.252.172:8080"),
#         ("invalid_url", ""),
#         ("http://", ""),
#         ("http://example.com", "http://example.com"),
#         ("https://example.com", "https://example.com"),
#         ("socks4://example.com", "socks4://example.com"),
#         ("socks5://example.com", "socks5://example.com"),
#     ]
#
#     for input_url, expected_result in test_cases:
#         result = normalize_url(input_url)
#         if expected_result is None:
#             assert result is None
#         else:
#             expected_parsed_url = urlparse(expected_result)
#             assert result == expected_parsed_url


def test_no_protocol():
    url = "example.com"
    expected = urlparse("http://example.com")
    assert normalize_url(url) == expected


def test_socks4():
    url = "socks4://example.com"
    expected = urlparse("socks4://example.com")
    assert normalize_url(url) == expected


def test_socks4a():
    url = "socks4a://example.com"
    expected = urlparse("socks4a://example.com")
    assert normalize_url(url) == expected


def test_socks5():
    url = "socks5://example.com"
    expected = urlparse("socks5://example.com")
    assert normalize_url(url) == expected


def test_socks5h():
    url = "socks5h://example.com"
    expected = urlparse("socks5h://example.com")
    assert normalize_url(url) == expected


def test_only_colon_slash_slash():
    url = "://example.com"
    expected = urlparse("http://example.com")
    assert normalize_url(url) == expected


def test_only_slash_slash():
    url = "//example.com"
    expected = urlparse("http://example.com")
    assert normalize_url(url) == expected


def test_already_has_protocol():
    url = "https://example.com"
    expected = urlparse(url)
    assert normalize_url(url) == expected


def test_default_protocol():
    url = "example.com"
    expected = urlparse("http://example.com")
    assert normalize_url(url) == expected


def test_custom_default_protocol():
    url = "example.com"
    default_scheme = "https"
    expected = urlparse("https://example.com")
    assert normalize_url(url, default_scheme) == expected


def test_invalid_url():
    url = " invalid url "
    expected = urlparse("")
    assert normalize_url(url) == expected
