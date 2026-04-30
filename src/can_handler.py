import serial
import threading
import time
import random

class CanHandler:
    def __init__(self):
        self.ser = None
        self.is_sniffing = False
        self.msg_callback = None
        self.simulation = False
        self.active_filter = ""

        self.sim_ids = ["290", "1C0", "4B1", "350", "7E8"]
        self.sim_data = {id: [0] * 8 for id in self.sim_ids}

    def connect(self, port_name, baudrate=38400):
        if port_name == "Demo Mode":
            self.simulation = True
            return True

        self.simulation = False
        try:
            if self.ser:
                try:
                    self.ser.close()
                except:
                    pass

            self.ser = serial.Serial(port_name, baudrate, timeout=1)

            commands = [
                b"AT Z\r", b"AT E1\r", b"AT L1\r", b"AT H1\r",
                b"AT SP 6\r", b"AT CAF 0\r"
            ]

            for cmd in commands:
                self.ser.write(cmd)
                time.sleep(0.1)
                self.ser.read_all()

            return True
        except Exception as e:
            print(f"CAN Connect Error: {e}")
            self.ser = None
            return False

    def disconnect(self):
        self.is_sniffing = False
        self.simulation = False
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
            self.ser = None

    def start_sniffing(self, filter_id="", callback=None):
        self.msg_callback = callback
        self.is_sniffing = True
        self.active_filter = filter_id.strip()

        if self.simulation:
            threading.Thread(target=self._sim_sniff_loop, daemon=True).start()
        else:
            if self.ser and self.ser.is_open:
                try:
                    if self.active_filter and len(self.active_filter) == 3:
                        self.ser.write(f"AT CRA {self.active_filter}\r".encode())
                    else:
                        self.ser.write(b"AT CRA\r")

                    time.sleep(0.1)
                    self.ser.read_all()
                    self.ser.write(b"AT MA\r")
                    threading.Thread(target=self._sniff_loop, daemon=True).start()
                except:
                    self.stop_sniffing()

    def stop_sniffing(self):
        self.is_sniffing = False
        if not self.simulation and self.ser and self.ser.is_open:
            try:
                self.ser.write(b"\r")
            except:
                pass

    def _sniff_loop(self):
        while self.is_sniffing and self.ser and self.ser.is_open:
            try:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()

                if "BUFFER FULL" in line:
                    if self.msg_callback:
                        self.msg_callback("⚠️ ERROR: ELM327 BUFFER FULL. Stopping. Use a Filter!")
                    self.is_sniffing = False
                    break

                if line and self.msg_callback:
                    self.msg_callback(line)
            except Exception:
                self.is_sniffing = False
                break

    def _sim_sniff_loop(self):
        while self.is_sniffing:
            if self.active_filter:
                can_id = self.active_filter
                if can_id not in self.sim_data:
                    self.sim_data[can_id] = [0] * 8
            else:
                can_id = random.choice(self.sim_ids)

            if random.random() > 0.5:
                idx = random.randint(0, 7)
                self.sim_data[can_id][idx] = random.randint(0, 255)

            data_str = " ".join([f"{b:02X}" for b in self.sim_data[can_id]])
            line = f"{can_id} {data_str}"

            if self.msg_callback:
                self.msg_callback(line)

            time.sleep(0.05)

    def _sanitize_hex(self, input_str):
        if not input_str: return ""
        clean = "".join([c for c in input_str.upper() if c in "0123456789ABCDEF"])

        if len(clean) % 2 != 0:
            clean = "0" + clean

        return clean

    def inject_frame(self, can_id, data):
        clean_id = self._sanitize_hex(can_id)
        if len(clean_id) % 2 != 0 and len(clean_id) < 3:
            clean_id = "0" + clean_id

        clean_data = self._sanitize_hex(data)

        if not clean_id or not clean_data:
            return "Error: Invalid Hex"

        if self.simulation:
            time.sleep(0.1)
            return "OK (Simulated)"

        if not self.ser: return "Error: No Serial"

        try:
            self.stop_sniffing()
            time.sleep(0.1)
            self.ser.read_all()
            self.ser.write(f"AT SH {clean_id}\r".encode())
            time.sleep(0.05)
            self.ser.write(f"{clean_data}\r".encode())
            time.sleep(0.05)
            return self.ser.read_all().decode('utf-8', errors='ignore')
        except Exception:
            self.disconnect()
            return "Error: Hardware Failure"