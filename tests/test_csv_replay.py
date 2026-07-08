import unittest
import tempfile
import os
import time
from src.obd_handler import OBDHandler


class TestCSVReplay(unittest.TestCase):
    def setUp(self):
        """
        Initialize the test environment.
        Instantiates the OBDHandler and generates temporary valid and invalid CSV files for testing.
        """
        self.obd = OBDHandler()

        # Generate a valid PyOBD log file mimicking the DataLogger output format
        self.valid_csv = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', newline='')
        self.valid_csv.write("Timestamp,RPM,SPEED\n")
        self.valid_csv.write("12:00:00,850,0\n")
        self.valid_csv.write("12:00:01,1200,15\n")
        self.valid_csv.close()

        # Generate an invalid CSV file (e.g., standard database dump lacking expected telemetry headers)
        self.invalid_csv = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', newline='')
        self.invalid_csv.write("Company Name,Valuation,Founder\n")
        self.invalid_csv.write("Superangel,10M,John Doe\n")
        self.invalid_csv.close()

    def tearDown(self):
        """
        Clean up temporary resources after test execution to prevent filesystem clutter.
        Includes a retry mechanism for Windows, as the background parsing thread
        might take up to 0.2s to release the file handle after stop_replay() is called.
        """
        self.obd.stop_replay()

        for file_name in [self.valid_csv.name, self.invalid_csv.name]:
            for _ in range(10):  # Retry up to 10 times (1 second total)
                try:
                    if os.path.exists(file_name):
                        os.remove(file_name)
                    break  # Success, exit the retry loop
                except PermissionError:
                    # Thread is still holding the file, wait 0.1s and try again
                    time.sleep(0.1)

    def test_invalid_csv_rejected(self):
        """
        Verify that the replay initialization fails gracefully when provided
        with a CSV file that lacks the required 'Timestamp' header.
        """
        success = self.obd.start_replay(self.invalid_csv.name)

        # Assert initialization returns False for invalid schema
        self.assertFalse(success, "Expected start_replay to return False for an invalid CSV file.")

        # Verify the internal state remains disconnected and replay mode is not triggered
        self.assertEqual(self.obd.status, "Disconnected")
        self.assertFalse(self.obd.replay_mode)

    def test_valid_csv_accepted(self):
        """
        Verify that a correctly formatted PyOBD log file is successfully loaded,
        and the background thread parses the telemetry data correctly.
        """
        success = self.obd.start_replay(self.valid_csv.name)

        # Assert initialization returns True for a valid schema
        self.assertTrue(success, "Expected start_replay to return True for a valid PyOBD CSV log.")
        self.assertTrue(self.obd.replay_mode)
        self.assertEqual(self.obd.status, "Connected (REPLAY)")

        # Allow the background I/O thread sufficient time to read and parse the first data row
        time.sleep(0.3)

        # Query the simulated sensor data and validate type and value mapping
        rpm = self.obd.query_sensor("RPM")
        self.assertIsNotNone(rpm, "Failed to retrieve RPM data from the replay buffer.")
        self.assertIn(rpm, [850.0, 1200.0], f"Retrieved unexpected RPM value: {rpm}")

        # Terminate the background thread and reset the handler state
        self.obd.stop_replay()
        self.assertFalse(self.obd.replay_active)


if __name__ == "__main__":
    unittest.main()