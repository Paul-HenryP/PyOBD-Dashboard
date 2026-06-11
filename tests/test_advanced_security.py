import unittest
import sys
import os

# Ensure src is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.can_handler import CanHandler


class TestAdvancedSecurity(unittest.TestCase):

    def setUp(self):
        self.can = CanHandler()

    def test_odd_hex_correction_header(self):
        """Safety: The handler MUST pad short or weird headers correctly (11-bit or 29-bit)."""
        # A 2-character header should pad to 3 (e.g. 1F -> 01F)
        clean_header_short = self.can._sanitize_header("1F")
        self.assertEqual(clean_header_short, "01F")

        # A 5-character header should pad to 8 (e.g. 1FFFF -> 0001FFFF)
        clean_header_mid = self.can._sanitize_header("1FFFF")
        self.assertEqual(clean_header_mid, "0001FFFF")

        # An 8-character header should stay 8
        clean_header_long = self.can._sanitize_header("1FFFFFFF")
        self.assertEqual(clean_header_long, "1FFFFFFF")

    def test_odd_hex_correction_data(self):
        """Safety: The handler MUST pad odd-length data to prevent alignment errors."""
        # "FFF" is 1.5 bytes, must become "0FFF" (2 bytes)
        clean_data = self.can._sanitize_data("FFF")
        self.assertEqual(clean_data, "0FFF")

        clean_data_2 = self.can._sanitize_data("A")
        self.assertEqual(clean_data_2, "0A")

    def test_invalid_characters(self):
        """Safety: The handler MUST strip non-hex characters to prevent injection."""
        # 'G', 'X', 'Z' are not valid hex. It should strip them and leave '12'
        clean_data = self.can._sanitize_data("GGXX12Z")
        self.assertEqual(clean_data, "12")

        clean_header = self.can._sanitize_header("7E8!@#")
        self.assertEqual(clean_header, "7E8")


if __name__ == '__main__':
    unittest.main()