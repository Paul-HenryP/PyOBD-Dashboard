import customtkinter as ctk
import json
import os
import threading
import sys
from collections import deque, defaultdict
import serial.tools.list_ports
import matplotlib.pyplot as plt

from data_logger import DataLogger
from config_manager import ConfigManager
from diagnostic_engine import DiagnosticEngine
from constants import STANDARD_SENSORS, PRO_PACK_DIR
from ui.theme import ThemeManager

from ui.tabs.dashboard_tab import DashboardTab
from ui.tabs.graph_tab import GraphTab
from ui.tabs.settings_tab import SettingsTab
from ui.tabs.diagnostics_tab import DiagnosticsTab, DebugTab


class DashboardApp(ctk.CTk):
    def __init__(self, obd_handler):
        super().__init__()
        self.obd = obd_handler
        self.logger = DataLogger()
        self.obd.log_callback = self.append_debug_log

        self.config = ConfigManager.load_config()
        self.sensor_state = {}
        self.available_sensors = {}
        self.sensor_sources = {}
        self.dashboard_dirty = False
        self.running = True

        self.log_buffer = deque(maxlen=500)
        self.txt_debug = None
        self.sensor_history = defaultdict(lambda: deque([0] * 60, maxlen=60))

        self.title("PyOBD Professional - Ultimate Edition")
        self.geometry("1100x800")

        # --- LOAD SAVED THEME ---
        saved_theme = self.config.get("theme", "Cyber")
        ThemeManager.set_theme(saved_theme)

        ctk.set_appearance_mode("dark")
        self.configure(fg_color=ThemeManager.get("BACKGROUND"))
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        # Tabs
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        self.tab_dash = self.tabview.add("Dashboard")
        self.tab_graph = self.tabview.add("Live Graph")
        self.tab_diag = self.tabview.add("Diagnostics")
        self.tab_settings = self.tabview.add("Settings")

        self.var_dev_mode = ctk.BooleanVar(value=self.config.get("developer_mode", False))
        self.var_port = ctk.StringVar(value="Auto")
        self.var_graph_left = ctk.StringVar(value="RPM")
        self.var_graph_right = ctk.StringVar(value="SPEED")

        self.reload_sensor_definitions()

        self.ui_dashboard = DashboardTab(self.tab_dash, self)
        self.ui_graph = GraphTab(self.tab_graph, self)
        self.ui_diagnostics = DiagnosticsTab(self.tab_diag, self)
        self.ui_settings = SettingsTab(self.tab_settings, self)

        self.refresh_dev_mode_visibility()
        self.ui_graph.update()
        self.ui_settings.update_filter_options()

        if "log_dir" in self.config:
            self.logger.set_directory(self.config["log_dir"])
            if hasattr(self, 'lbl_path'):
                self.lbl_path.configure(text=f"Save Path: {self.logger.log_dir}")

        self.ui_dashboard.rebuild_grid()
        self.update_loop()

    def change_theme(self, new_theme):
        ThemeManager.set_theme(new_theme)
        self.configure(fg_color=ThemeManager.get("BACKGROUND"))

        if hasattr(self, 'ui_dashboard'):
            self.ui_dashboard.dash_scroll.configure(fg_color=ThemeManager.get("BACKGROUND"))
            self.ui_dashboard.frame_controls.configure(fg_color=ThemeManager.get("BACKGROUND"))

            self.ui_dashboard.app.btn_connect.configure(
                fg_color=ThemeManager.get("ACCENT"),
                text_color=ThemeManager.get("BACKGROUND"),
                hover_color=ThemeManager.get("ACCENT_DIM")
            )

            self.ui_dashboard.combo_ports.configure(
                fg_color=ThemeManager.get("CARD_BG"),
                text_color=ThemeManager.get("ACCENT"),
                button_color=ThemeManager.get("ACCENT_DIM")
            )

            if hasattr(self.ui_dashboard, 'btn_prev'):
                self.ui_dashboard.btn_prev.configure(fg_color=ThemeManager.get("CARD_BG"))
                self.ui_dashboard.btn_next.configure(fg_color=ThemeManager.get("CARD_BG"))
                self.ui_dashboard.lbl_page.configure(text_color=ThemeManager.get("TEXT_MAIN"))

        for cmd, state in self.sensor_state.items():
            if state["card_widget"]:
                state["card_widget"].configure(fg_color=ThemeManager.get("CARD_BG"))

            gauge = state.get("widget_progress_bar")
            if gauge and hasattr(gauge, 'redraw_colors'):
                gauge.redraw_colors()

            title_lbl = state.get("widget_title_label")
            if title_lbl:
                title_lbl.configure(text_color=ThemeManager.get("TEXT_MAIN"))

        self.config["theme"] = new_theme
        ConfigManager.save_config(self.config)

    def reload_sensor_definitions(self):
        self.available_sensors = STANDARD_SENSORS.copy()
        self.sensor_sources = {k: "Standard" for k in STANDARD_SENSORS}

        enabled_packs = self.config.get("enabled_packs", [])

        if os.path.exists(PRO_PACK_DIR):
            for root, dirs, files in os.walk(PRO_PACK_DIR):
                for f in files:
                    if f.endswith(".json"):
                        full = os.path.join(root, f)
                        rel = os.path.relpath(full, PRO_PACK_DIR)
                        match = False
                        for p in enabled_packs:
                            if os.path.normpath(p) == os.path.normpath(rel):
                                match = True
                                break
                        if match:
                            try:
                                with open(full, 'r') as json_file:
                                    pro_data = json.load(json_file)
                                    for key, val in pro_data.items():
                                        self.available_sensors[key] = tuple(val[:5])
                                        self.sensor_sources[key] = rel
                                    print(f"Loaded Pack: {rel}")
                            except Exception as e:
                                print(f"Error loading {rel}: {e}")

        self.obd.set_pro_definitions(self.available_sensors)
        self._init_sensor_state()

    def _init_sensor_state(self):
        old_state = self.sensor_state if hasattr(self, 'sensor_state') else {}
        self.sensor_state = {}
        saved_sensors = self.config.get("sensors", {})

        for cmd, tuple_data in self.available_sensors.items():
            name = tuple_data[0]
            unit = tuple_data[1]
            def_show = tuple_data[2]
            def_log = tuple_data[3]
            def_limit = tuple_data[4]

            if len(tuple_data) > 5:
                description = tuple_data[5]
            else:
                description = f"{name}: Manufacturer specific sensor."

            if cmd in old_state:
                is_show = old_state[cmd]["show_var"].get()
                is_log = old_state[cmd]["log_var"].get()
                limit_val = old_state[cmd]["limit_var"].get()
                card = old_state[cmd].get("card_widget", None)
                val_lbl = old_state[cmd].get("widget_value_label", None)
                bar = old_state[cmd].get("widget_progress_bar", None)
            else:
                saved = saved_sensors.get(cmd, {})
                is_show = saved.get("show", def_show)
                is_log = saved.get("log", def_log)
                limit_val = str(saved.get("limit", def_limit))
                card, val_lbl, bar = None, None, None

            self.sensor_state[cmd] = {
                "name": name, "unit": unit,
                "description": description,
                "show_var": ctk.BooleanVar(value=is_show),
                "log_var": ctk.BooleanVar(value=is_log),
                "limit_var": ctk.StringVar(value=limit_val),
                "card_widget": card,
                "widget_value_label": val_lbl,
                "widget_progress_bar": bar,
                "widget_title_label": None
            }

    def refresh_dev_mode_visibility(self):
        is_dev = self.var_dev_mode.get()
        try:
            self.tabview.tab("Debug Log")
            exists = True
        except:
            exists = False

        if is_dev and not exists:
            self.tabview.add("Debug Log")
            self.ui_debug = DebugTab(self.tabview.tab("Debug Log"), self)
            for msg in self.log_buffer:
                if self.txt_debug:
                    self.txt_debug.insert("end", msg + "\n")
            if self.txt_debug: self.txt_debug.see("end")
        elif not is_dev and exists:
            self.tabview.delete("Debug Log")
            self.txt_debug = None

    def get_serial_ports(self):
        ports = ["Auto", "Demo Mode"]
        try:
            for port in serial.tools.list_ports.comports():
                ports.append(port.device)
        except Exception:
            pass
        return ports

    def refresh_ports(self):
        new_ports = self.get_serial_ports()
        if hasattr(self, 'ui_dashboard'):
            self.ui_dashboard.combo_ports.configure(values=new_ports)
        if self.var_port.get() not in new_ports:
            self.var_port.set("Auto")

    def mark_dashboard_dirty(self):
        self.dashboard_dirty = True

    def update_graph_dropdowns(self):
        if hasattr(self, 'ui_graph'):
            options = sorted(list(self.available_sensors.keys()))
            self.ui_graph.app.menu_left.configure(values=options)
            self.ui_graph.app.menu_right.configure(values=options)

    def on_connect_click(self):
        if hasattr(self.ui_dashboard.app, 'btn_connect'):
            self.ui_dashboard.app.btn_connect.configure(state="disabled", text="Connecting...")
        threading.Thread(target=self.toggle_connection, daemon=True).start()

    def toggle_connection(self):
        if self.obd.is_connected():
            self.obd.disconnect()
            if hasattr(self.ui_dashboard.app, 'btn_connect'):
                self.ui_dashboard.app.btn_connect.configure(text="CONNECT", fg_color=ThemeManager.get("ACCENT"),
                                                            state="normal")

            for cmd in self.sensor_state:
                bar = self.sensor_state[cmd]['widget_progress_bar']
                if bar and hasattr(bar, 'update_value'):
                    bar.update_value(0)
        else:
            selected_port = self.var_port.get()
            if selected_port == "Demo Mode":
                self.obd.simulation = True
                target_port = None
            else:
                self.obd.simulation = False
                target_port = None if selected_port == "Auto" else selected_port

            success = self.obd.connect(target_port)

            if hasattr(self.ui_dashboard.app, 'btn_connect'):
                if success:
                    self.ui_dashboard.app.btn_connect.configure(text="DISCONNECT", fg_color="red", state="normal")
                    log_sensors = [k for k, v in self.sensor_state.items() if v["log_var"].get()]
                    self.logger.start_new_log(log_sensors)
                    self.append_debug_log(f"Started logging: {len(log_sensors)} sensors.")
                else:
                    self.ui_dashboard.app.btn_connect.configure(text="RETRY CONNECT", fg_color="orange", state="normal")

    def change_log_folder(self):
        new_dir = filedialog.askdirectory()
        if new_dir:
            if self.logger.set_directory(new_dir):
                if hasattr(self.ui_settings.app, 'lbl_path'):
                    self.ui_settings.app.lbl_path.configure(text=f"Save Path: {new_dir}")

    def append_debug_log(self, message):
        self.log_buffer.append(message)
        if self.txt_debug and self.var_dev_mode.get():
            try:
                self.txt_debug.insert("end", message + "\n")
                self.txt_debug.see("end")
            except:
                pass

    def run_analysis(self):
        if not self.obd.is_connected():
            if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
                self.ui_diagnostics.app.txt_dtc.delete("1.0", "end")
                self.ui_diagnostics.app.txt_dtc.insert("end", "Error: Connect to car first.")
            return

        if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
            self.ui_diagnostics.app.txt_dtc.delete("1.0", "end")
            self.ui_diagnostics.app.txt_dtc.insert("end", "Gathering data for analysis...\n")
        self.update()

        snapshot = {}
        thresholds = {}
        for cmd, state in self.sensor_state.items():
            snapshot[cmd] = self.obd.query_sensor(cmd)
            thresholds[cmd] = state["limit_var"].get()

        issues = DiagnosticEngine.analyze(snapshot, thresholds)

        if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
            if not issues:
                self.ui_diagnostics.app.txt_dtc.insert("end", "✅ System Analysis Passed.")
            else:
                self.ui_diagnostics.app.txt_dtc.insert("end", f"⚠️ Found {len(issues)} Potential Issues:\n", "bold")
                for issue in issues:
                    self.ui_diagnostics.app.txt_dtc.insert("end", f"• {issue}\n")

    def scan_codes(self):
        if not hasattr(self.ui_diagnostics.app, 'txt_dtc'): return

        if not self.obd.is_connected():
            self.ui_diagnostics.app.txt_dtc.delete("1.0", "end")
            self.ui_diagnostics.app.txt_dtc.insert("end", "Error: Not Connected.")
            return

        self.ui_diagnostics.app.txt_dtc.delete("1.0", "end")
        self.ui_diagnostics.app.txt_dtc.insert("end", "Scanning...\n")
        self.update()

        codes = self.obd.get_dtc()
        self.ui_diagnostics.app.txt_dtc.delete("1.0", "end")
        if not codes:
            self.ui_diagnostics.app.txt_dtc.insert("end", "No Fault Codes Found (Green Light!)")
        else:
            self.ui_diagnostics.app.txt_dtc.insert("end", f"Found {len(codes)} Faults:\n", "bold")
            for c in codes:
                self.ui_diagnostics.app.txt_dtc.insert("end", f"• {c[0]}: {c[1]}\n")

    def perform_full_backup(self):
        if not self.obd.is_connected(): messagebox.showerror("Error", "Connect to car first!"); return
        if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
            self.ui_diagnostics.app.txt_dtc.delete("1.0", "end")
            self.ui_diagnostics.app.txt_dtc.insert("end", "Reading System Data...\n")
        self.update()

        codes = self.obd.get_dtc()
        snapshot = self.obd.get_freeze_frame_snapshot(list(self.sensor_state.keys()))
        report = {"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "fault_codes": codes, "freeze_frame_data": snapshot}
        filename = f"Backup_{int(time.time())}.json"
        filepath = os.path.join(self.logger.log_dir, filename)

        try:
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=4)
            if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
                self.ui_diagnostics.app.txt_dtc.insert("end", f"SUCCESS: Backup saved to:\n{filepath}\n\n")
                self.ui_diagnostics.app.txt_dtc.insert("end", f"Snapshot: {json.dumps(snapshot, indent=2)}")
        except Exception as e:
            if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
                self.ui_diagnostics.app.txt_dtc.insert("end", f"Error saving backup: {e}")

    def confirm_clear_codes(self):
        if not self.obd.is_connected(): messagebox.showerror("Error", "Connect to car first!"); return
        answer = messagebox.askyesno("WARNING",
                                     "Have you performed a FULL BACKUP yet?\n\nClearing codes will PERMANENTLY erase Freeze Frame data.\nProceed?")
        if answer:
            if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
                self.ui_diagnostics.app.txt_dtc.delete("1.0", "end")
                self.ui_diagnostics.app.txt_dtc.insert("end", "Clearing codes...\n")
            self.update()

            if self.obd.clear_dtc():
                if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
                    self.ui_diagnostics.app.txt_dtc.insert("end", "\nSUCCESS: Codes cleared.\n")
                messagebox.showinfo("Success", "Codes cleared.")
            else:
                if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
                    self.ui_diagnostics.app.txt_dtc.insert("end", "\nFAILED: Could not clear codes.")

    def on_close(self):
        self.running = False
        data_to_save = {
            "log_dir": self.logger.log_dir,
            "enabled_packs": self.config.get("enabled_packs", []),
            "developer_mode": self.var_dev_mode.get(),
            "theme": self.config.get("theme", "Cyber"),
            "sensors": {}
        }
        for cmd, state in self.sensor_state.items():
            data_to_save["sensors"][cmd] = {"show": state["show_var"].get(), "log": state["log_var"].get(),
                                            "limit": state["limit_var"].get()}
        ConfigManager.save_config(data_to_save)

        try:
            plt.close('all')
        except:
            pass
        self.destroy()
        os._exit(0)

    def update_loop(self):
        if not self.running: return

        # 0. Lazy Rebuild (UI Optimization)
        if self.dashboard_dirty and self.tabview.get() == "Dashboard":
            self.ui_dashboard.rebuild_grid()

        if self.obd.is_connected():
            data_snapshot = {}
            current_speed = 0

            # --- OPTIMIZATION: INTERLACED POLLING ---
            # 1. Identify all active sensors
            active_sensors = []

            # Graph sensors are ALWAYS High Priority
            graph_left = self.var_graph_left.get()
            graph_right = self.var_graph_right.get()

            # Gather all sensors the user wants to see/log
            for cmd, state in self.sensor_state.items():
                if state["show_var"].get() or state["log_var"].get():
                    active_sensors.append(cmd)

            # 2. Split into FAST and SLOW queues
            # Import priorities here to avoid circular imports at top level if needed,
            # or ensure constants.py is imported at top of file.
            from constants import HIGH_PRIORITY_SENSORS

            fast_queue = set()
            slow_queue = []

            for cmd in active_sensors:
                if cmd in HIGH_PRIORITY_SENSORS or cmd == graph_left or cmd == graph_right:
                    fast_queue.add(cmd)
                else:
                    slow_queue.append(cmd)

            # 3. Construct the "To Query" list for THIS specific frame
            # Always query ALL Fast sensors
            sensors_to_query = list(fast_queue)

            # Add ONE Slow sensor (Round-Robin)
            # We use a persistent counter to cycle through them
            if not hasattr(self, '_slow_sensor_index'):
                self._slow_sensor_index = 0

            if slow_queue:
                # Wrap around if index is out of bounds
                if self._slow_sensor_index >= len(slow_queue):
                    self._slow_sensor_index = 0

                # Add the one lucky slow sensor
                sensors_to_query.append(slow_queue[self._slow_sensor_index])

                # Increment for next frame
                self._slow_sensor_index += 1

            # --- EXECUTE QUERIES ---
            for cmd in sensors_to_query:
                val = self.obd.query_sensor(cmd)

                if val is not None:
                    # Update History & Snapshot
                    data_snapshot[cmd] = val
                    self.sensor_history[cmd].append(val)
                    if cmd == "SPEED": current_speed = val

                    # Update UI (Only if visible)
                    state = self.sensor_state.get(cmd)
                    if state and state["show_var"].get():
                        gauge = state.get("widget_progress_bar")
                        if gauge and hasattr(gauge, 'update_value'):
                            if gauge.winfo_ismapped():
                                gauge.update_value(val)

            # --- UPDATE GRAPH ---
            if self.tabview.get() == "Live Graph":
                self.ui_graph.update()

            # --- SAFETY CHECKS ---
            if hasattr(self.ui_diagnostics.app, 'btn_clear'):
                if current_speed > 0:
                    self.ui_diagnostics.app.btn_clear.configure(state="disabled", text="MOVING...")
                else:
                    self.ui_diagnostics.app.btn_clear.configure(state="normal", text="CLEAR CODES")

            # --- LOGGING ---
            # Note: The logger will write empty strings for sensors not queried in this frame.
            # This is acceptable for CSVs, or we can cache values.
            # For simplicity in this optimization, we log what we get.
            self.logger.write_row(data_snapshot)

        if self.running:
            # Run as fast as possible (10ms) because we are now doing less work per frame
            self.after(10, self.update_loop)