import unittest
import time
from src.obd_handler import OBDHandler


class TestOBDLogic(unittest.TestCase):

    def setUp(self):
        self.handler = OBDHandler(simulation=True)
        self.handler.connect()

    def test_connection_status(self):
        """Test if simulation connects successfully"""
        self.assertTrue(self.handler.connect())
        self.assertIn("Connected", self.handler.status)

    def test_standard_sensor_types(self):
        """Test that standard sensors return correct data types"""
        rpm = self.handler.query_sensor("RPM")
        self.assertIsInstance(rpm, int, "RPM should be an Integer")
        self.assertGreaterEqual(rpm, 0, "RPM should be positive")

        volts = self.handler.query_sensor("CONTROL_MODULE_VOLTAGE")
        self.assertIsInstance(volts, float, "Voltage should be a Float")

    def test_simulation_smart_logic(self):
        """Test that our specific simulation logic works"""
        run_time = self.handler.query_sensor("RUN_TIME")
        self.assertIsInstance(run_time, int)

        fuel = self.handler.query_sensor("FUEL_LEVEL")
        self.assertEqual(fuel, 75.0, "Simulation Fuel Level should be fixed at 75.0")

        baro = self.handler.query_sensor("BAROMETRIC_PRESSURE")
        self.assertAlmostEqual(baro, 101.3, delta=2, msg="Barometric pressure sim is out of range")

    def test_dtc_structure(self):
        """Test that diagnostic codes return a Dictionary (Updated for V1.1)"""
        codes = self.handler.get_dtc()
        self.assertIsInstance(codes, dict, "DTCs should be returned as a Dictionary groups")

        # Check if specific keys exist
        self.assertIn("ENGINE - CONFIRMED", codes)

        engine_codes = codes["ENGINE - CONFIRMED"]
        self.assertIsInstance(engine_codes, list)
        if len(engine_codes) > 0:
            self.assertEqual(len(engine_codes[0]), 2)  # Should be (Code, Description)

    # --- MATH TESTS ---

    def test_formula_calculation_simple(self):
        data = b'\x0A\x05'
        formula = "(A*256)+B"
        result = self.handler._calculate_formula(formula, data)
        self.assertEqual(result, 2565)

    def test_formula_calculation_signed(self):
        data = b'\xFF'
        formula = "signed(A)"
        result = self.handler._calculate_formula(formula, data)
        self.assertEqual(result, -1)


if __name__ == '__main__':
    unittest.main()