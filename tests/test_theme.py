import pytest

from focusguard.ui.theme import choiceFor, resolveTheme


@pytest.mark.parametrize(
    ("choice", "system", "expected"),
    [
        ("system", "dark", "dark"),
        ("system", "light", "light"),
        ("light", "dark", "light"),
        ("dark", "light", "dark"),
    ],
)
def test_resolve_theme(choice, system, expected):
    assert resolveTheme(choice, system) == expected


@pytest.mark.parametrize(
    ("picked", "system", "expected"),
    [
        ("light", "dark", "light"),
        ("dark", "light", "dark"),
        ("dark", "dark", "system"),
        ("light", "light", "system"),
    ],
)
def test_choice_for(picked, system, expected):
    assert choiceFor(picked, system) == expected
