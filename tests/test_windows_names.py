# windows app names, cleaning exe descriptions up

import sys

import pytest

if sys.platform != "win32":
    pytest.skip("Windows backend", allow_module_level=True)

from arete.platform.windows import tidyDescription


@pytest.mark.parametrize(
    ("desc", "expected"),
    [
        ("PowerToys.Run", "PowerToys Run"),
        ("PowerToys.Peek.UI", "PowerToys Peek UI"),
        ("Microsoft.Media.Player", "Microsoft Media Player"),
        ("Google Chrome", "Google Chrome"),
        ("Helium", "Helium"),
        ("draw.io", "draw.io"),
        ("Node.js JavaScript Runtime", "Node.js JavaScript Runtime"),
        ("Setup.exe", "Setup.exe"),
    ],
)
def test_tidy_description(desc, expected):
    assert tidyDescription(desc) == expected
