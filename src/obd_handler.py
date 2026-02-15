import obd
from obd import OBDCommand
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
    
    def _parse_host_port(self, s):
        if s is None:
            return None
        m = re.match(r"^\s*([^\s:]+)\s*:\s*(\d{1,5})\s*$", s)
        if m is None:
            return None
        host = m.group(1)
        port = int(m.group(2))
        if 0 < port and port < 65536:
            return host, port
        return None
    
    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        print(message)

    def set_pro_definitions(self, defs):
        self.pro_defs = defs

    def is_connected(self):
        return self.status == "Connected" or self.status == "Connected (SIMULATION)"

    def connect(self, port_name=None, baudrate=115200):
        if self.simulation:
            self.log("Attempting connection (SIMULATION)...")
            self.status = "Connected (SIMULATION)"
            self.sim_start_time = time.time()
            self.log("SUCCESS: Simulation Mode Active")
            return True

        self.log(f"Attempting connection to {port_name if port_name else 'Auto-Scan'}...")

        try:
            
            hp = self._parse_host_port(port_name)

            if hp is not None:
                host, port = hp
                portstr = f"socket://{host}:{port}"
                self.connection = obd.OBD(portstr=portstr, fast=False, timeout=30, baudrate=baudrate)
            else:
                if port_name and port_name != "Auto":
                    self.connection = obd.OBD(portstr=port_name, fast=False, timeout=30, baudrate=baudrate)
                else:
                    self.connection = obd.OBD(fast=False, timeout=30, baudrate=baudrate)

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
        if self.simulation: return True
        if not self.is_connected(): return False

        if hasattr(obd.commands, command_key):
            cmd = getattr(obd.commands, command_key)
            return cmd in self.supported_commands

        if command_key in self.pro_defs:
            return True

        return False

    def _set_header(self, header_hex):
        if not header_hex: return
        try:
            cmd = OBDCommand("SET_HEADER", "AT SH " + header_hex, b"", lambda m: m)
            self.connection.query(cmd, force=True)
        except Exception:
            pass

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
                self._set_header(header_hex)

            mode = pid_hex[:2]
            pid = pid_hex[2:]

            cmd = OBDCommand("CUSTOM_PID", mode + pid, b"", lambda m: m)
            raw_response = self.connection.query(cmd, force=True)

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

    def _decode_uds_dtc(self, byte1, byte2, byte3):
        """Converts 3-byte UDS hex to standard P/U/B/C code"""

        type_bits = (byte1 & 0xC0) >> 6
        prefix = {0: "P", 1: "C", 2: "B", 3: "U"}[type_bits]

        second_char = (byte1 & 0x30) >> 4

        rest_of_byte1 = byte1 & 0x0F

        hex_code = f"{prefix}{second_char}{rest_of_byte1:X}{byte2:02X}{byte3:02X}"
        return hex_code.upper()

    def _get_uds_dtcs(self, target_header="7E0"):
        """EXPERIMENTAL: Scan for UDS Service 19 faults"""
        codes = []
        try:
            self.log(f"Attempting UDS (Service 19) Scan on {target_header}...")
            self._set_header(target_header)
            time.sleep(0.1)

            cmd = OBDCommand("UDS_SCAN", "19 02 FF", b"", lambda m: m)
            response = self.connection.query(cmd, force=True)

            if not response.is_null() and response.messages:
                data = response.messages[0].data

                if len(data) > 0 and data[0] == 0x59:
                    self.log(f"UDS RAW DATA: {data.hex()}")

                    i = 3
                    while i + 3 < len(data):
                        b1 = data[i]
                        b2 = data[i + 1]
                        b3 = data[i + 2]
                        status = data[i + 3]

                        if status & 0x09:  # 0x01 (Current) or 0x08 (Confirmed)
                            code_str = self._decode_uds_dtc(b1, b2, b3)
                            codes.append((code_str, f"UDS Extended (Status: {status:02X})"))

                        i += 4
                elif len(data) > 0 and data[0] == 0x7F:
                    self.log(f"UDS Not Supported by this module (Response: {data.hex()})")
            else:
                self.log("No response to UDS Scan.")

        except Exception as e:
            self.log(f"UDS Logic Error: {e}")

        return codes

    def get_dtc(self):
        if not self.is_connected(): return {}
        self.log("Starting Deep DTC Scan...")

        dtc_groups = {
            "ENGINE - CONFIRMED": [],
            "ENGINE - PENDING": [],
            "UDS / EXTENDED (Experimental)": [],

            "TRANSMISSION": []
        }

        if self.simulation:
            return {"ENGINE - CONFIRMED": [("P0300", "Random Misfire")]}

        try:

            self.log("Scanning Engine (Standard)...")
            self._set_header("7E0")

            res_conf = self.connection.query(obd.commands.GET_DTC, force=True)
            if not res_conf.is_null() and res_conf.value:
                for c in res_conf.value: dtc_groups["ENGINE - CONFIRMED"].append(c)

            res_pend = self.connection.query(obd.commands.GET_CURRENT_DTC, force=True)
            if not res_pend.is_null() and res_pend.value:
                for c in res_pend.value: dtc_groups["ENGINE - PENDING"].append(c)

            uds_codes = self._get_uds_dtcs("7E0")
            for c in uds_codes:

                is_duplicate = any(existing[0] == c[0] for existing in dtc_groups["ENGINE - CONFIRMED"])
                if not is_duplicate:
                    dtc_groups["UDS / EXTENDED (Experimental)"].append(c)

            self.log("Scanning Trans (Standard)...")
            self._set_header("7E1")
            res_tcu = self.connection.query(obd.commands.GET_DTC, force=True)
            if not res_tcu.is_null() and res_tcu.value:
                for c in res_tcu.value: dtc_groups["TRANSMISSION"].append(c)

        except Exception as e:
            self.log(f"Scan Critical Error: {e}")
        finally:
            self._set_header("7E0")

        self.log("Scan Complete.")
        return dtc_groups

    def get_freeze_frame_snapshot(self, sensor_list):
        self.log("Reading Freeze Frame Data...")
        snapshot = {}
        if self.simulation:
            for name in sensor_list: snapshot[name] = self._simulate_data(name)
            return snapshot

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
            return True

        if self.connection and self.connection.is_connected():
            try:

                self._set_header("7E0")
                self.connection.query(obd.commands.CLEAR_DTC)

                self._set_header("7E1")
                self.connection.query(obd.commands.CLEAR_DTC)
                self._set_header("7E0")
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
        if name == 'SPEED': return random.randint(0, 120)
        if name == 'RPM': return 800 + random.randint(0, 500)

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