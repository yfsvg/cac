from __future__ import annotations
import hashlib
import hmac
import os

from arete.storage import memory

# Only a salted scrypt hash of the parent PIN is saved, never the PIN itself.
# scrypt is slow and memory-hungry on purpose, so guessing PINs from the hash takes a long time.
SCRYPT_N = 2 ** 15
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_MAX_MEMORY = 64 * 1024 * 1024


def hashPin(pin: str, salt: bytes, n: int, r: int, p: int) -> str:
    pinHash = hashlib.scrypt(pin.encode(), salt=salt, n=n, r=r, p=p, maxmem=SCRYPT_MAX_MEMORY, dklen=32)
    return pinHash.hex()





# Saving / removing pin

def savePin(newPin: str) -> None:
    salt = os.urandom(16)
    savedMemory = memory.load()
    savedMemory.pop("parentPin", None)
    savedMemory["parentPinHash"] = {
        "salt": salt.hex(),
        "hash": hashPin(newPin, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P),
        "n": SCRYPT_N,
        "r": SCRYPT_R,
        "p": SCRYPT_P,
    }
    memory.save(savedMemory)


def removePin() -> None:
    savedMemory = memory.load()
    savedMemory.pop("parentPin", None)
    savedMemory.pop("parentPinHash", None)
    memory.save(savedMemory)


# old versions saved pin as plain text, this hashes it first time its seen
def upgradeOldPin() -> None:
    oldPin = memory.load().get("parentPin")
    if oldPin is None:
        return
    if oldPin == "":
        removePin()
    else:
        savePin(str(oldPin))





# checking pin

def hasPin() -> bool:
    upgradeOldPin()
    return "parentPinHash" in memory.load()


def pinMatches(typedPin: str) -> bool:
    upgradeOldPin()
    savedHash = memory.load().get("parentPinHash")
    if not isinstance(savedHash, dict):
        return False
    try:
        salt = bytes.fromhex(savedHash["salt"])
        typedHash = hashPin(typedPin, salt, int(savedHash["n"]), int(savedHash["r"]), int(savedHash["p"]))
    except (KeyError, TypeError, ValueError):
        return False
    # compare_digest = same time match or not, so no timing guessing
    return hmac.compare_digest(typedHash, str(savedHash["hash"]))
