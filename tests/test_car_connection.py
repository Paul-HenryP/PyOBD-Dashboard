import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.obd_handler import OBDHandler


class TestCarConnection(unittest.TestCase):

    def setUp(self):
        self.handler = OBDHandler(simulation=False)

    @patch('src.obd_handler.obd')
    def test_successful_connection(self, mock_obd_lib):
        """Test that the app handles a successful USB connection correctly."""
        # 1. Setup Mock Connection
        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_conn.port_name = "COM3"
        mock_conn.protocol_name.return_value = "ISO 15765-4"

        # 2. Setup Mock Commands
        # We must create specific objects so we can verify they exist in the set
        mock_cmd_rpm = MagicMock(name='RPM')
        mock_cmd_speed = MagicMock(name='SPEED')

        # 3. Configure the connection to support these commands
        mock_conn.supported_commands = {mock_cmd_rpm, mock_cmd_speed}

        # 4. Link the mock to the library
        mock_obd_lib.OBD.return_value = mock_conn

        # 5. Run the code
        result = self.handler.connect("COM3")

        # 6. Assertions
        self.assertTrue(result)
        self.assertEqual(self.handler.status, "Connected")
        # Verify the list length to ensure copy worked
        self.assertEqual(len(self.handler.supported_commands), 2)

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
        """Test reading a standard PID like RPM."""
        # 1. Setup Connection
        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_obd_lib.OBD.return_value = mock_conn

        # 2. Setup RPM Command (CRITICAL STEP)
        # Create one mock object for RPM
        mock_cmd_rpm = MagicMock(name='RPM_COMMAND')

        # Tell the connection: "I support this object"
        mock_conn.supported_commands = {mock_cmd_rpm}

        # Tell the library: "When code asks for obd.commands.RPM, give them THIS object"
        mock_obd_lib.commands.RPM = mock_cmd_rpm

        # 3. Connect (This copies supported_commands to the handler)
        self.handler.connect()

        # Verify the setup: The command object in handler must match the library object
        self.assertIn(mock_cmd_rpm, self.handler.supported_commands)

        # 4. Setup Response
        mock_response = MagicMock()
        mock_response.is_null.return_value = False
        mock_response.value.magnitude = 3500
        mock_conn.query.return_value = mock_response

        # 5. Execute
        val = self.handler.query_sensor("RPM")

        # 6. Verify
        self.assertEqual(val, 3500)

    # Patch 'src.obd_handler.OBDCommand' because it is imported as 'from obd import OBDCommand'
    @patch('src.obd_handler.OBDCommand')
    @patch('src.obd_handler.obd')
    def test_pro_pack_custom_pid_math(self, mock_obd_lib, mock_obd_command):
        """Test custom PID logic."""
        # 1. Setup Connection
        mock_conn = MagicMock()
        mock_conn.is_connected.return_value = True
        mock_obd_lib.OBD.return_value = mock_conn

        # 2. Mock AT commands
        mock_obd_lib.commands.AT.SH = "ATSH"
        mock_obd_lib.commands.mode.return_value = "MODE"

        # 3. Ensure 'TEST_OIL_TEMP' is NOT seen as a standard command
        del mock_obd_lib.commands.TEST_OIL_TEMP

        self.handler.connect()

        # 4. Define Pro Sensor
        fake_defs = {
            "TEST_OIL_TEMP": [
                "Test Oil", "C", True, True, 150,
                "221234", "7E0", "((A*256)+B)/100"
            ]
        }
        self.handler.set_pro_definitions(fake_defs)

        # 5. Prepare Response
        mock_response = MagicMock()
        mock_response.is_null.return_value = False
        mock_message = MagicMock()
        mock_message.data = b'\x0A\x14'  # 2580
        mock_response.messages = [mock_message]
        mock_conn.query.return_value = mock_response

        # 6. Execute
        result = self.handler.query_sensor("TEST_OIL_TEMP")

        # 7. Verify
        self.assertTrue(mock_conn.query.call_count >= 1, "Query not called")
        self.assertEqual(result, 25.8)

    def test_formula_logic(self):
        self.assertEqual(self.handler._calculate_formula("signed(A)", b'\xFF'), -1)
        self.assertAlmostEqual(self.handler._calculate_formula("((A*256)+B)*0.1", b'\x01\xF4'), 50.0)


if __name__ == '__main__':
    unittest.main()