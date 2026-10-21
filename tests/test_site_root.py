import pytest

from focusguard.core.classifier import site_root


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=abc", "youtube.com"),
        ("http://docs.python.org/3/library/", "docs.python.org"),
        ("github.com/anthropics", "github.com"),
        ("https://localhost:8000/x", "localhost"),
        ("chrome://newtab/", None),
        ("file:///Users/me/notes.html", None),
        ("", None),
        (None, None),
    ],
)
def test_site_root(url, expected):
    assert site_root(url) == expected
