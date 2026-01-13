import obd
import random
import time


class OBDHandler:
    def __init__(self, simulation=False, log_callback=None):
        self.simulation = simulation
        self.connection = None
        self.status = "Disconnected"
        self.log_callback = log_callback
        self.inter_command_delay = 0.05

    def log(self, message):
        if self.log_callback:
            self.log_callback(message)
        print(message)

    def is_connected(self):
        return self.status == "Connected" or self.status == "Connected (SIMULATION)"

    def connect(self):
        self.log("Attempting connection...")
        if self.simulation:
            self.status = "Connected (SIMULATION)"
            self.log("SUCCESS: Simulation Mode Active")
            return True

        try:
            self.connection = obd.OBD(fast=False)
            if self.connection.is_connected():
                self.status = "Connected"
                self.log(f"SUCCESS: Connected to {self.connection.port_name}")
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

    def query_sensor(self, command_name):
        if not self.is_connected(): return None
        if self.simulation: return self._simulate_data(command_name)

        if hasattr(obd.commands, command_name):
            cmd = getattr(obd.commands, command_name)
            time.sleep(self.inter_command_delay)
            try:
                response = self.connection.query(cmd)
                if response.is_null(): return None
                return response.value.magnitude
            except:
                return None
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
                if hasattr(obd.commands, name):
                    cmd = getattr(obd.commands, name)
                    time.sleep(self.inter_command_delay)
                    response = self.connection.query(cmd, mode=2)
                    if not response.is_null():
                        snapshot[name] = response.value.magnitude
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
            'RPM': (800, 5000),
            'SPEED': (0, 130),
            'COOLANT_TEMP': (80, 110),
            'CONTROL_MODULE_VOLTAGE': (12.8, 14.5),
            'ENGINE_LOAD': (15, 80),
            'THROTTLE_POS': (0, 100),
            'INTAKE_TEMP': (20, 50),
            'MAF': (2, 50),
            'FUEL_LEVEL': (0, 100),
            'BAROMETRIC_PRESSURE': (95, 105),
            'TIMING_ADVANCE': (-10, 40),
            'RUN_TIME': (0, 9999)
        }

        if name == 'SPEED':
            return 0 if random.random() < 0.1 else random.randint(0, 120)

        if name in ranges:
            val = random.uniform(*ranges[name])
            return int(val) if val > 10 else round(val, 2)
        return 0