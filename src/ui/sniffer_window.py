import customtkinter as ctk
import threading
import serial.tools.list_ports
from tkinter import filedialog, simpledialog, messagebox

from ui.theme import ThemeManager
from can_handler import CanHandler
from can_session import CanSessionManager


class SnifferApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.last_known_packets = {}
        self.can = CanHandler()
        self.session = CanSessionManager()
        self.session.create_new_session()

        self.title("PyCAN Hacker - Reverse Engineering Tool")
        self.geometry("1100x700")

        ThemeManager.set_theme("Cyber")
        self.configure(fg_color=ThemeManager.get("BACKGROUND"))

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_lab = self.tabview.add("CAN Laboratory")
        self.tab_help = self.tabview.add("Hacker's Manual & Safety")

        self._setup_lab_tab()
        self._setup_help_tab()

    def _setup_help_tab(self):
        scroll = ctk.CTkScrollableFrame(self.tab_help, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(
            scroll,
            text="⚠️ CRITICAL SAFETY WARNINGS",
            font=("Arial", 24, "bold"),
            text_color=ThemeManager.get("WARNING")
        ).pack(pady=(10, 20), anchor="w")

        warning_text = (
            "This tool provides RAW ACCESS to your vehicle's Controller Area Network (CAN). "
            "Unlike OBD-II scanners which ask questions, this tool allows you to shout commands.\n\n"
            "1. DO NOT INJECT RANDOM DATA while driving.\n"
            "   Sending random IDs can accidentally trigger airbags, lock electronic parking brakes, "
            "   or kill the engine. Only inject commands you have verified on a stationary vehicle.\n\n"
            "2. THE 'FLOOD' RISK:\n"
            "   The 'Start Sniffing' button puts the adapter into 'Monitor All' mode. On modern cars, "
            "   this generates thousands of messages per second. Cheap ELM327 clones may freeze or "
            "   crash under this load. Always use the 'Filter ID' box if possible to reduce load."
        )
        ctk.CTkLabel(scroll, text=warning_text, font=("Arial", 12), text_color=ThemeManager.get("TEXT_MAIN"),
                     justify="left", wraplength=900).pack(anchor="w")

        ctk.CTkLabel(
            scroll,
            text="🕵️ How to Reverse Engineer (Find Hidden Features)",
            font=("Arial", 20, "bold"),
            text_color=ThemeManager.get("ACCENT")
        ).pack(pady=(30, 10), anchor="w")

        tutorial_text = (
            "GOAL: Find the code that rolls down the window.\n\n"
            "STEP 1: CONNECT & SNIFF\n"
            "   - Connect to the port.\n"
            "   - Click 'Start Sniff'. You will see a waterfall of data.\n"
            "   - It is likely too fast to read. Click 'Stop'.\n\n"
            "STEP 2: ISOLATE THE NOISE\n"
            "   - Cars are noisy. Even doing nothing, the engine sends RPM data constantly.\n"
            "   - Try to guess the ID. Body controls (windows/lights) are often in the 200-400 Hex range.\n"
            "   - Enter '290' (example) in the Filter box and Sniff again. It should be quieter.\n\n"
            "STEP 3: THE ACTION\n"
            "   - Enable 'Diff Mode' (Difference Analyzer).\n"
            "   - With the sniffer running, press the physical Window button in your car.\n"
            "   - Watch for a byte that turns RED exactly when you press the button.\n"
            "   - Example: ID 290 changes from '00 00' to '01 00'.\n\n"
            "STEP 4: REPLAY ATTACK\n"
            "   - Stop sniffing.\n"
            "   - Type the ID (290) and Data (01 00) into the Injector column.\n"
            "   - Click 'FIRE ONCE'. If the window moves, you have successfully hacked it!\n"
            "   - Click 'Add Selected to Library' to save it for later."
        )
        ctk.CTkLabel(scroll, text=tutorial_text, font=("Arial", 12), text_color=ThemeManager.get("TEXT_DIM"),
                     justify="left", wraplength=900).pack(anchor="w")

    def _setup_lab_tab(self):
        frame = self.tab_lab

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)
        frame.grid_columnconfigure(2, weight=1)
        frame.grid_rowconfigure(1, weight=1)

        self.header = ctk.CTkFrame(frame, height=50, fg_color=ThemeManager.get("CARD_BG"))
        self.header.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=10)

        ctk.CTkLabel(self.header, text="HARDWARE:", font=("Arial", 12, "bold"),
                     text_color=ThemeManager.get("TEXT_DIM")).pack(side="left", padx=(20, 5))

        self.var_port = ctk.StringVar(value="Select Port")
        self.combo_ports = ctk.CTkOptionMenu(
            self.header,
            variable=self.var_port,
            values=self.get_serial_ports(),
            width=150,
            fg_color=ThemeManager.get("BACKGROUND"),
            text_color=ThemeManager.get("ACCENT")
        )
        self.combo_ports.pack(side="left", padx=10)

        ctk.CTkButton(self.header, text="⟳", width=30, command=self.refresh_ports,
                      fg_color=ThemeManager.get("BACKGROUND")).pack(side="left", padx=2)

        self.btn_connect = ctk.CTkButton(
            self.header, text="CONNECT HARDWARE",
            fg_color=ThemeManager.get("ACCENT"),
            text_color=ThemeManager.get("BACKGROUND"),
            command=self.on_connect_click
        )
        self.btn_connect.pack(side="left", padx=20)

        self.frame_sniff = ctk.CTkFrame(frame, fg_color="transparent")
        self.frame_sniff.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)

        ctk.CTkLabel(self.frame_sniff, text="Live Traffic", font=("Arial", 14, "bold"),
                     text_color=ThemeManager.get("TEXT_MAIN")).pack(anchor="w")

        self.frame_filter = ctk.CTkFrame(self.frame_sniff, fg_color="transparent")
        self.frame_filter.pack(fill="x", pady=5)

        self.entry_filter = ctk.CTkEntry(self.frame_filter, placeholder_text="Filter ID (e.g. 7E8)")
        self.entry_filter.pack(side="left", fill="x", expand=True, padx=(0, 5))

        self.var_diff_mode = ctk.BooleanVar(value=False)
        self.switch_diff = ctk.CTkSwitch(self.frame_filter, text="Diff Mode", variable=self.var_diff_mode,
                                         progress_color=ThemeManager.get("WARNING"),
                                         text_color=ThemeManager.get("TEXT_DIM"))
        self.switch_diff.pack(side="left", padx=10)

        self.btn_sniff = ctk.CTkButton(self.frame_filter, text="START SNIFF", fg_color="green", width=100,
                                       command=self.toggle_sniff)
        self.btn_sniff.pack(side="right")

        self.txt_log = ctk.CTkTextbox(self.frame_sniff, font=("Consolas", 12), text_color=ThemeManager.get("TEXT_MAIN"),
                                      fg_color=ThemeManager.get("CARD_BG"))
        self.txt_log.pack(fill="both", expand=True)

        self.txt_log.tag_config("diff", foreground=ThemeManager.get("WARNING"))
        self.txt_log.tag_config("id_tag", foreground=ThemeManager.get("ACCENT"))
        self.txt_log.tag_config("tx", foreground="#00FF00")

        ctk.CTkButton(self.frame_sniff, text="Add Selected to Library ->", command=self.save_from_log,
                      fg_color=ThemeManager.get("CARD_BG")).pack(fill="x", pady=5)

        self.frame_inject = ctk.CTkFrame(frame, width=250, fg_color=ThemeManager.get("CARD_BG"))
        self.frame_inject.grid(row=1, column=1, sticky="ns", padx=5, pady=5)

        ctk.CTkLabel(self.frame_inject, text="Injector", font=("Arial", 14, "bold"),
                     text_color=ThemeManager.get("TEXT_MAIN")).pack(pady=15)

        ctk.CTkLabel(self.frame_inject, text="CAN ID (Hex):", text_color=ThemeManager.get("TEXT_DIM")).pack(anchor="w",
                                                                                                            padx=15)
        self.entry_id = ctk.CTkEntry(self.frame_inject, placeholder_text="7E0")
        self.entry_id.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(self.frame_inject, text="Data Payload (Hex):", text_color=ThemeManager.get("TEXT_DIM")).pack(
            anchor="w", padx=15)
        self.entry_data = ctk.CTkEntry(self.frame_inject, placeholder_text="01 0D")
        self.entry_data.pack(fill="x", padx=15, pady=(0, 20))

        self.btn_inject = ctk.CTkButton(
            self.frame_inject, text="FIRE ONCE",
            fg_color=ThemeManager.get("WARNING"),
            hover_color=ThemeManager.get("ACCENT_DIM"),
            height=50, command=self.inject_once
        )
        self.btn_inject.pack(fill="x", padx=15)

        self.frame_lib = ctk.CTkFrame(frame, fg_color="transparent")
        self.frame_lib.grid(row=1, column=2, sticky="nsew", padx=10, pady=5)

        self.frame_lib_tools = ctk.CTkFrame(self.frame_lib, fg_color="transparent")
        self.frame_lib_tools.pack(fill="x", pady=5)
        ctk.CTkButton(self.frame_lib_tools, text="Load File", width=80, command=self.load_file).pack(side="left",
                                                                                                     padx=2)
        ctk.CTkButton(self.frame_lib_tools, text="Save File", width=80, command=self.save_file).pack(side="left",
                                                                                                     padx=2)

        ctk.CTkLabel(self.frame_lib, text="Known Commands", font=("Arial", 14, "bold"),
                     text_color=ThemeManager.get("TEXT_MAIN")).pack(anchor="w", pady=5)

        self.scroll_lib = ctk.CTkScrollableFrame(self.frame_lib, fg_color=ThemeManager.get("CARD_BG"))
        self.scroll_lib.pack(fill="both", expand=True)

        self.refresh_library_ui()

    def get_serial_ports(self):
        ports = ["Demo Mode"]
        try:
            for port in serial.tools.list_ports.comports():
                ports.append(port.device)
        except:
            pass
        return ports if ports else ["No Ports Found"]

    def refresh_ports(self):
        self.combo_ports.configure(values=self.get_serial_ports())

    def on_connect_click(self):
        self.btn_connect.configure(state="disabled", text="Working...")
        threading.Thread(target=self.bg_toggle_connection, daemon=True).start()

    def bg_toggle_connection(self):
        success = False
        is_disconnecting = False

        if self.can.is_sniffing or (self.can.ser and self.can.ser.is_open) or self.can.simulation:
            is_disconnecting = True
            self.can.disconnect()
            success = True
        else:
            port = self.var_port.get()
            if port == "Select Port" or port == "No Ports Found":
                success = False
            else:
                success = self.can.connect(port)

        self.after(0, lambda: self.post_connect_update(success, is_disconnecting))

    def post_connect_update(self, success, is_disconnecting):
        self.btn_connect.configure(state="normal")

        if is_disconnecting:
            self.btn_connect.configure(text="CONNECT HARDWARE", fg_color=ThemeManager.get("ACCENT"))
            self.btn_sniff.configure(state="disabled")
            self.btn_inject.configure(state="disabled")
        else:
            if success:
                self.btn_connect.configure(text="DISCONNECT", fg_color=ThemeManager.get("WARNING"))
                self.btn_sniff.configure(state="normal")
                self.btn_inject.configure(state="normal")
            else:
                messagebox.showerror("Error", "Failed to open serial port. Check connection.")

    def toggle_sniff(self):
        if self.can.is_sniffing:
            self.can.stop_sniffing()
            self.btn_sniff.configure(text="START SNIFF", fg_color="green")
        else:
            self.last_known_packets.clear()
            self.can.start_sniffing(self.entry_filter.get(), self.process_can_line)
            self.btn_sniff.configure(text="STOP SNIFF", fg_color="red")

    def process_can_line(self, line):
        parts = line.split()
        if len(parts) < 2: return

        can_id = parts[0]
        data_str = " ".join(parts[1:])

        if self.var_diff_mode.get():
            prev_data = self.last_known_packets.get(can_id)
            if prev_data != data_str:
                self.print_diff_line(can_id, prev_data, data_str)
                self.last_known_packets[can_id] = data_str
        else:
            self.txt_log.insert("end", f"{can_id} {data_str}\n")
            self.txt_log.see("end")

    def print_diff_line(self, can_id, prev_data, new_data):
        self.txt_log.insert("end", f"{can_id} ", "id_tag")

        if prev_data is None:
            self.txt_log.insert("end", f"{new_data}\n")
        else:
            new_bytes = new_data.split()
            prev_bytes = prev_data.split()

            for i, byte in enumerate(new_bytes):
                if i < len(prev_bytes) and byte != prev_bytes[i]:
                    self.txt_log.insert("end", f"{byte} ", "diff")
                else:
                    self.txt_log.insert("end", f"{byte} ")

            self.txt_log.insert("end", "\n")

        self.txt_log.see("end")

    def inject_once(self):
        if not self.can.ser and not self.can.simulation:
            return

        cid = self.entry_id.get()
        data = self.entry_data.get()

        if not cid or not data:
            return

        self.txt_log.insert("end", f"--> TX: {cid} {data}\n", "tx")

        was_sniffing = self.can.is_sniffing

        response = self.can.inject_frame(cid, data)

        if response:
            self.txt_log.insert("end", f"<-- RX: {response}\n")

        self.txt_log.see("end")

        if was_sniffing:
            self.can.start_sniffing(self.entry_filter.get(), self.process_can_line)
        else:
            self.btn_sniff.configure(text="START SNIFF", fg_color="green")

    def save_from_log(self):
        try:
            selected_text = self.txt_log.selection_get()
            if not selected_text: return
            name = ctk.CTkInputDialog(text="Name this packet:", title="Add to Library").get_input()
            if name:
                self.session.save_command(name, "RAW", selected_text)
                self.refresh_library_ui()
        except:
            pass

    def refresh_library_ui(self):
        for widget in self.scroll_lib.winfo_children(): widget.destroy()

        for cmd in self.session.saved_commands:
            row = ctk.CTkFrame(self.scroll_lib, fg_color="transparent")
            row.pack(fill="x", pady=2)

            ctk.CTkButton(row, text="▶", width=30, fg_color=ThemeManager.get("ACCENT"),
                          command=lambda d=cmd['data'], i=cmd['id']: self.load_to_injector(i, d)).pack(side="left",
                                                                                                       padx=2)

            ctk.CTkLabel(row, text=cmd['name'], text_color="white", width=120, anchor="w").pack(side="left", padx=5)
            ctk.CTkLabel(row, text=cmd['data'], text_color="gray").pack(side="left", padx=5)

    def load_to_injector(self, i, d):
        self.entry_data.delete(0, "end");
        self.entry_data.insert(0, d)
        if i != "RAW": self.entry_id.delete(0, "end"); self.entry_id.insert(0, i)

    def save_file(self):
        path = filedialog.asksaveasfilename(defaultextension=".json")
        if path: self.session.save_session_to_file(path)

    def load_file(self):
        path = filedialog.askopenfilename()
        if path:
            self.session.load_session_from_file(path)
            self.refresh_library_ui()