import customtkinter as ctk
import json
import os
import time
from tkinter import filedialog, messagebox
from collections import deque 

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from data_logger import DataLogger
from config_manager import ConfigManager
from diagnostic_engine import DiagnosticEngine

# --- 1. DEFINE STANDARD (FREE) SENSORS ---
STANDARD_SENSORS = {
    "RPM": ("Engine RPM", "", True, True, 6000),
    "SPEED": ("Vehicle Speed", "km/h", True, True, 160),
    "COOLANT_TEMP": ("Coolant Temp", "°C", True, True, 120),
    "CONTROL_MODULE_VOLTAGE": ("Voltage", "V", True, False, 16),
    "ENGINE_LOAD": ("Engine Load", "%", True, False, 100),
    "THROTTLE_POS": ("Throttle Pos", "%", False, True, 100),
    "INTAKE_TEMP": ("Intake Air Temp", "°C", False, False, 80),
    "MAF": ("MAF Air Flow", "g/s", False, False, 200),
    "FUEL_LEVEL": ("Fuel Level", "%", False, False, 100),
    "BAROMETRIC_PRESSURE": ("Barometric", "kPa", False, False, 200),
    "TIMING_ADVANCE": ("Timing Adv", "°", False, False, 60),
    "RUN_TIME": ("Run Time", "sec", False, False, 3600)
}

# --- 2. PRO PACK LOADER ---
# Checks for external JSON file to unlock extra sensors
PRO_FILE = "pro_definitions.json"
AVAILABLE_SENSORS = STANDARD_SENSORS.copy()

if os.path.exists(PRO_FILE):
    try:
        with open(PRO_FILE, 'r') as f:
            pro_data = json.load(f)
            # Expected format in JSON: 
            # "SENSOR_KEY": ["Name", "Unit", ShowBool, LogBool, MaxLimit, "PID", "HEADER"]
            
            for key, val in pro_data.items():
                # We slice [:5] to ensure we only get UI data (Name, Unit, Defaults, Limit)
                # The Handler would use indices [5] and [6] for the actual communication logic later
                AVAILABLE_SENSORS[key] = tuple(val[:5])
                
        print(f"✅ PRO MODE ACTIVE: Loaded {len(pro_data)} extra sensors from {PRO_FILE}")
    except Exception as e:
        print(f"❌ Error loading Pro Pack: {e}")
else:
    print("ℹ️ Standard Mode Active. (No pro_definitions.json found)")


