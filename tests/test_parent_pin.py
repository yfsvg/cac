# parent pin, only the salted hash gets saved + old plain text ones get upgraded

import json

import pytest

from arete.storage import memory, parent_pin


@pytest.fixture(autouse=True)
def tempMemory(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "FILE", tmp_path / "memory.json")


# every value saved in memory.json. checking these instead of the raw text, since the random hex
# salt/hash will contain the pin's digits now and then (that made CI fail randomly)
def savedValues(node):
    if isinstance(node, dict):
        for value in node.values():
            yield from savedValues(value)
    elif isinstance(node, list):
        for value in node:
            yield from savedValues(value)
    else:
        yield str(node)


def pinIsSaved(pin):
    return pin in savedValues(json.loads(memory.FILE.read_text()))



# saving + checking
def test_pin_is_never_saved_in_plain_text():
    parent_pin.savePin("4821")
    assert not pinIsSaved("4821")
    assert "parentPin" not in memory.load()
    assert parent_pin.hasPin()


def test_right_and_wrong_pin():
    parent_pin.savePin("4821")
    assert parent_pin.pinMatches("4821")
    assert not parent_pin.pinMatches("4822")
    assert not parent_pin.pinMatches("")


def test_same_pin_gets_a_different_salt_each_time():
    parent_pin.savePin("4821")
    firstHash = memory.load()["parentPinHash"]
    parent_pin.savePin("4821")
    secondHash = memory.load()["parentPinHash"]
    assert firstHash["salt"] != secondHash["salt"]
    assert firstHash["hash"] != secondHash["hash"]


# upgrading old versions
def test_old_plain_text_pin_is_upgraded():
    memory.save({"parentPin": "1234"})
    assert pinIsSaved("1234")
    assert parent_pin.hasPin()
    assert not pinIsSaved("1234")
    assert parent_pin.pinMatches("1234")


def test_old_empty_pin_means_no_parental_controls():
    memory.save({"parentPin": ""})
    assert not parent_pin.hasPin()
    assert "parentPin" not in memory.load()


def test_remove_pin():
    parent_pin.savePin("4821")
    parent_pin.removePin()
    assert not parent_pin.hasPin()
    assert not parent_pin.pinMatches("4821")
