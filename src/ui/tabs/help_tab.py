import customtkinter as ctk
from ui.theme import ThemeManager
from translation import translate
class HelpTab:
    def __init__(self, parent_frame, app_instance):
        self.frame = parent_frame
        self.app = app_instance

        self.scroll = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)

        self.add_header(translate("ui_tab_help_guide_safety"))

        self.add_sub_header(translate("ui_tab_help_safety_header"))
        self.add_text(translate("ui_tab_help_safety"))

        self.add_sub_header(translate("ui_tab_help_tutorial_header"))
        self.add_text(translate("ui_tab_help_tutorial"))

        self.add_sub_header(translate("ui_tab_help_troubleshooting_header"))
        self.add_text(translate("ui_tab_help_troubleshooting"))

        ctk.CTkLabel(
            self.scroll,
            text=translate("ui_tab_help_warning"),
            text_color=ThemeManager.get("WARNING"),
            font=("Arial", 12, "bold")
        ).pack(pady=20, anchor="w")

    def add_header(self, text):
        ctk.CTkLabel(
            self.scroll,
            text=text,
            font=("Arial", 24, "bold"),
            text_color=ThemeManager.get("ACCENT")
        ).pack(pady=(10, 20), anchor="w")

    def add_sub_header(self, text):
        ctk.CTkLabel(
            self.scroll,
            text=text,
            font=("Arial", 16, "bold"),
            text_color=ThemeManager.get("TEXT_MAIN")
        ).pack(pady=(20, 5), anchor="w")

    def add_text(self, text):
        ctk.CTkLabel(
            self.scroll,
            text=text,
            font=("Arial", 12),
            text_color=ThemeManager.get("TEXT_DIM"),
            justify="left",
            wraplength=700

        ).pack(pady=2, anchor="w")