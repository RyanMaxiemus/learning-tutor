from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash


_ARGON2_PH = PasswordHasher()  # uses safe defaults (memory/time/parallelism)
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)


@dataclass(frozen=True)
class PasswordVerification:
    ok: bool
    needs_rehash: bool = False
    upgraded_hash: Optional[str] = None


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password must not be empty")
    return _ARGON2_PH.hash(password)


def verify_password(password: str, stored_hash: Optional[str]) -> PasswordVerification:
    """
    Verifies password against either:
    - Argon2 hashes (preferred)
    - legacy unsalted SHA-256 hex hashes (migrates on successful login)
    """
    if not password or not stored_hash:
        return PasswordVerification(ok=False)

    # Preferred: Argon2
    if stored_hash.startswith("$argon2"):
        try:
            ok = _ARGON2_PH.verify(stored_hash, password)
            if not ok:
                return PasswordVerification(ok=False)
            needs_rehash = _ARGON2_PH.check_needs_rehash(stored_hash)
            if needs_rehash:
                new_hash = _ARGON2_PH.hash(password)
                return PasswordVerification(ok=True, needs_rehash=True, upgraded_hash=new_hash)
            return PasswordVerification(ok=True)
        except (VerifyMismatchError, VerificationError, InvalidHash):
            return PasswordVerification(ok=False)

    # Legacy: SHA-256 hex (unsalted)
    if _SHA256_HEX_RE.match(stored_hash):
        legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
        if hmac.compare_digest(legacy, stored_hash.lower()):
            new_hash = _ARGON2_PH.hash(password)
            return PasswordVerification(ok=True, needs_rehash=True, upgraded_hash=new_hash)
        return PasswordVerification(ok=False)

    return PasswordVerification(ok=False)

