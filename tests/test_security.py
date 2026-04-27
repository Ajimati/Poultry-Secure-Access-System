import unittest

from src.security import hash_password, verify_password


class SecurityTests(unittest.TestCase):
    def test_password_hash_round_trip(self) -> None:
        password_hash, salt = hash_password("securepass123")
        self.assertTrue(verify_password("securepass123", password_hash, salt))
        self.assertFalse(verify_password("wrongpass", password_hash, salt))

    def test_empty_password_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            hash_password("")


if __name__ == "__main__":
    unittest.main()
