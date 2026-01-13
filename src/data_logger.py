import csv
import time
import os


class DataLogger:
    def __init__(self):
        self.enabled = True
        self.log_dir = os.path.join(os.getcwd(), "logs")
        self.current_filepath = None
        self.active_headers = []

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def start_new_log(self, sensor_keys):
        if not sensor_keys:
            return

        self.active_headers = sensor_keys
        filename = f"trip_log_{int(time.time())}.csv"
        self.current_filepath = os.path.join(self.log_dir, filename)

        try:
            with open(self.current_filepath, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["Timestamp"] + sensor_keys)
        except Exception as e:
            print(f"Logging Init Error: {e}")

    def write_row(self, data_dict):
        if not self.enabled or not self.current_filepath:
            return

        try:
            row_data = [time.strftime("%H:%M:%S")]
            for key in self.active_headers:
                row_data.append(data_dict.get(key, ""))

            with open(self.current_filepath, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(row_data)
        except Exception:
            pass

    def set_directory(self, new_path):
        if os.path.isdir(new_path):
            self.log_dir = new_path
            return True
        return False

    def toggle_logging(self, is_enabled):
        self.enabled = is_enabled