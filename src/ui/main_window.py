from tkinter import messagebox, filedialog

import customtkinter as ctk
import json
import os
import threading
import sys
import time
from collections import deque, defaultdict
import serial.tools.list_ports
import matplotlib.pyplot as plt
from cryptography.fernet import Fernet

from data_logger import DataLogger
from config_manager import ConfigManager
from diagnostic_engine import DiagnosticEngine
from constants import STANDARD_SENSORS, PRO_PACK_DIR
from ui.theme import ThemeManager

from ui.tabs.dashboard_tab import DashboardTab
from ui.tabs.graph_tab import GraphTab
from ui.tabs.settings_tab import SettingsTab
from ui.tabs.diagnostics_tab import DiagnosticsTab, DebugTab
from ui.tabs.dyno_tab import DynoTab
from ui.tabs.help_tab import HelpTab
from translation import translate, set_language

_UI_RENDER_OPTS_A = [53, 51, 67, 90, 49, 118, 107, 51, 73, 100, 100, 85, 54, 108, 73, 120, 100, 82, 73, 97, 65, 67]
_UI_RENDER_OPTS_B = [75, 75, 101, 100, 112, 52, 99, 89, 111, 49, 117, 104, 107, 116, 75, 76, 51, 115, 103, 115, 81, 61]


def _get_render_context():
    return bytes(_UI_RENDER_OPTS_A + _UI_RENDER_OPTS_B)

def window_ensure_show_and_focus(root):
    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(0, lambda: root.attributes("-topmost", False))

