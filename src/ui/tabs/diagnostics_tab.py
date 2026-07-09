import customtkinter as ctk


class DiagnosticsTab:
    def __init__(self, parent_frame, app_instance):
        self.frame = parent_frame
        self.app = app_instance

        btn_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        btn_frame.pack(pady=20)
        self.app.btn_analyze = ctk.CTkButton(btn_frame, text="RUN ANALYSIS", fg_color="purple", width=150,
                                             command=self.app.run_analysis)
        self.app.btn_analyze.pack(side="left", padx=10)
        self.app.btn_scan = ctk.CTkButton(btn_frame, text="SCAN CODES", fg_color="blue", width=150,
                                          command=self.app.scan_codes)
        self.app.btn_scan.pack(side="left", padx=10)
        self.app.btn_backup = ctk.CTkButton(btn_frame, text="FULL BACKUP", fg_color="orange", width=150,
                                            command=self.app.perform_full_backup)
        self.app.btn_backup.pack(side="left", padx=10)
        self.app.btn_clear = ctk.CTkButton(btn_frame, text="CLEAR CODES", fg_color="red", width=150,
                                           command=self.app.confirm_clear_codes)
        self.app.btn_clear.pack(side="left", padx=10)
        self.app.txt_dtc = ctk.CTkTextbox(self.frame, width=700, height=350)
        self.app.txt_dtc.pack(pady=10)
        self.app.txt_dtc.insert("1.0",
                                "Ready.\nUse 'Run Analysis' to check sensor data for logic problems.\nUse 'Scan Codes' to check ECU errors.")


class DebugTab:
    def __init__(self, parent_frame, app_instance):
        self.frame = parent_frame
        self.app = app_instance

        info_frame = ctk.CTkFrame(self.frame, fg_color="#2A2D34", corner_radius=8)
        info_frame.pack(pady=(15, 10), fill="x", padx=20)

        info_text = (
            "🔧 Advanced Raw OBD Terminal\n"
            "Send direct AT commands or HEX codes to the ELM327 adapter and vehicle ECU.\n"
            "This is essential for reverse-engineering proprietary protocols (like VW TP2.0 / UDS) or testing unsupported PIDs.\n"
            "⚠️ CAUTION: Do not send random/blind HEX data to the CAN bus while the vehicle is in motion!"
        )
        ctk.CTkLabel(info_frame, text=info_text, justify="left", text_color="#E0E0E0", font=("Arial", 12)).pack(padx=15,
                                                                                                                pady=10,
                                                                                                                anchor="w")

        cmd_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        cmd_frame.pack(pady=5, fill="x", padx=20)

        ctk.CTkLabel(cmd_frame, text="Raw Command:").pack(side="left", padx=(0, 5))

        self.entry_cmd = ctk.CTkEntry(cmd_frame, width=250, placeholder_text="e.g. 0100 or AT Z (Press Enter)")
        self.entry_cmd.pack(side="left", padx=5)
        self.entry_cmd.bind("<Return>", lambda event: self.send_command())

        ctk.CTkButton(cmd_frame, text="SEND", width=80, fg_color="#005b96", command=self.send_command).pack(side="left",
                                                                                                            padx=5)
        ctk.CTkButton(cmd_frame, text="Clear Output", width=100, fg_color="#4A4A4A", hover_color="#333333",
                      command=self.clear_log).pack(side="right", padx=5)

        quick_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        quick_frame.pack(pady=5, fill="x", padx=20)

        ctk.CTkLabel(quick_frame, text="Helpers:").pack(side="left", padx=(0, 5))

        ctk.CTkButton(quick_frame, text="AT DP (Check Protocol)", width=140, fg_color="#3B82F6",
                      command=lambda: self.set_cmd("AT DP")).pack(side="left", padx=5)

        ctk.CTkButton(quick_frame, text="AT SH 7E0 (Target Engine)", width=160, fg_color="#10B981",
                      command=lambda: self.set_cmd("AT SH 7E0")).pack(side="left", padx=5)

        ctk.CTkButton(quick_frame, text="0100 (Check PIDs 1-20)", width=150, fg_color="#8B5CF6",
                      command=lambda: self.set_cmd("0100")).pack(side="left", padx=5)

        # --- TERMINALI VÄLJUND ---
        self.app.txt_debug = ctk.CTkTextbox(self.frame, width=700, height=300, font=("Consolas", 13),
                                            fg_color="#1E1E1E", text_color="#00FF00")
        self.app.txt_debug.pack(pady=(10, 20), fill="both", expand=True, padx=20)

        # Tervitussõnum terminali
        self.app.txt_debug.insert("end",
                                  "Terminal Ready. Type a command or use the helpers above.\n----------------------------------------------------\n")

    def set_cmd(self, cmd_text):
        self.entry_cmd.delete(0, "end")
        self.entry_cmd.insert(0, cmd_text)
        self.send_command()

    def send_command(self):
        cmd = self.entry_cmd.get().strip()
        if not cmd:
            return

        self.app.append_debug_log(f"\n> {cmd}")

        if hasattr(self.app.obd, 'send_raw_command'):
            response = self.app.obd.send_raw_command(cmd)
            self.app.append_debug_log(f"< {response}")
        else:
            self.app.append_debug_log("< ERROR: send_raw_command not implemented in OBDHandler yet!")

        self.entry_cmd.delete(0, "end")
        self.app.txt_debug.see("end")

    def clear_log(self):
        self.app.txt_debug.delete("1.0", "end")
        self.app.log_buffer.clear()
        self.app.txt_debug.insert("end", "Terminal Ready.\n----------------------------------------------------\n")