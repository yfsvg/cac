# urls -> just the site, like youtube.com

import pytest

from arete.core.classifier import siteRoot


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
    assert siteRoot(url) == expected
