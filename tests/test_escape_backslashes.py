from httpie_websockets import escape_backslashes


def test_escape_backslashes():
    assert escape_backslashes("") == ("", True)
    assert escape_backslashes("a") == ("a", True)
    assert escape_backslashes("\\") == ("", False)
    assert escape_backslashes("\\\\") == ("\\", True)
    assert escape_backslashes("\\\\\\") == ("\\", False)
    assert escape_backslashes("\\\\\\\\") == ("\\\\", True)
