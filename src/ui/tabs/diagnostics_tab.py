import customtkinter as ctk
from translation import translate

class DiagnosticsTab:
    def __init__(self, parent_frame, app_instance):
        self.frame = parent_frame
        self.app = app_instance

        btn_frame = ctk.CTkFrame(self.frame, fg_color="transparent")
        btn_frame.pack(pady=20)
        self.app.btn_analyze = ctk.CTkButton(btn_frame, text=translate("ui_tab_diagnostics_analyze"), fg_color="purple", width=150,
                                             command=self.app.run_analysis)
        self.app.btn_analyze.pack(side="left", padx=10)
        self.app.btn_scan = ctk.CTkButton(btn_frame, text=translate("ui_tab_diagnostics_scan_codes"), fg_color="blue", width=150,
                                          command=self.app.scan_codes)
        self.app.btn_scan.pack(side="left", padx=10)
        self.app.btn_backup = ctk.CTkButton(btn_frame, text=translate("ui_tab_diagnostics_full_backup"), fg_color="orange", width=150,
                                            command=self.app.perform_full_backup)
        self.app.btn_backup.pack(side="left", padx=10)
        self.app.btn_clear = ctk.CTkButton(btn_frame, text=translate("ui_tab_diagnostics_clear_codes"), fg_color="red", width=150,
                                           command=self.app.confirm_clear_codes)
        self.app.btn_clear.pack(side="left", padx=10)
        self.app.txt_dtc = ctk.CTkTextbox(self.frame, width=700, height=350)
        self.app.txt_dtc.pack(pady=10)
        self.app.txt_dtc.insert("1.0",
            translate("ui_tab_diagnostics_ready_message")
        )


class DebugTab:
    def __init__(self, parent_frame, app_instance):
        self.frame = parent_frame
        self.app = app_instance
        self.app.txt_debug = ctk.CTkTextbox(self.frame, width=700, height=400, font=("Consolas", 12))
        self.app.txt_debug.pack(pady=10, fill="both", expand=True)