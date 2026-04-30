import customtkinter as ctk
from tkinter import filedialog, messagebox
import struct
import shutil
import os
import time


class SuzukiClusterTool(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PyOBD Professional - Odometer Sync Tool")
        self.geometry("600x550")
        ctk.set_appearance_mode("dark")

        self.file_path = None
        self.file_data = None
        self.chip_type = None
        self.multiplier = 16.0

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="#1F4B6D", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(header, text="SUZUKI DENSO CLUSTER SYNC", font=("Arial", 20, "bold"), text_color="white").pack(
            pady=15)

        self.frame_file = ctk.CTkFrame(self)
        self.frame_file.grid(row=1, column=0, padx=20, pady=20, sticky="ew")

        self.lbl_file = ctk.CTkLabel(self.frame_file, text="No EEPROM dump loaded.", font=("Consolas", 12))
        self.lbl_file.pack(pady=10)

        self.btn_load = ctk.CTkButton(self.frame_file, text="LOAD .BIN FILE", command=self.load_file,
                                      fg_color="#3B8ED0")
        self.btn_load.pack(pady=10)

        self.frame_calc = ctk.CTkFrame(self)
        self.frame_calc.grid(row=2, column=0, padx=20, pady=5, sticky="ew")

        ctk.CTkLabel(self.frame_calc, text="1. Verification", font=("Arial", 14, "bold")).grid(row=0, column=0,
                                                                                               columnspan=2, pady=10)

        ctk.CTkLabel(self.frame_calc, text="Current Mileage on LCD (km):").grid(row=1, column=0, padx=10, pady=5,
                                                                                sticky="e")
        self.entry_current = ctk.CTkEntry(self.frame_calc, placeholder_text="e.g. 45200")
        self.entry_current.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        self.btn_verify = ctk.CTkButton(self.frame_calc, text="VERIFY ALGORITHM", fg_color="#E04F5F",
                                        command=self.verify_dump, state="disabled")
        self.btn_verify.grid(row=2, column=0, columnspan=2, pady=15)

        self.frame_write = ctk.CTkFrame(self)
        self.frame_write.grid(row=3, column=0, padx=20, pady=20, sticky="ew")

        ctk.CTkLabel(self.frame_write, text="2. Synchronization", font=("Arial", 14, "bold")).grid(row=0, column=0,
                                                                                                   columnspan=2,
                                                                                                   pady=10)

        ctk.CTkLabel(self.frame_write, text="Target Mileage (km):").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.entry_target = ctk.CTkEntry(self.frame_write, placeholder_text="e.g. 24000", state="disabled")
        self.entry_target.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        self.btn_patch = ctk.CTkButton(self.frame_write, text="GENERATE PATCHED FILE", fg_color="green",
                                       command=self.generate_patch, state="disabled")
        self.btn_patch.grid(row=2, column=0, columnspan=2, pady=15)

    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("Binary Files", "*.bin")])
        if not path: return

        try:
            with open(path, 'rb') as f:
                self.file_data = bytearray(f.read())
        except Exception as e:
            messagebox.showerror("Error", f"Could not read file: {e}")
            return

        self.file_path = path
        size = len(self.file_data)

        if size == 128:
            self.chip_type = "93C46"
        elif size == 256:
            self.chip_type = "93C56"
        else:
            messagebox.showerror("Invalid File", f"Expected 128 or 256 bytes for SV650. Got {size} bytes.")
            self.file_data = None
            return

        self.lbl_file.configure(text=f"Loaded: {os.path.basename(path)} | Chip: {self.chip_type}", text_color="green")
        self.btn_verify.configure(state="normal")
        self.entry_target.configure(state="disabled")
        self.btn_patch.configure(state="disabled")

    def verify_dump(self):
        if not self.file_data: return

        try:
            current_km = int(self.entry_current.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "Please enter valid numbers for the current mileage.")
            return

        w1 = struct.unpack('<H', self.file_data[0:2])[0]
        w2 = struct.unpack('<H', self.file_data[2:4])[0]
        w3 = struct.unpack('<H', self.file_data[4:6])[0]

        if not (w1 == w2 == w3):
            msg = f"Memory redundancy check failed.\nWord1: {hex(w1)}\nWord2: {hex(w2)}\nWord3: {hex(w3)}\nThis is likely not a valid Suzuki Denso dump."
            messagebox.showerror("Verification Failed", msg)
            return

        calc_hex = w1 ^ 0xFFFF

        if current_km > 0 and calc_hex > 0:
            detected_multiplier = current_km / calc_hex
        else:
            detected_multiplier = 0

        # Suzuki SV650 Denso uses ~16.0 multiplier (sometimes 10 depending on MPH/KMH region)
        if 15.5 < detected_multiplier < 16.5:
            self.multiplier = 16.0
        elif 9.5 < detected_multiplier < 10.5:
            self.multiplier = 10.0
        else:
            msg = f"Mathematical mismatch. Calculated multiplier: {detected_multiplier:.2f}\nThis doesn't match standard Denso architecture. File may be corrupt."
            messagebox.showerror("Verification Failed", msg)
            return

        estimated_km = int(calc_hex * self.multiplier)
        diff = abs(current_km - estimated_km)

        if diff > 30:
            msg = f"Tolerance exceeded.\nYou entered: {current_km} km\nFile calculated: {estimated_km} km\nAre you sure you typed the exact dash reading?"
            messagebox.showwarning("Warning", msg)
            return

        messagebox.showinfo("Verified",
                            f"Algorithm Verified!\nBase Hex: {hex(calc_hex)}\nCalculated Mileage: {estimated_km} km\nReady to patch.")

        self.entry_target.configure(state="normal")
        self.btn_patch.configure(state="normal")

    def generate_patch(self):
        try:
            target_km = int(self.entry_target.get().strip())
        except ValueError:
            messagebox.showerror("Input Error", "Please enter a valid target mileage.")
            return

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.file_path.replace('.bin', '')}_BACKUP_{timestamp}.bin"
        try:
            shutil.copy(self.file_path, backup_path)
        except Exception as e:
            messagebox.showerror("Backup Failed", f"Could not create safety backup: {e}")
            return

        new_base = int(target_km / self.multiplier)
        new_hex = new_base ^ 0xFFFF
        new_bytes = struct.pack('<H', new_hex)

        patched_data = bytearray(self.file_data)
        patched_data[0:2] = new_bytes
        patched_data[2:4] = new_bytes
        patched_data[4:6] = new_bytes

        patched_path = self.file_path.replace('.bin', f'_SYNCED_{target_km}km.bin')

        try:
            with open(patched_path, 'wb') as f:
                f.write(patched_data)
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save patched file: {e}")
            return

        msg = f"Successfully generated patched file:\n\n{os.path.basename(patched_path)}\n\nA safety backup of your original file was also saved.\nYou may now flash the SYNCED file using AsProgrammer."
        messagebox.showinfo("Success", msg)


if __name__ == "__main__":
    app = SuzukiClusterTool()
    app.mainloop()