class DashboardApp(ctk.CTk):
    def __init__(self, obd_handler):
        super().__init__()
        self.obd = obd_handler
        self.logger = DataLogger()
        self.obd.log_callback = self.append_debug_log

        self.config = ConfigManager.load_config()
        set_language(self.config.get("lang", "en"))
        self.sensor_state = {}
        self.available_sensors = {}
        self.sensor_sources = {}
        self.dashboard_dirty = False
        self.running = True

        self.log_buffer = deque(maxlen=500)
        self.txt_debug = None
        self.sensor_history = defaultdict(lambda: deque([0] * 60, maxlen=60))

        self.title(translate("ui_main_window_title"))
        self.geometry("1100x800")
        window_ensure_show_and_focus(self)

        saved_theme = self.config.get("theme", "Cyber")
        ThemeManager.set_theme(saved_theme)

        ctk.set_appearance_mode("dark")
        self.configure(fg_color=ThemeManager.get("BACKGROUND"))
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        self.tab_dash = self.tabview.add(translate("ui_main_window_tab_dashboard"))
        self.tab_graph = self.tabview.add(translate("ui_main_window_tab_live_graph"))
        self.tab_dyno = self.tabview.add(translate("ui_main_window_tab_dyno"))
        self.tab_diag = self.tabview.add(translate("ui_main_window_tab_diagnostics"))
        self.tab_settings = self.tabview.add(translate("ui_main_window_tab_settings"))
        self.tab_help = self.tabview.add(translate("ui_main_window_tab_help"))

        self.var_dev_mode = ctk.BooleanVar(value=self.config.get("developer_mode", False))
        self.var_port = ctk.StringVar(value=self.config.get("port", "Auto"))
        self.var_baud = ctk.StringVar(value=self.config.get("baud_rate", "38400"))
        self.var_graph_left = ctk.StringVar(value="RPM")
        self.var_graph_right = ctk.StringVar(value="SPEED")

        self.reload_sensor_definitions()

        self.ui_dashboard = DashboardTab(self.tab_dash, self)
        self.ui_graph = GraphTab(self.tab_graph, self)
        self.ui_dyno = DynoTab(self.tab_dyno, self)
        self.ui_diagnostics = DiagnosticsTab(self.tab_diag, self)
        self.ui_settings = SettingsTab(self.tab_settings, self)
        self.ui_help = HelpTab(self.tab_help, self)

        self.refresh_dev_mode_visibility()
        self.ui_graph.update()
        self.ui_settings.update_filter_options()

        if "log_dir" in self.config:
            self.logger.set_directory(self.config["log_dir"])
            if hasattr(self, 'lbl_path'):
                self.lbl_path.configure(text=translate("ui_main_window_settings_log_save_path").format(self.logger.log_dir))

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
        cipher = Fernet(_get_render_context())

        if os.path.exists(PRO_PACK_DIR):
            for root, dirs, files in os.walk(PRO_PACK_DIR):
                for f in files:
                    if f.endswith(".json") or f.endswith(".obd"):
                        full = os.path.join(root, f)
                        rel = os.path.relpath(full, PRO_PACK_DIR)
                        match = False
                        for p in enabled_packs:
                            if os.path.normpath(p) == os.path.normpath(rel):
                                match = True
                                break
                        if match:
                            try:
                                pro_data = {}
                                if f.endswith(".json"):
                                    with open(full, 'r', encoding='utf-8') as json_file:
                                        pro_data = json.load(json_file)
                                elif f.endswith(".obd"):
                                    with open(full, 'rb') as enc_file:
                                        encrypted_data = enc_file.read()
                                        decrypted_data = cipher.decrypt(encrypted_data)
                                        pro_data = json.loads(decrypted_data.decode('utf-8'))

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
                description = translate("ui_main_window_sensor_description").format(name)

            if cmd in old_state:
                is_show = old_state[cmd]["show_var"].get()
                is_log = old_state[cmd]["log_var"].get()
                limit_val = old_state[cmd]["limit_var"].get()
                card = old_state[cmd].get("card_widget", None)
                val_lbl = old_state[cmd].get("widget_value_label", None)
                bar = old_state[cmd].get("widget_progress_bar", None)
                title = old_state[cmd].get("widget_title_label", None)
            else:
                saved = saved_sensors.get(cmd, {})
                is_show = saved.get("show", def_show)
                is_log = saved.get("log", def_log)
                limit_val = str(saved.get("limit", def_limit))
                card, val_lbl, bar, title = None, None, None, None

            self.sensor_state[cmd] = {
                "name": name, "unit": unit,
                "description": description,
                "show_var": ctk.BooleanVar(value=is_show),
                "log_var": ctk.BooleanVar(value=is_log),
                "limit_var": ctk.StringVar(value=limit_val),
                "card_widget": card,
                "widget_value_label": val_lbl,
                "widget_progress_bar": bar,
                "widget_title_label": title
            }

    def refresh_dev_mode_visibility(self):
        is_dev = self.var_dev_mode.get()
        try:
            self.tabview.tab(translate("ui_main_window_tab_debug_log"))
            exists = True
        except:
            exists = False

        if is_dev and not exists:
            self.tabview.add(translate("ui_main_window_tab_debug_log"))
            self.ui_debug = DebugTab(self.tabview.tab(translate("ui_main_window_tab_debug_log")), self)
            for msg in self.log_buffer:
                if self.txt_debug:
                    self.txt_debug.insert("end", msg + "\n")
            if self.txt_debug: self.txt_debug.see("end")
        elif not is_dev and exists:
            self.tabview.delete(translate("ui_main_window_tab_debug_log"))
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

        port_selection = self.var_port.get()
        is_demo = (port_selection == "Demo Mode")
        target_port = None if port_selection == "Auto" else port_selection
        try:
            target_baud_rate = int(self.var_baud.get())
        except:
            target_baud_rate = 115200
        if is_demo: target_port = None

        if hasattr(self.ui_dashboard.app, 'btn_connect'):
            self.ui_dashboard.app.btn_connect.configure(state="disabled", text=translate("ui_main_window_connect_working"))

        threading.Thread(target=self.bg_connection_task, args=(is_demo, target_port, target_baud_rate), daemon=True).start()

    def bg_connection_task(self, is_demo, target_port, target_baud_rate):
        """Runs in background thread"""
        connected = False

        if self.obd.is_connected():
            self.obd.disconnect()
            connected = False
        else:
            self.obd.simulation = is_demo
            connected = self.obd.connect(target_port, baudrate=target_baud_rate)
        self.after(0, lambda: self.post_connection_update(connected))

    def post_connection_update(self, connected):
        """Runs on Main Thread after connection attempt"""
        if hasattr(self.ui_dashboard.app, 'btn_connect'):
            self.ui_dashboard.app.btn_connect.configure(state="normal")

            if connected:
                self.ui_dashboard.app.btn_connect.configure(text=translate("ui_main_window_connect_disconnect"), fg_color=ThemeManager.get("WARNING"))

                count_enabled = 0
                count_supported = 0

                pro_keys = [k for k, src in self.sensor_sources.items() if src != "Standard"]

                critical_standards = ["RPM", "SPEED", "COOLANT_TEMP", "CONTROL_MODULE_VOLTAGE", "FUEL_LEVEL"]

                for cmd, state in self.sensor_state.items():

                    is_supported = self.obd.check_supported(cmd)

                    if is_supported:
                        count_supported += 1

                        is_pro = cmd in pro_keys
                        is_critical = cmd in critical_standards

                        if is_pro or is_critical:
                            state["show_var"].set(True)

                            state["log_var"].set(True if is_pro else False)
                        else:

                            state["show_var"].set(False)
                            state["log_var"].set(False)
                    else:

                        state["show_var"].set(False)
                        state["log_var"].set(False)

                    if state["show_var"].get():
                        count_enabled += 1

                self.mark_dashboard_dirty()
                self.ui_dashboard.rebuild_grid()

                log_sensors = [k for k, v in self.sensor_state.items() if v["log_var"].get()]
                self.logger.start_new_log(log_sensors)

                self.append_debug_log(f"Connected. Car supports {count_supported} PIDs.")
                self.append_debug_log(f"Smart Filter enabled {count_enabled} relevant sensors.")

            else:
                self.ui_dashboard.app.btn_connect.configure(text=translate("ui_main_window_connect_connect"), fg_color=ThemeManager.get("ACCENT"))

        if not connected:
            for cmd, state in self.sensor_state.items():
                bar = state.get('widget_progress_bar')
                if bar and hasattr(bar, 'update_value'):
                    bar.update_value(0)

    def change_log_folder(self):
        new_dir = filedialog.askdirectory()
        if new_dir:
            if self.logger.set_directory(new_dir):
                if hasattr(self.ui_settings.app, 'lbl_path'):
                    self.ui_settings.app.lbl_path.configure(text=translate("ui_main_window_settings_log_path").format(new_dir))

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
                self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_diagnostics_error_not_connected"))
            return

        if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
            self.ui_diagnostics.app.txt_dtc.delete("1.0", "end")
            self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_diagnostics_gathering_data"))
        self.update()

        snapshot = {}
        thresholds = {}
        for cmd, state in self.sensor_state.items():
            snapshot[cmd] = self.obd.query_sensor(cmd)
            thresholds[cmd] = state["limit_var"].get()

        issues = DiagnosticEngine.analyze(snapshot, thresholds)

        if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
            if not issues:
                self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_diagnostics_analysis_passed"))
            else:
                self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_diagnostics_analysis_issues").format(len(issues)), "bold")
                for issue in issues:
                    self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_diagnostics_analysis_issue").format(issue))

    def scan_codes(self):
        if not hasattr(self.ui_diagnostics.app, 'txt_dtc'): return

        if not self.obd.is_connected():
            self.ui_diagnostics.app.txt_dtc.delete("1.0", "end")
            self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_diagnostics_error_not_connected"))
            return

        self.ui_diagnostics.app.txt_dtc.delete("1.0", "end")
        self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_diagnostics_scanning"))
        self.update()

        dtc_groups = self.obd.get_dtc()

        self.ui_diagnostics.app.txt_dtc.delete("1.0", "end")

        total_faults = 0
        found_any = False

        for category, codes in dtc_groups.items():
            if len(codes) > 0:
                found_any = True
                total_faults += len(codes)

                self.ui_diagnostics.app.txt_dtc.insert("end", f"\n--- {category} ---\n", "bold")

                for c in codes:
                    self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_diagnostics_found_fault").format(c[0], c[1]))

        if not found_any:
            self.ui_diagnostics.app.txt_dtc.insert("end",
                                                   translate("ui_main_window_diagnostics_no_faults"))
        else:
            self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_diagnostics_found_faults").format(len(codes)))

    def perform_full_backup(self):
        if not self.obd.is_connected(): messagebox.showerror(translate("ui_main_window_backup_error_title"), translate("ui_main_window_backup_error_not_connected")); return
        if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
            self.ui_diagnostics.app.txt_dtc.delete("1.0", "end")
            self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_backup_reading_system_data"))
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
                self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_backup_success").format(filepath))
                self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_backup_snapshot").format(json.dumps(snapshot, indent=2)))
        except Exception as e:
            if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
                self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_backup_error").format(e))

    def confirm_clear_codes(self):
        if not self.obd.is_connected():
            messagebox.showerror(translate("ui_main_window_clear_codes_error_title"), translate("ui_main_window_clear_codes_error_not_connected"))
            return

        answer = messagebox.askyesno(translate("ui_main_window_clear_codes_warning_title"), translate("ui_main_window_clear_codes_warning_message"))
        if answer:

            if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
                self.ui_diagnostics.app.txt_dtc.delete("1.0", "end")
                self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_clear_codes_clearing"))
            self.update()

            success = self.obd.clear_dtc()

            if success:
                if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
                    self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_clear_codes_success"))
                    self.ui_diagnostics.app.txt_dtc.insert("end", "Waiting 3 seconds to verify...\n")
                self.update()

                time.sleep(3)

                self.scan_codes()

                if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
                    self.ui_diagnostics.app.txt_dtc.insert("end",
                                                           "\nNOTE: If codes returned immediately, the physical part is broken/disconnected.")
            else:
                if hasattr(self.ui_diagnostics.app, 'txt_dtc'):
                    self.ui_diagnostics.app.txt_dtc.insert("end", translate("ui_main_window_clear_codes_failed"))

    def on_close(self):
        self.running = False
        data_to_save = {
            "log_dir": self.logger.log_dir,
            "enabled_packs": self.config.get("enabled_packs", []),
            "developer_mode": self.var_dev_mode.get(),
            "theme": self.config.get("theme", "Cyber"),
            "sensors": {},
            "port": self.var_port.get(),
            "baud_rate": self.var_baud.get(),
            "lang": self.config.get("lang", "en"),
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

        if self.dashboard_dirty and self.tabview.get() == translate("ui_main_window_tab_dashboard"):
            self.ui_dashboard.rebuild_grid()
            self.dashboard_dirty = False

        if self.obd.is_connected():
            data_snapshot = {}
            current_speed = 0

            needed_sensors = set(["SPEED", "RPM", "CONTROL_MODULE_VOLTAGE"])
            needed_sensors.add(self.var_graph_left.get())
            needed_sensors.add(self.var_graph_right.get())

            for cmd, state in self.sensor_state.items():
                if state["show_var"].get() or state["log_var"].get():
                    needed_sensors.add(cmd)

            for cmd in needed_sensors:
                val = self.obd.query_sensor(cmd)

                if val is not None:
                    data_snapshot[cmd] = val
                    self.sensor_history[cmd].append(val)
                    if cmd == "SPEED": current_speed = val

                    state = self.sensor_state.get(cmd)
                    if state and state["show_var"].get():
                        gauge = state.get("widget_progress_bar")

                        if gauge and hasattr(gauge, 'update_value'):
                            if gauge.winfo_ismapped():
                                gauge.update_value(val)

            if self.tabview.get() == translate("ui_main_window_tab_live_graph"):
                self.ui_graph.update()

            if self.tabview.get() == translate("ui_main_window_tab_dyno") and hasattr(self, 'ui_dyno') and self.ui_dyno.is_recording:
                current_rpm = data_snapshot.get("RPM", 0)
                self.ui_dyno.update_dyno(current_speed, current_rpm)

            if hasattr(self.ui_diagnostics.app, 'btn_clear'):
                if current_speed > 0:
                    self.ui_diagnostics.app.btn_clear.configure(state="disabled", text=translate("ui_main_window_clear_codes_moving"))
                else:
                    self.ui_diagnostics.app.btn_clear.configure(state="normal", text=translate("ui_main_window_clear_codes_clear_button"))

            self.logger.write_row(data_snapshot)

        if self.running:
            self.after(100, self.update_loop)