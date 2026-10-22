import pytest

from focusguard.core.classifier import site_root


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://www.youtube.com/watch?v=abc", "youtube.com"),
        ("chrome://newtab/", None),
        ("", None),
        (None, None),
    ],
)
def test_site_root(url, expected):
    assert site_root(url) == expected
