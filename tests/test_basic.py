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
        """Test that our specific simulation logic works (not just random numbers)"""

        run_time = self.handler.query_sensor("RUN_TIME")
        self.assertIsInstance(run_time, int)

        fuel = self.handler.query_sensor("FUEL_LEVEL")
        self.assertEqual(fuel, 75, "Simulation Fuel Level should be fixed at 75")

        baro = self.handler.query_sensor("BAROMETRIC_PRESSURE")
        self.assertAlmostEqual(baro, 101, delta=2, msg="Barometric pressure sim is out of range")

    def test_dtc_structure(self):
        """Test that diagnostic codes return a list"""
        codes = self.handler.get_dtc()
        self.assertIsInstance(codes, list)
        if len(codes) > 0:
            self.assertEqual(len(codes[0]), 2)

    def test_formula_calculation_simple(self):
        """Test basic math: (A * 256) + B"""

        data = b'\x0A\x05'
        formula = "(A*256)+B"
        result = self.handler._calculate_formula(formula, data)
        self.assertEqual(result, 2565)

    def test_formula_calculation_signed(self):
        """Test signed integer logic"""

        data = b'\xFF'
        formula = "signed(A)"
        result = self.handler._calculate_formula(formula, data)
        self.assertEqual(result, -1)

    def test_formula_bad_math(self):
        """Test that bad formulas do not crash the app"""
        data = b'\x0A'

        result = self.handler._calculate_formula("A/0", data)
        self.assertIsNone(result, "Division by zero should return None, not crash")

        result = self.handler._calculate_formula("((A*256", data)
        self.assertIsNone(result, "Bad syntax should return None")

if __name__ == '__main__':
    unittest.main()