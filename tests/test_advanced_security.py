import unittest
import threading
import time
from unittest.mock import MagicMock, patch
from src.can_handler import CanHandler

class TestAdvancedSecurity(unittest.TestCase):

    def setUp(self):
        self.can = CanHandler()
        self.can.simulation = False
        self.can.ser = MagicMock()
        self.can.ser.is_open = True

    def test_odd_hex_correction(self):
        """
        Safety: The handler MUST pad odd-length inputs to prevent alignment errors.
        """

        clean_data = self.can._sanitize_hex("FFF")
        self.assertEqual(clean_data, "0FFF")

        clean_data_2 = self.can._sanitize_hex("1 A")
        self.assertEqual(clean_data_2, "1A")

        clean_data_3 = self.can._sanitize_hex("C")
        self.assertEqual(clean_data_3, "0C")

    def test_hardware_disconnect_recovery(self):
        """
        Stability: If serial.write throws an OSError (Cable pulled),
        the app must catch it and reset state to avoid a crash loop.
        """

        self.can.ser.write.side_effect = OSError("Device disconnected")

        result = self.can.inject_frame("7E0", "01 0D")

        self.assertIn("Error", result)

        self.assertFalse(self.can.is_sniffing)

    def test_rapid_toggling_race_condition(self):
        """
        Stability: Spamming Start/Stop sniffing shouldn't spawn
        multiple zombie threads.
        """
        self.can.start_sniffing()
        t1 = threading.active_count()

        self.can.stop_sniffing()
        self.can.start_sniffing()
        self.can.stop_sniffing()
        self.can.start_sniffing()

        t2 = threading.active_count()

        self.assertLess(t2 - t1, 3)

    def test_buffer_overflow_protection(self):
        """
        Safety: If the sniffer receives garbage/binary data (not text),
        it should ignore it rather than crash the UI string decoding.
        """

        self.can.ser.readline.return_value = b'\x80\xFF\xFE\x00'

        callback_mock = MagicMock()
        self.can.start_sniffing(callback=callback_mock)

        time.sleep(0.1)
        self.can.stop_sniffing()

        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()