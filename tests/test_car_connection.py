import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.obd_handler import OBDHandler

class TestCarConnection(unittest.TestCase):

    def setUp(self):
        self.handler = OBDHandler(simulation=False)

    @patch('src.obd_handler.obd')
    def test_successful_connection(self, mock_obd_lib):
        """Test that the app handles a successful USB connection correctly."""

        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_conn.port_name = "COM3"
        mock_conn.protocol_name.return_value = "ISO 15765-4"

        mock_cmd_rpm = MagicMock()
        mock_conn.supported_commands = {mock_cmd_rpm}

        mock_obd_lib.OBD.return_value = mock_conn
        mock_obd_lib.commands.RPM = mock_cmd_rpm

        result = self.handler.connect("COM3")

        self.assertTrue(result)
        self.assertEqual(self.handler.status, "Connected")
        self.assertIn(mock_cmd_rpm, self.handler.supported_commands)

    @patch('src.obd_handler.obd')
    def test_failed_connection(self, mock_obd_lib):
        """Test failure scenario."""
        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = False
        mock_obd_lib.OBD.return_value = mock_conn

        result = self.handler.connect("COM3")

        self.assertFalse(result)
        self.assertEqual(self.handler.status, "Failed")

    @patch('src.obd_handler.obd')
    def test_standard_query(self, mock_obd_lib):
        """Test reading a standard PID."""

        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_obd_lib.OBD.return_value = mock_conn

        mock_cmd_rpm = MagicMock()
        mock_conn.supported_commands = {mock_cmd_rpm}
        mock_obd_lib.commands.RPM = mock_cmd_rpm

        self.handler.connect()

        mock_response = MagicMock()
        mock_response.is_null.return_value = False
        mock_response.value.magnitude = 3500
        mock_conn.query.return_value = mock_response

        val = self.handler.query_sensor("RPM")

        self.assertEqual(val, 3500)

    @patch('src.obd_handler.obd')
    def test_pro_pack_custom_pid_math(self, mock_obd_lib):
        """Test custom PID logic (Headers + Math)."""

        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_obd_lib.OBD.return_value = mock_conn

        mock_obd_lib.commands.AT.SH = "ATSH"
        mock_obd_lib.commands.mode.return_value = "MODE"

        del mock_obd_lib.commands.TEST_OIL_TEMP

        self.handler.connect()

        fake_defs = {
            "TEST_OIL_TEMP": [
                "Test Oil", "C", True, True, 150,
                "221234", "7E0", "((A*256)+B)/100"
            ]
        }
        self.handler.set_pro_definitions(fake_defs)

        mock_response = MagicMock()
        mock_response.is_null.return_value = False
        mock_message = MagicMock()
        mock_message.data = b'\x0A\x14'

        mock_response.messages = [mock_message]
        mock_conn.query.return_value = mock_response

        result = self.handler.query_sensor("TEST_OIL_TEMP")

        self.assertTrue(mock_conn.query.call_count >= 1, "Query not called")

        self.assertEqual(result, 25.8)

    def test_formula_logic(self):
        """Test the internal math parser directly (no mocking needed)."""

        self.assertEqual(self.handler._calculate_formula("signed(A)", b'\xFF'), -1)
        self.assertEqual(self.handler._calculate_formula("signed(A)", b'\x7F'), 127)

        self.assertAlmostEqual(self.handler._calculate_formula("((A*256)+B)*0.1", b'\x01\xF4'), 50.0)

if __name__ == '__main__':
    unittest.main()