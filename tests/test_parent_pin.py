import json

import pytest

from focusguard.storage import memory, parent_pin


@pytest.fixture(autouse=True)
def tempMemory(tmp_path, monkeypatch):
    monkeypatch.setattr(memory, "FILE", tmp_path / "memory.json")


def test_pin_is_never_saved_in_plain_text():
    parent_pin.savePin("4821")
    savedText = memory.FILE.read_text()
    assert "4821" not in savedText
    assert "parentPin" not in json.loads(savedText)
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


def test_old_plain_text_pin_is_upgraded():
    memory.save({"parentPin": "1234"})
    assert parent_pin.hasPin()
    assert "1234" not in memory.FILE.read_text()
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
