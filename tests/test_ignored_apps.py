import pytest

from focusguard.core.classifier import isIgnoredApp
from focusguard.core.models import ActiveWindow


@pytest.mark.parametrize(
    ("appId", "expected"),
    [
        ("explorer.exe", True),
        ("ShellExperienceHost.exe", True),
        ("SnippingTool.exe", True),
        ("focusguard.exe", True),
        ("com.apple.finder", True),
        ("discord.exe", False),
        ("chrome.exe", False),
        ("com.google.chrome", False),
    ],
)
def test_is_ignored_app(appId, expected):
    window = ActiveWindow(app_name="whatever", app_id=appId, pid=1)
    assert isIgnoredApp(window) == expected