class DashboardApp(ctk.CTk):
    def __init__(self, obd_handler):
        super().__init__()
        self.obd = obd_handler
        self.logger = DataLogger()
        self.obd.log_callback = self.append_debug_log
        
        self.config = ConfigManager.load_config()
        self.sensor_state = {} 

        # GRAPH DATA STORAGE (Last 60 points)
        self.history_rpm = deque([0]*60, maxlen=60)
        self.history_speed = deque([0]*60, maxlen=60)

        # Window Setup
        self.title("PyOBD Professional - Ultimate Edition")
        self.geometry("1100x800") 
        ctk.set_appearance_mode("dark")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.tab_dash = self.tabview.add("Dashboard")
        self.tab_graph = self.tabview.add("Live Graph")
        self.tab_diag = self.tabview.add("Diagnostics")
        self.tab_settings = self.tabview.add("Settings")
        self.tab_debug = self.tabview.add("Debug Log")
        
        self._init_sensor_state()
        self._setup_dashboard_tab()
        self._setup_graph_tab()
        self._setup_diagnostics_tab()
        self._setup_settings_tab()
        self._setup_debug_tab()
        
        if "log_dir" in self.config:
            self.logger.set_directory(self.config["log_dir"])
            self.lbl_path.configure(text=f"Save Path: {self.logger.log_dir}")
        
        self.rebuild_dashboard_grid()
        self.update_loop()

    def _init_sensor_state(self):
        saved_sensors = self.config.get("sensors", {})
        for cmd, (name, unit, def_show, def_log, def_limit) in AVAILABLE_SENSORS.items():
            saved = saved_sensors.get(cmd, {})
            self.sensor_state[cmd] = {
                "name": name, "unit": unit,
                "show_var": ctk.BooleanVar(value=saved.get("show", def_show)),
                "log_var": ctk.BooleanVar(value=saved.get("log", def_log)),
                "limit_var": ctk.StringVar(value=str(saved.get("limit", def_limit))),
                "widget_value_label": None,
                "widget_progress_bar": None 
            }

    # --- DASHBOARD TAB ---
    def _setup_dashboard_tab(self):
        self.frame_controls = ctk.CTkFrame(self.tab_dash, height=50)
        self.frame_controls.pack(fill="x", padx=10, pady=5)
        self.btn_connect = ctk.CTkButton(self.frame_controls, text="CONNECT", fg_color="green", command=self.toggle_connection)
        self.btn_connect.pack(pady=10)
        self.dash_scroll = ctk.CTkScrollableFrame(self.tab_dash)
        self.dash_scroll.pack(fill="both", expand=True, padx=5, pady=5)

    def rebuild_dashboard_grid(self):
        for widget in self.dash_scroll.winfo_children(): widget.destroy()
        active_sensors = [k for k, v in self.sensor_state.items() if v["show_var"].get()]
        cols = 3
        for i, cmd in enumerate(active_sensors):
            row = i // cols; col = i % cols
            
            # Card Frame
            card = ctk.CTkFrame(self.dash_scroll)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
            self.dash_scroll.grid_columnconfigure(col, weight=1)
            
            # Title
            title = f"{self.sensor_state[cmd]['name']}"
            if self.sensor_state[cmd]['unit']: title += f" ({self.sensor_state[cmd]['unit']})"
            ctk.CTkLabel(card, text=title, font=("Arial", 12, "bold"), text_color="gray").pack(pady=(10,0))
            
            # Number Value
            val_lbl = ctk.CTkLabel(card, text="--", font=("Arial", 32, "bold"), text_color="#3498db")
            val_lbl.pack(pady=(0,5))
            self.sensor_state[cmd]['widget_value_label'] = val_lbl

            # Progress Bar (Visual Indicator)
            bar = ctk.CTkProgressBar(card, width=200, height=10, progress_color="#3498db")
            bar.set(0) # Start empty
            bar.pack(pady=(0,15))
            self.sensor_state[cmd]['widget_progress_bar'] = bar

    # --- LIVE GRAPH TAB ---
    def _setup_graph_tab(self):
        self.fig, self.ax1 = plt.subplots(figsize=(6, 4), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b') 
        
        self.ax1.set_facecolor('#2b2b2b')
        self.ax1.set_ylabel('RPM', color='#3498db', fontsize=12, fontweight='bold')
        self.ax1.tick_params(axis='y', labelcolor='#3498db', colors='white')
        self.ax1.tick_params(axis='x', colors='white')
        self.ax1.grid(True, color='#404040', linestyle='--', alpha=0.5)
        self.ax1.set_ylim(0, 7000)

        self.ax2 = self.ax1.twinx()
        self.ax2.set_ylabel('Speed (km/h)', color='#e74c3c', fontsize=12, fontweight='bold')
        self.ax2.tick_params(axis='y', labelcolor='#e74c3c', colors='white')
        self.ax2.spines['bottom'].set_color('white'); self.ax2.spines['top'].set_color('white') 
        self.ax2.spines['left'].set_color('white'); self.ax2.spines['right'].set_color('white')
        self.ax2.set_ylim(0, 160)

        self.line_rpm, = self.ax1.plot([], [], color='#3498db', linewidth=2, label="RPM")
        self.line_speed, = self.ax2.plot([], [], color='#e74c3c', linewidth=2, label="Speed")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.tab_graph)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def update_graph(self):
        x_data = list(range(len(self.history_rpm)))
        self.line_rpm.set_data(x_data, self.history_rpm)
        self.line_speed.set_data(x_data, self.history_speed)
        self.ax1.set_xlim(0, len(self.history_rpm))
        self.ax2.set_xlim(0, len(self.history_speed))
        self.canvas.draw_idle()

    # --- SETTINGS TAB ---
    def _setup_settings_tab(self):
        lbl = ctk.CTkLabel(self.tab_settings, text="Sensor Configuration & Warnings", font=("Arial", 18, "bold"))
        lbl.pack(pady=10)
        header_frame = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        header_frame.pack(fill="x", padx=20)
        ctk.CTkLabel(header_frame, text="Sensor Name", width=200, anchor="w").pack(side="left", padx=10)
        ctk.CTkLabel(header_frame, text="Bar Max/Limit", width=80).pack(side="right", padx=5)
        ctk.CTkLabel(header_frame, text="Log", width=50).pack(side="right", padx=10)
        ctk.CTkLabel(header_frame, text="Show", width=50).pack(side="right", padx=10)
        self.settings_scroll = ctk.CTkScrollableFrame(self.tab_settings)
        self.settings_scroll.pack(fill="both", expand=True, padx=20, pady=5)
        for cmd, data in self.sensor_state.items():
            row = ctk.CTkFrame(self.settings_scroll)
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=data["name"], width=200, anchor="w").pack(side="left", padx=10)
            ctk.CTkCheckBox(row, text="", variable=data["show_var"], command=self.rebuild_dashboard_grid, width=20).pack(side="right", padx=15)
            ctk.CTkCheckBox(row, text="", variable=data["log_var"], width=20).pack(side="right", padx=15)
            ctk.CTkEntry(row, textvariable=data["limit_var"], width=60).pack(side="right", padx=5)
        frame_log = ctk.CTkFrame(self.tab_settings)
        frame_log.pack(fill="x", padx=20, pady=20)
        self.lbl_path = ctk.CTkLabel(frame_log, text=f"Save Path: {self.logger.log_dir}")
        self.lbl_path.pack(side="left", padx=10)
        ctk.CTkButton(frame_log, text="Change Folder", command=self.change_log_folder).pack(side="right", padx=10)

    # --- DIAGNOSTICS TAB ---
    def _setup_diagnostics_tab(self):
        btn_frame = ctk.CTkFrame(self.tab_diag, fg_color="transparent")
        btn_frame.pack(pady=20)
        self.btn_analyze = ctk.CTkButton(btn_frame, text="RUN ANALYSIS", fg_color="purple", width=150, command=self.run_analysis)
        self.btn_analyze.pack(side="left", padx=10)
        self.btn_scan = ctk.CTkButton(btn_frame, text="SCAN CODES", fg_color="blue", width=150, command=self.scan_codes)
        self.btn_scan.pack(side="left", padx=10)
        self.btn_backup = ctk.CTkButton(btn_frame, text="FULL BACKUP", fg_color="orange", width=150, command=self.perform_full_backup)
        self.btn_backup.pack(side="left", padx=10)
        self.btn_clear = ctk.CTkButton(btn_frame, text="CLEAR CODES", fg_color="red", width=150, command=self.confirm_clear_codes)
        self.btn_clear.pack(side="left", padx=10)
        self.txt_dtc = ctk.CTkTextbox(self.tab_diag, width=700, height=350)
        self.txt_dtc.pack(pady=10)
        self.txt_dtc.insert("1.0", "Ready.\nUse 'Run Analysis' to check sensor data for logic problems.\nUse 'Scan Codes' to check ECU errors.")

    def _setup_debug_tab(self):
        self.txt_debug = ctk.CTkTextbox(self.tab_debug, width=700, height=400, font=("Consolas", 12))
        self.txt_debug.pack(pady=10, fill="both", expand=True)

    def on_close(self):
        data_to_save = {"log_dir": self.logger.log_dir, "sensors": {}}
        for cmd, state in self.sensor_state.items():
            data_to_save["sensors"][cmd] = {"show": state["show_var"].get(), "log": state["log_var"].get(), "limit": state["limit_var"].get()}
        ConfigManager.save_config(data_to_save)
        plt.close('all') 
        self.destroy()

    def update_loop(self):
        if self.obd.is_connected():
            data_snapshot = {}
            current_speed = 0

            # 1. Fetch Data
            for cmd, state in self.sensor_state.items():
                if state["show_var"].get() or state["log_var"].get() or cmd in ["SPEED", "RPM", "CONTROL_MODULE_VOLTAGE"]:
                    val = self.obd.query_sensor(cmd)
                    if val is not None:
                        data_snapshot[cmd] = val
                        if cmd == "SPEED": current_speed = val
                        
                        # Update Dashboard Labels & Bars
                        if state["show_var"].get():
                            
                            if state["widget_value_label"]:
                                state["widget_value_label"].configure(text=str(val))
                            
                            # Update Color & Bar Progress
                            try:
                                limit = float(state["limit_var"].get())
                                
                                # Color Logic
                                color = "#3498db" # Blue
                                if cmd == "CONTROL_MODULE_VOLTAGE" and (val < 11.5 or val > 15.5): color = "red"
                                elif limit > 0 and val > limit: color = "red"
                                
                                if state["widget_value_label"]: state["widget_value_label"].configure(text_color=color)
                                
                                # Bar Progress Logic (0.0 to 1.0)
                                if state["widget_progress_bar"] and limit > 0:
                                    progress = min(val / limit, 1.0) # Cap at 100%
                                    state["widget_progress_bar"].set(progress)
                                    state["widget_progress_bar"].configure(progress_color=color)

                            except ValueError: pass

            # 2. Update Graph Data
            rpm_val = data_snapshot.get("RPM", 0)
            speed_val = data_snapshot.get("SPEED", 0)
            self.history_rpm.append(rpm_val)
            self.history_speed.append(speed_val)
            
            if self.tabview.get() == "Live Graph":
                self.update_graph()

            # 3. Safety Check
            if current_speed > 0:
                self.btn_clear.configure(state="disabled", text="MOVING...")
            else:
                self.btn_clear.configure(state="normal", text="CLEAR CODES")

            self.logger.write_row(data_snapshot)
        self.after(500, self.update_loop)

    # --- ACTIONS ---
    def run_analysis(self):
        if not self.obd.is_connected():
            self.txt_dtc.delete("1.0", "end"); self.txt_dtc.insert("end", "Error: Connect to car first.")
            return
        self.txt_dtc.delete("1.0", "end"); self.txt_dtc.insert("end", "Gathering data for analysis...\n")
        self.update()
        snapshot = {}
        thresholds = {}
        for cmd, state in self.sensor_state.items():
            snapshot[cmd] = self.obd.query_sensor(cmd)
            thresholds[cmd] = state["limit_var"].get()
        issues = DiagnosticEngine.analyze(snapshot, thresholds)
        if not issues: self.txt_dtc.insert("end", "✅ System Analysis Passed.")
        else:
            self.txt_dtc.insert("end", f"⚠️ Found {len(issues)} Potential Issues:\n", "bold")
            for issue in issues: self.txt_dtc.insert("end", f"• {issue}\n")

    def toggle_connection(self):
        if self.obd.is_connected():
            self.obd.disconnect()
            self.btn_connect.configure(text="CONNECT", fg_color="green")
            for cmd in self.sensor_state:
                lbl = self.sensor_state[cmd]['widget_value_label']
                if lbl: lbl.configure(text="--")
                bar = self.sensor_state[cmd]['widget_progress_bar']
                if bar: bar.set(0)
        else:
            self.btn_connect.configure(text="CONNECTING...", state="disabled")
            self.update()
            if self.obd.connect():
                self.btn_connect.configure(text="DISCONNECT", fg_color="red")
                log_sensors = [k for k, v in self.sensor_state.items() if v["log_var"].get()]
                self.logger.start_new_log(log_sensors)
                self.append_debug_log(f"Started logging: {len(log_sensors)} sensors.")
            else:
                self.btn_connect.configure(text="RETRY CONNECT", fg_color="orange")
            self.btn_connect.configure(state="normal")

    def change_log_folder(self):
        new_dir = filedialog.askdirectory()
        if new_dir:
            if self.logger.set_directory(new_dir): self.lbl_path.configure(text=f"Save Path: {new_dir}")

    def append_debug_log(self, message):
        self.txt_debug.insert("end", message + "\n"); self.txt_debug.see("end")

    def scan_codes(self):
        if not self.obd.is_connected(): self.txt_dtc.delete("1.0", "end"); self.txt_dtc.insert("end", "Error: Not Connected."); return
        self.txt_dtc.delete("1.0", "end"); self.txt_dtc.insert("end", "Scanning...\n"); self.update()
        codes = self.obd.get_dtc()
        self.txt_dtc.delete("1.0", "end")
        if not codes: self.txt_dtc.insert("end", "No Fault Codes Found (Green Light!)")
        else:
            self.txt_dtc.insert("end", f"Found {len(codes)} Faults:\n", "bold")
            for c in codes: self.txt_dtc.insert("end", f"• {c[0]}: {c[1]}\n")

    def perform_full_backup(self):
        if not self.obd.is_connected(): messagebox.showerror("Error", "Connect to car first!"); return
        self.txt_dtc.delete("1.0", "end"); self.txt_dtc.insert("end", "Reading System Data...\n"); self.update()
        codes = self.obd.get_dtc()
        snapshot = self.obd.get_freeze_frame_snapshot(list(self.sensor_state.keys()))
        report = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "fault_codes": codes, "freeze_frame_data": snapshot}
        filename = f"Backup_{int(time.time())}.json"
        filepath = os.path.join(self.logger.log_dir, filename)
        try:
            with open(filepath, 'w') as f: json.dump(report, f, indent=4)
            self.txt_dtc.insert("end", f"SUCCESS: Backup saved to:\n{filepath}\n\n"); self.txt_dtc.insert("end", f"Snapshot: {json.dumps(snapshot, indent=2)}")
        except Exception as e: self.txt_dtc.insert("end", f"Error saving backup: {e}")

    def confirm_clear_codes(self):
        if not self.obd.is_connected(): messagebox.showerror("Error", "Connect to car first!"); return
        answer = messagebox.askyesno("WARNING", "Have you performed a FULL BACKUP yet?\n\nClearing codes will PERMANENTLY erase Freeze Frame data.\nProceed?")
        if answer:
            self.txt_dtc.delete("1.0", "end"); self.txt_dtc.insert("end", "Clearing codes...\n"); self.update()
            if self.obd.clear_dtc(): self.txt_dtc.insert("end", "\nSUCCESS: Codes cleared.\n"); messagebox.showinfo("Success", "Codes cleared.")
            else: self.txt_dtc.insert("end", "\nFAILED: Could not clear codes.")