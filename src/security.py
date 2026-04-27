import hashlib
import hmac
import os


def hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    if not password:
        raise ValueError("Password cannot be empty.")

    salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        150_000,
    )
    return password_hash.hex(), salt.hex()


def verify_password(password: str, stored_hash_hex: str, salt_hex: str) -> bool:
    computed_hash_hex, _ = hash_password(password, salt_hex)
    return hmac.compare_digest(computed_hash_hex, stored_hash_hex)
