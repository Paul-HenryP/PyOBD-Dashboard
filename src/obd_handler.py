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
        self.inter_command_delay = 0.01

        self.pro_defs = {}

        self.supported_commands = set()

        self.sim_start_time = time.time()
        self.sim_speed = 0

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
            self.sim_start_time = time.time()
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

                self.supported_commands = self.connection.supported_commands
                self.log(f"Auto-Detected {len(self.supported_commands)} supported sensors.")
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
        self.supported_commands = set()

        self.log("Disconnected.")

    def check_supported(self, command_key):
        """Returns True if the sensor is supported by this specific car"""
        if self.simulation: return True
        if not self.is_connected(): return False

        if hasattr(obd.commands, command_key):
            cmd = getattr(obd.commands, command_key)
            return cmd in self.supported_commands

        if command_key in self.pro_defs:
            return True

        return False

    def query_sensor(self, command_key):
        if not self.is_connected(): return None
        if self.simulation: return self._simulate_data(command_key)

        if hasattr(obd.commands, command_key):
            cmd = getattr(obd.commands, command_key)

            if cmd not in self.supported_commands:
                return None

            time.sleep(self.inter_command_delay)
            try:
                response = self.connection.query(cmd)
                if response.is_null(): return None

                val = response.value.magnitude

                if isinstance(val, float):
                    return round(val, 2)
                return val
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
            allowed_names = {"min": min, "max": max, "abs": abs, "signed": self._signed}
            allowed_names.update(variables)
            result = eval(formula, {"__builtins__": {}}, allowed_names)
            return float(result)
        except:
            return None

    def _signed(self, val):
        if val > 127: return val - 256
        return val

    def get_dtc(self):
        """
        Performs a Deep Scan and returns specific categories.
        Returns a Dictionary: {'Category Name': [(Code, Description), ...]}
        """
        if not self.is_connected(): return {}

        self.log("Starting Deep DTC Scan...")

        dtc_groups = {
            "ENGINE - CONFIRMED (Permanent)": [],
            "ENGINE - PENDING (Intermittent)": [],
            "TRANSMISSION (TCU)": []
        }

        if self.simulation:
            return {
                "ENGINE - CONFIRMED (Permanent)": [("P0300", "Random Misfire")],
                "ENGINE - PENDING (Intermittent)": [("P0171", "System Too Lean")],
                "TRANSMISSION (TCU)": []
            }

        try:
            # --- 1. SCAN ENGINE (7E0) ---
            self.log("Scanning Engine...")
            self.connection.query(obd.commands.AT.SH + "7E0")

            # Confirmed (Mode 03)
            res_confirmed = self.connection.query(obd.commands.GET_DTC)
            if not res_confirmed.is_null() and res_confirmed.value:
                for code in res_confirmed.value:
                    dtc_groups["ENGINE - CONFIRMED (Permanent)"].append(code)

            # Pending (Mode 07)
            res_pending = self.connection.query(obd.commands.GET_CURRENT_DTC)
            if not res_pending.is_null() and res_pending.value:
                for code in res_pending.value:
                    dtc_groups["ENGINE - PENDING (Intermittent)"].append(code)

            # --- 2. SCAN TRANSMISSION (7E1 / 7E2) ---
            for target in ["7E1", "7E2"]:
                self.log(f"Scanning Transmission ({target})...")
                self.connection.query(obd.commands.AT.SH + target)
                time.sleep(0.1)

                res_tcu = self.connection.query(obd.commands.GET_DTC)

                if not res_tcu.is_null() and res_tcu.value:
                    for code in res_tcu.value:
                        dtc_groups["TRANSMISSION (TCU)"].append(code)

        except Exception as e:
            self.log(f"Scan Error: {e}")
        finally:
            self.connection.query(obd.commands.AT.SH + "7E0")

        self.log("Scan Complete.")
        return dtc_groups

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
        if name == 'RUN_TIME': return int(time.time() - self.sim_start_time)
        if name == 'BAROMETRIC_PRESSURE': return 101.3
        if name == 'FUEL_LEVEL': return 75.0
        if name == 'TIMING_ADVANCE': return random.randint(10, 25)

        if name == 'SPEED':
            change = random.randint(-5, 5)
            self.sim_speed += change
            if self.sim_speed < 0: self.sim_speed = 0
            if self.sim_speed > 160: self.sim_speed = 160
            return self.sim_speed

        if name == 'RPM':
            if self.sim_speed == 0:
                return 800 + random.randint(-20, 20)
            else:
                return (self.sim_speed * 30) + random.randint(0, 200)

        ranges = {
            'COOLANT_TEMP': (80, 105), 'CONTROL_MODULE_VOLTAGE': (13.8, 14.4),
            'ENGINE_LOAD': (15, 80), 'THROTTLE_POS': (0, 100),
            'INTAKE_TEMP': (20, 50), 'MAF': (2, 50)
        }

        if name in ranges:
            val = random.uniform(*ranges[name])
            if name == 'CONTROL_MODULE_VOLTAGE': return round(val, 2)
            return int(val) if val > 10 else round(val, 2)
        return random.randint(0, 100)