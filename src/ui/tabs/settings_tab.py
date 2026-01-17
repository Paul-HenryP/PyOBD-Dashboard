import customtkinter as ctk
import os
import json
from config_manager import ConfigManager
from constants import PRO_PACK_DIR


class SettingsTab:
    def __init__(self, parent_frame, app_instance):
        self.frame = parent_frame
        self.app = app_instance

        frame_top = ctk.CTkFrame(self.frame, fg_color="transparent")
        frame_top.pack(fill="x", padx=20, pady=10)

        self.filter_var = ctk.StringVar(value="Standard")
        ctk.CTkLabel(frame_top, text="Show Pack:", font=("Arial", 12)).pack(side="left", padx=5)
        self.app.combo_filter = ctk.CTkOptionMenu(frame_top, variable=self.filter_var, values=["Standard"],
                                                  command=self.refresh_settings_list)
        self.app.combo_filter.pack(side="left", padx=5)

        ctk.CTkButton(frame_top, text="Manage Pro Packs", fg_color="purple", width=150,
                      command=self.open_pack_manager).pack(side="right")

        header_frame = ctk.CTkFrame(self.frame, fg_color="#404040")
        header_frame.pack(fill="x", padx=20)

        frame_all_show = ctk.CTkFrame(header_frame, fg_color="transparent")
        frame_all_show.pack(side="right", padx=5)
        ctk.CTkButton(frame_all_show, text="All", width=30, height=15, font=("Arial", 8),
                      command=lambda: self.toggle_all("show", True)).pack()
        ctk.CTkButton(frame_all_show, text="None", width=30, height=15, font=("Arial", 8), fg_color="gray",
                      command=lambda: self.toggle_all("show", False)).pack()
        ctk.CTkLabel(header_frame, text="Show", width=30).pack(side="right")

        frame_all_log = ctk.CTkFrame(header_frame, fg_color="transparent")
        frame_all_log.pack(side="right", padx=5)
        ctk.CTkButton(frame_all_log, text="All", width=30, height=15, font=("Arial", 8),
                      command=lambda: self.toggle_all("log", True)).pack()
        ctk.CTkButton(frame_all_log, text="None", width=30, height=15, font=("Arial", 8), fg_color="gray",
                      command=lambda: self.toggle_all("log", False)).pack()
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

        frame_log = ctk.CTkFrame(self.frame)
        frame_log.pack(fill="x", padx=20, pady=20)
        self.app.lbl_path = ctk.CTkLabel(frame_log, text=f"Save Path: {self.app.logger.log_dir}")
        self.app.lbl_path.pack(side="left", padx=10)
        ctk.CTkButton(frame_log, text="Change Folder", command=self.app.change_log_folder).pack(side="right", padx=10)

        ctk.CTkSwitch(frame_log, text="Developer Mode", variable=self.app.var_dev_mode,
                      command=self.app.refresh_dev_mode_visibility).pack(side="right", padx=20)

    def refresh_settings_list(self, choice=None):
        for widget in self.settings_scroll.winfo_children(): widget.destroy()

        target_pack = self.filter_var.get()
        row_idx = 0

        items_to_show = []
        for cmd, data in self.app.sensor_state.items():
            src = self.app.sensor_sources.get(cmd, "Standard")
            if target_pack == "All (Slow)" or src == target_pack:
                items_to_show.append((cmd, data))

        for cmd, data in items_to_show:
            ctk.CTkLabel(self.settings_scroll, text=data["name"], anchor="w").grid(row=row_idx, column=0, sticky="w",
                                                                                   padx=10, pady=2)
            ctk.CTkEntry(self.settings_scroll, textvariable=data["limit_var"], width=60).grid(row=row_idx, column=1,
                                                                                              padx=5, pady=2)
            ctk.CTkCheckBox(self.settings_scroll, text="", variable=data["log_var"], width=20).grid(row=row_idx,
                                                                                                    column=2, padx=15,
                                                                                                    pady=2)
            ctk.CTkCheckBox(self.settings_scroll, text="", variable=data["show_var"],
                            command=self.app.mark_dashboard_dirty, width=20).grid(row=row_idx, column=3, padx=15,
                                                                                  pady=2)
            row_idx += 1
            if row_idx % 20 == 0: self.app.update_idletasks()

    def toggle_all(self, type_str, state):
        target_pack = self.filter_var.get()
        for cmd, data in self.app.sensor_state.items():
            src = self.app.sensor_sources.get(cmd, "Standard")
            if target_pack == "All (Slow)" or src == target_pack:
                if type_str == "show":
                    data["show_var"].set(state)
                elif type_str == "log":
                    data["log_var"].set(state)

        if type_str == "show": self.app.mark_dashboard_dirty()

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
                    if f.endswith(".json"):
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

            self.app.configure(cursor="watch");
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