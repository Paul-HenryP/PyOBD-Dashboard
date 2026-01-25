import customtkinter as ctk
from ui.theme import ThemeManager

class HelpTab:
    def __init__(self, parent_frame, app_instance):
        self.frame = parent_frame
        self.app = app_instance

        self.scroll = ctk.CTkScrollableFrame(self.frame, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)

        self.add_header("PyOBD User Guide & Safety Protocols")

        self.add_sub_header("🛡️ ECU Safety Features")
        safety_text = (
            "This application is designed with multiple layers of protection to ensure "
            "it can be used safely while the engine is running:\n\n"
            "1. PASSIVE READ-ONLY MODE:\n"
            "   By default, the Dashboard and Graph tabs only send 'Read Data' (Mode 01/22) requests. "
            "   These requests asks the ECU to report a value. They do not attempt to change settings, "
            "   making it impossible to accidentally 'brick' an ECU in standard mode.\n\n"
            "2. INTELLIGENT RATE LIMITING:\n"
            "   The application uses an 'Interlaced Polling' engine. It prioritizes critical sensors "
            "   (RPM, Speed) while slowing down requests for static data (Fuel Level). This prevents "
            "   'CAN Bus Flooding', ensuring the car's internal networks (ABS, Airbags) are never "
            "   interrupted by diagnostic traffic.\n\n"
            "3. PROTOCOL ISOLATION:\n"
            "   The 'Clear Codes' command is the only write command available. It is protected by "
            "   a confirmation dialog and a motion lock (disabled while driving)."
        )
        self.add_text(safety_text)

        self.add_sub_header("🚀 Quick Start Guide")
        tutorial_text = (
            "1. CONNECTION:\n"
            "   - Plug the ELM327 adapter into the OBD-II port (usually under the steering wheel).\n"
            "   - Turn Ignition to ON (Engine can be running or off).\n"
            "   - Click the 'Refresh (⟳)' button next to Port.\n"
            "   - Select the COM port (e.g., COM3) and click CONNECT.\n\n"
            "2. PRO PACKS (Custom Data):\n"
            "   - Go to the 'Settings' tab.\n"
            "   - Click 'Manage Pro Packs'.\n"
            "   - Select your car model (e.g., BMW, Ford) and click Save & Reload.\n"
            "   - New sensors will appear in the Settings list. Check 'Show' to see them on the Dashboard.\n\n"
            "3. DYNO MODE:\n"
            "   - Find a safe, private road.\n"
            "   - Enter vehicle weight in the Dyno tab.\n"
            "   - Click 'Start Run', accelerate fully, then click 'Stop'."
        )
        self.add_text(tutorial_text)

        self.add_sub_header("🔧 Troubleshooting")
        trouble_text = (
            "• 'Interface Found, No Connection to ECU':\n"
            "   The adapter is powered, but the car is off. Turn the key to the 'ON' position.\n\n"
            "• 'Laggy' Updates:\n"
            "   Go to Settings and uncheck sensors you don't need. Logging fewer sensors makes the updates faster.\n\n"
            "• 'Unknown Code' in Diagnostics:\n"
            "   The app found a fault code, but it is manufacturer specific. Google the code (e.g. P1234) + your car model."
        )
        self.add_text(trouble_text)

        ctk.CTkLabel(
            self.scroll,
            text="⚠️ DISCLAIMER: Use at your own risk. Always focus on the road while driving.",
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