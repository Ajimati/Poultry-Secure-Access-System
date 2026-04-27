import unittest

from src.config import staff_id_storage_key


class PathSafetyTests(unittest.TestCase):
    def test_staff_id_is_sanitized_for_storage(self) -> None:
        self.assertEqual(staff_id_storage_key("2026/015"), "2026_015")
        self.assertEqual(staff_id_storage_key(" PF-01 "), "PF-01")
        self.assertEqual(staff_id_storage_key("A\\B:C*D?"), "A_B_C_D")


if __name__ == "__main__":
    unittest.main()
