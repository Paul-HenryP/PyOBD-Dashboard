import obd
from obd.utils import bytes_to_int
import random
import time
import re


class OBDHandler:
    def __init__(self, simulation=False, log_callback=None):
        self.simulation = simulation
        self.connection = None
        self.status = "Disconnected"
        self.log_callback = log_callback
        self.inter_command_delay = 0.05

        self.pro_defs = {}

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        print(message)

    def set_pro_definitions(self, defs):
        self.pro_defs = defs

    def is_connected(self):
        return self.status == "Connected" or self.status == "Connected (SIMULATION)"

    def connect(self, port_name=None):
        if self.simulation:
            self.log("Attempting connection (SIMULATION)...")
            self.status = "Connected (SIMULATION)"
            self.log("SUCCESS: Simulation Mode Active")
            return True

        self.log(f"Attempting connection to {port_name if port_name else 'Auto-Scan'}...")

        try:
            if port_name and port_name != "Auto":
                self.connection = obd.OBD(portstr=port_name, fast=False, timeout=30)
            else:
                self.connection = obd.OBD(fast=False, timeout=30)

            if self.connection.is_connected():
                self.status = "Connected"
                self.log(f"SUCCESS: Connected to {self.connection.port_name}")
                self.log(f"Protocol: {self.connection.protocol_name()}")
                return True
            else:
                self.status = "Failed"
                self.log("ERROR: Interface found, but no connection to ECU.")
                return False
        except Exception as e:
            self.status = "Error"
            self.log(f"CRITICAL ERROR: {e}")
            return False

    def disconnect(self):
        self.log("Disconnecting...")
        if self.connection:
            self.connection.close()
            self.connection = None
        self.status = "Disconnected"
        self.log("Disconnected.")

    def query_sensor(self, command_key):
        if not self.is_connected(): return None
        if self.simulation: return self._simulate_data(command_key)

        if hasattr(obd.commands, command_key):
            cmd = getattr(obd.commands, command_key)
            time.sleep(self.inter_command_delay)
            try:
                response = self.connection.query(cmd)
                if response.is_null(): return None
                return response.value.magnitude
            except:
                return None

        elif command_key in self.pro_defs:
            return self._query_custom_pid(command_key)

        return None

    def _query_custom_pid(self, key):
        definition = self.pro_defs[key]
        if len(definition) < 8: return None

        pid_hex = definition[5]
        header_hex = definition[6]
        formula = definition[7]

        time.sleep(self.inter_command_delay)

        try:
            if header_hex:
                self.connection.query(obd.commands.AT.SH + header_hex)

            mode = pid_hex[:2]
            pid = pid_hex[2:]

            raw_response = self.connection.query(obd.commands.mode(mode) + pid)

            if raw_response.is_null(): return None
            if not raw_response.messages: return None
            data_bytes = raw_response.messages[0].data

            return self._calculate_formula(formula, data_bytes)

        except Exception as e:
            return None

    def _calculate_formula(self, formula, data_bytes):
        variables = {}
        for i, byte_val in enumerate(data_bytes):
            char_code = 65 + i
            if char_code > 90: break
            variables[chr(char_code)] = byte_val

        try:
            allowed_names = {"min": min, "max": max, "abs": abs}
            allowed_names.update(variables)
            result = eval(formula, {"__builtins__": {}}, allowed_names)
            return float(result)
        except:
            return None

    def get_dtc(self):
        if not self.is_connected(): return []
        self.log("Querying DTCs...")
        if self.simulation: return [("P0300", "Random/Multiple Cylinder Misfire")]

        time.sleep(0.2)
        res = self.connection.query(obd.commands.GET_DTC)
        return res.value if not res.is_null() else []

    def get_freeze_frame_snapshot(self, sensor_list):
        self.log("Reading Freeze Frame Data...")
        snapshot = {}
        if self.simulation:
            time.sleep(1)
            return {"RPM": 4520, "SPEED": 110, "DTC": "P0300"}

        if self.connection and self.connection.is_connected():
            for name in sensor_list:
                val = self.query_sensor(name)
                if val is not None:
                    snapshot[name] = val
        return snapshot

    def clear_dtc(self):
        self.log("Attempting to Clear DTCs...")
        if self.simulation:
            time.sleep(1)
            self.log("SIMULATION: Codes Cleared.")
            return True

        if self.connection and self.connection.is_connected():
            try:
                self.connection.query(obd.commands.CLEAR_DTC)
                self.log("Command Sent: CLEAR_DTC")
                return True
            except Exception as e:
                self.log(f"Clear Failed: {e}")
                return False
        return False

    def _simulate_data(self, name):
        ranges = {
            'RPM': (800, 5000), 'SPEED': (0, 130),
            'COOLANT_TEMP': (80, 110), 'CONTROL_MODULE_VOLTAGE': (12.8, 14.5),
            'ENGINE_LOAD': (15, 80), 'THROTTLE_POS': (0, 100),
            'INTAKE_TEMP': (20, 50), 'MAF': (2, 50),
            'FUEL_LEVEL': (0, 100), 'BAROMETRIC_PRESSURE': (95, 105),
            'TIMING_ADVANCE': (-10, 40), 'RUN_TIME': (0, 9999)
        }

        if name not in ranges:
            return random.randint(0, 100)

        if name == 'SPEED':
            return 0 if random.random() < 0.1 else random.randint(0, 120)

        if name in ranges:
            val = random.uniform(*ranges[name])
            return int(val) if val > 10 else round(val, 2)
        return 0