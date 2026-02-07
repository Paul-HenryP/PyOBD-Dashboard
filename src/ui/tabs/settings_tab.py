import customtkinter as ctk
import os
import json
from config_manager import ConfigManager
from constants import PRO_PACK_DIR
from ui.theme import ThemeManager
from elm import Elm
import threading
import socket

def _port_busy(host: str, port: int, timeout_s: float = 0.15) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(timeout_s)
        return s.connect_ex((host, port)) == 0
    finally:
        try:
            s.close()
        except Exception:
            pass


def _next_free_port(host: str, start_port: int, max_tries: int = 200) -> int:
    for p in range(start_port, start_port + max_tries):
        if not _port_busy(host, p):
            t = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                t.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                t.bind((host, p))
                return p
            except OSError:
                pass
            finally:
                try:
                    t.close()
                except Exception:
                    pass
    raise RuntimeError("no free port found")

class SettingsTab:
    def __init__(self, parent_frame, app_instance):
        self.frame = parent_frame
        self.app = app_instance

        frame_top = ctk.CTkFrame(self.frame, fg_color="transparent")
        frame_top.pack(fill="x", padx=20, pady=10)
        self.sim = None
        self.sim_location = None

        self.filter_var = ctk.StringVar(value="Standard")
        ctk.CTkLabel(frame_top, text="Show Pack:", font=("Arial", 12)).pack(side="left", padx=5)
        self.app.combo_filter = ctk.CTkOptionMenu(
            frame_top,
            variable=self.filter_var,
            values=["Standard"],
            command=self.refresh_settings_list,
        )
        self.app.combo_filter.pack(side="left", padx=5)

        ctk.CTkButton(
            frame_top,
            text="Manage Pro Packs",
            fg_color="purple",
            width=150,
            command=self.open_pack_manager,
        ).pack(side="right")

        ctk.CTkLabel(frame_top, text="Theme:", font=("Arial", 12)).pack(side="right", padx=5)
        self.var_theme = ctk.StringVar(value=self.app.config.get("theme", "Cyber"))

        theme_names = sorted(list(ThemeManager.THEMES.keys()))

        self.combo_theme = ctk.CTkOptionMenu(
            frame_top,
            variable=self.var_theme,
            values=theme_names,
            command=self.app.change_theme,
            width=130,
        )
        self.combo_theme.pack(side="right", padx=5)

        header_frame = ctk.CTkFrame(self.frame, fg_color="#404040")
        header_frame.pack(fill="x", padx=20)

        frame_all_show = ctk.CTkFrame(header_frame, fg_color="transparent")
        frame_all_show.pack(side="right", padx=5)
        ctk.CTkButton(
            frame_all_show,
            text="All",
            width=30,
            height=15,
            font=("Arial", 8),
            command=lambda: self.toggle_all("show", True),
        ).pack()
        ctk.CTkButton(
            frame_all_show,
            text="None",
            width=30,
            height=15,
            font=("Arial", 8),
            fg_color="gray",
            command=lambda: self.toggle_all("show", False),
        ).pack()
        ctk.CTkLabel(header_frame, text="Show", width=30).pack(side="right")

        frame_all_log = ctk.CTkFrame(header_frame, fg_color="transparent")
        frame_all_log.pack(side="right", padx=5)
        ctk.CTkButton(
            frame_all_log,
            text="All",
            width=30,
            height=15,
            font=("Arial", 8),
            command=lambda: self.toggle_all("log", True),
        ).pack()
        ctk.CTkButton(
            frame_all_log,
            text="None",
            width=30,
            height=15,
            font=("Arial", 8),
            fg_color="gray",
            command=lambda: self.toggle_all("log", False),
        ).pack()
        ctk.CTkLabel(header_frame, text="Log", width=30).pack(side="right")

        ctk.CTkLabel(header_frame, text="Limit", width=80).pack(side="right", padx=5)
        ctk.CTkLabel(header_frame, text="Sensor Name", width=200, anchor="w").pack(side="left", padx=10)

        self.settings_scroll = ctk.CTkScrollableFrame(self.frame)
        self.settings_scroll.pack(fill="both", expand=True, padx=20, pady=5)

        self.settings_scroll.grid_columnconfigure(0, weight=1)
        self.settings_scroll.grid_columnconfigure(1, minsize=80)
        self.settings_scroll.grid_columnconfigure(2, minsize=60)
        self.settings_scroll.grid_columnconfigure(3, minsize=60)

        self.refresh_settings_list()

        self._build_sim_section()

        frame_log = ctk.CTkFrame(self.frame)
        frame_log.pack(fill="x", padx=20, pady=20)
        self.app.lbl_path = ctk.CTkLabel(frame_log, text=f"Save Path: {self.app.logger.log_dir}")
        self.app.lbl_path.pack(side="left", padx=10)
        ctk.CTkButton(frame_log, text="Change Folder", command=self.app.change_log_folder).pack(side="right", padx=10)

        ctk.CTkSwitch(
            frame_log,
            text="Developer Mode",
            variable=self.app.var_dev_mode,
            command=self.app.refresh_dev_mode_visibility,
        ).pack(side="right", padx=20)

    def _build_sim_section(self):
        sim = ctk.CTkFrame(self.frame)
        sim.pack(fill="x", padx=20, pady=(10, 0))

        ctk.CTkLabel(sim, text="Simulation", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 6)
        )

        self.var_sim_mode = ctk.StringVar(value=self.app.config.get("sim_mode", "serial"))

        ctk.CTkLabel(sim, text="Mode:", anchor="w").grid(row=1, column=0, sticky="w", padx=10, pady=6)
        self.combo_sim_mode = ctk.CTkOptionMenu(
            sim,
            variable=self.var_sim_mode,
            values=["serial", "network"],
            width=140,
        )
        self.combo_sim_mode.grid(row=1, column=1, sticky="w", padx=10, pady=6)

        self.btn_sim_toggle = ctk.CTkButton(sim, text="Start", fg_color="green", width=120, command=self._toggle_sim)
        self.btn_sim_toggle.grid(row=1, column=3, rowspan=2, sticky="e", padx=10, pady=6)

        sim.grid_columnconfigure(2, weight=1)

        self._sync_sim_button()

    def _sync_sim_button(self):
        if self.sim:
            self.btn_sim_toggle.configure(text="Stop", fg_color="red")
            self.combo_sim_mode.configure(state="disabled")
        else:
            self.btn_sim_toggle.configure(text="Start", fg_color="green")
            self.combo_sim_mode.configure(state="normal")

    def _toggle_sim(self):
        if self.sim:
            self._stop_sim()
        else:
            self._start_sim()

    def _start_sim(self):
        mode = (self.var_sim_mode.get() or "").strip().lower()

        if mode not in ("serial", "network"):
            return

        result = False
        try:
            if mode == "serial":
                self.sim = Elm()
                self.sim_location = self.sim.get_pty()
                result = self.sim.connect_serial()
            elif mode == "network":
                host = "127.0.0.1"
                net_port = _next_free_port(host, 35000)
                self.sim = Elm(net_port=net_port)
                self.sim_location = f"{host}:{net_port}"
                result = True
            threading.Thread(target=self.sim.run, daemon=True).start()
        except Exception:
            return

        self._sync_sim_button()
        if result:
            self.app.var_port.set(self.sim_location)
        return result

    def _stop_sim(self):
        self.sim.terminate()
        self.sim = None
        self._sync_sim_button()

    def refresh_settings_list(self, choice=None):
        for widget in self.settings_scroll.winfo_children():
            widget.destroy()

        target_pack = self.filter_var.get()
        row_idx = 0

        items_to_show = []
        for cmd, data in self.app.sensor_state.items():
            src = self.app.sensor_sources.get(cmd, "Standard")
            if target_pack == "All (Slow)" or src == target_pack:
                items_to_show.append((cmd, data))

        for cmd, data in items_to_show:
            ctk.CTkLabel(self.settings_scroll, text=data["name"], anchor="w").grid(
                row=row_idx, column=0, sticky="w", padx=10, pady=2
            )
            ctk.CTkEntry(self.settings_scroll, textvariable=data["limit_var"], width=60).grid(
                row=row_idx, column=1, padx=5, pady=2
            )
            ctk.CTkCheckBox(self.settings_scroll, text="", variable=data["log_var"], width=20).grid(
                row=row_idx, column=2, padx=15, pady=2
            )
            ctk.CTkCheckBox(
                self.settings_scroll,
                text="",
                variable=data["show_var"],
                command=self.app.mark_dashboard_dirty,
                width=20,
            ).grid(row=row_idx, column=3, padx=15, pady=2)
            row_idx += 1

    def toggle_all(self, type_str, state):
        target_pack = self.filter_var.get()
        for cmd, data in self.app.sensor_state.items():
            src = self.app.sensor_sources.get(cmd, "Standard")
            if target_pack == "All (Slow)" or src == target_pack:
                if type_str == "show":
                    data["show_var"].set(state)
                elif type_str == "log":
                    data["log_var"].set(state)

        if type_str == "show":
            self.app.mark_dashboard_dirty()

    def open_pack_manager(self):
        window = ctk.CTkToplevel(self.app)
        window.title("Manage Pro Packs")
        window.geometry("400x400")
        window.attributes("-topmost", True)

        ctk.CTkLabel(window, text=f"Scan Path:\n{PRO_PACK_DIR}", font=("Arial", 10), text_color="gray").pack(pady=5)

        scroll = ctk.CTkScrollableFrame(window)
        scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        footer = ctk.CTkFrame(window, height=50)
        footer.pack(fill="x", side="bottom")

        enabled_packs = self.app.config.get("enabled_packs", [])

        available_files = []
        if os.path.exists(PRO_PACK_DIR):
            for root, dirs, files in os.walk(PRO_PACK_DIR):
                for f in files:
                    if f.endswith(".json") or f.endswith(".obd"):
                        full = os.path.join(root, f)
                        rel = os.path.relpath(full, PRO_PACK_DIR)
                        available_files.append(rel)

        if not available_files:
            ctk.CTkLabel(scroll, text="No .json files found.").pack()

        pack_vars = {}

        def on_save():
            new_enabled = [f for f, var in pack_vars.items() if var.get()]
            self.app.config["enabled_packs"] = new_enabled
            ConfigManager.save_config(self.app.config)
            window.destroy()

            self.app.configure(cursor="watch")
            self.app.update()
            self.app.reload_sensor_definitions()
            self.update_filter_options()
            self.refresh_settings_list()
            self.app.mark_dashboard_dirty()
            self.app.configure(cursor="")

        for f in available_files:
            row = ctk.CTkFrame(scroll)
            row.pack(fill="x", pady=2)

            is_checked = False
            norm_f = os.path.normpath(f)
            for enabled in enabled_packs:
                if os.path.normpath(enabled) == norm_f:
                    is_checked = True
                    break

            var = ctk.BooleanVar(value=is_checked)
            pack_vars[f] = var
            ctk.CTkCheckBox(row, text=f, variable=var).pack(side="left", padx=10, pady=5)

        ctk.CTkButton(footer, text="Save & Reload", fg_color="green", command=on_save).pack(pady=10)

    def update_filter_options(self):
        packs = sorted(list(set(self.app.sensor_sources.values())))
        if "Standard" in packs:
            packs.remove("Standard")
            packs.insert(0, "Standard")
        packs.insert(0, "All (Slow)")
        self.app.combo_filter.configure(values=packs)
        if self.filter_var.get() not in packs:
            self.filter_var.set("Standard")
