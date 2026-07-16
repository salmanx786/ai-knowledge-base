"""Password hashing primitives.

This module intentionally contains *only* the hashing/verification
primitives. Login, session issuance, and JWT are out of scope and live
elsewhere when they are implemented.

Uses ``pwdlib`` with Argon2id, the OWASP-recommended password hashing
algorithm for new applications and the actively maintained successor to
``passlib`` (which no longer receives updates).
"""

from pwdlib import PasswordHash

# A single shared hasher. ``recommended()`` selects Argon2id with sensible
# default cost parameters and supports transparent rehashing later.
_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Return an Argon2id hash (including salt and parameters) for ``password``."""
    return _password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Return ``True`` if ``password`` matches the stored ``hashed_password``."""
    return _password_hash.verify(password, hashed_password)
