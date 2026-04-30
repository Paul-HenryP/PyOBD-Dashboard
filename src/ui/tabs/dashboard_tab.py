import customtkinter as ctk
import math
from ui.tooltip import ToolTip
from ui.theme import ThemeManager
from ui.widgets.analog_gauge import AnalogGauge
from translation import translate

class DashboardTab:
    def __init__(self, parent_frame, app_instance):
        self.frame = parent_frame
        self.app = app_instance

        self.current_page = 0
        self.items_per_page = 15
        self.total_pages = 1

        self.frame_controls = ctk.CTkFrame(self.frame, height=50, fg_color=ThemeManager.get("BACKGROUND"))
        self.frame_controls.pack(fill="x", padx=10, pady=5)

        
        ctk.CTkLabel(self.frame_controls, text=translate("ui_tab_dashboard_port"), font=("Arial", 12),
                     text_color=ThemeManager.get("TEXT_MAIN")).pack(side="left", padx=(10, 5))

        self.app.var_port = getattr(self.app, "var_port", ctk.StringVar(value="Auto"))

        self.combo_ports = ctk.CTkComboBox(
            self.frame_controls,
            variable=self.app.var_port,
            values=self._get_ports_values(),
            width=200,
            fg_color=ThemeManager.get("CARD_BG"),
            text_color=ThemeManager.get("ACCENT"),
            border_color=ThemeManager.get("ACCENT_DIM"),
            button_color=ThemeManager.get("ACCENT_DIM"),
            dropdown_fg_color=ThemeManager.get("CARD_BG"),
            dropdown_text_color=ThemeManager.get("TEXT_MAIN"),
            dropdown_hover_color=ThemeManager.get("ACCENT_DIM"),
        )
        self.combo_ports.pack(side="left", padx=5)

        ctk.CTkLabel(self.frame_controls, text=translate("ui_tab_dashboard_baud"), font=("Arial", 12),
                     text_color=ThemeManager.get("TEXT_MAIN")).pack(side="left", padx=(10, 5))

        if not hasattr(self.app, "var_baud"):
            self.app.var_baud = ctk.StringVar(value="115200")

        self.combo_baud = ctk.CTkComboBox(
            self.frame_controls,
            variable=self.app.var_baud,
            values=self._get_baud_values(),
            width=120,
            fg_color=ThemeManager.get("CARD_BG"),
            text_color=ThemeManager.get("ACCENT"),
            border_color=ThemeManager.get("ACCENT_DIM"),
            button_color=ThemeManager.get("ACCENT_DIM"),
            dropdown_fg_color=ThemeManager.get("CARD_BG"),
            dropdown_text_color=ThemeManager.get("TEXT_MAIN"),
            dropdown_hover_color=ThemeManager.get("ACCENT_DIM"),
        )
        self.combo_baud.pack(side="left", padx=5)

        ctk.CTkButton(self.frame_controls, text="⟳", width=30, fg_color=ThemeManager.get("CARD_BG"),
                      command=self.refresh_ports_ui).pack(side="left", padx=2)

        self.app.btn_connect = ctk.CTkButton(
            self.frame_controls,
            text=translate("ui_tab_dashboard_connect"),
            fg_color=ThemeManager.get("ACCENT"),
            text_color=ThemeManager.get("BACKGROUND"),
            hover_color=ThemeManager.get("ACCENT_DIM"),
            command=self.app.on_connect_click,
            width=150
        )
        self.app.btn_connect.pack(side="left", padx=20)

        self.btn_next = ctk.CTkButton(self.frame_controls, text=">", width=40, command=self.next_page,
                                      fg_color=ThemeManager.get("CARD_BG"))
        self.btn_next.pack(side="right", padx=5)

        self.lbl_page = ctk.CTkLabel(self.frame_controls, text=translate("ui_tab_dashboard_page").format(1, 1), width=80,
                                     text_color=ThemeManager.get("TEXT_MAIN"))
        self.lbl_page.pack(side="right", padx=5)

        self.btn_prev = ctk.CTkButton(self.frame_controls, text="<", width=40, command=self.prev_page,
                                      fg_color=ThemeManager.get("CARD_BG"))
        self.btn_prev.pack(side="right", padx=5)

        self.dash_scroll = ctk.CTkScrollableFrame(self.frame, fg_color=ThemeManager.get("BACKGROUND"))
        self.dash_scroll.pack(fill="both", expand=True, padx=0, pady=0)

    def _get_ports_values(self):
        ports = []
        try:
            ports = list(self.app.get_serial_ports() or [])
        except:
            ports = []
        values = ["Auto"] + [p for p in ports if p and p != "Auto"]
        seen = set()
        out = []
        for v in values:
            if v not in seen:
                seen.add(v)
                out.append(v)
        return out

    def _get_baud_values(self):
        values = ["9600", "38400", "115200", "230400"]
        cur = ""
        try:
            cur = str(self.app.var_baud.get() or "")
        except:
            cur = ""
        if cur and cur not in values:
            values = [cur] + values
        return values

    def refresh_ports_ui(self):
        typed_port = ""
        typed_baud = ""

        try:
            typed_port = self.app.var_port.get()
        except:
            typed_port = ""
        try:
            typed_baud = self.app.var_baud.get()
        except:
            typed_baud = ""

        port_values = self._get_ports_values()
        self.combo_ports.configure(values=port_values)

        baud_values = self._get_baud_values()
        self.combo_baud.configure(values=baud_values)

        if typed_port:
            self.app.var_port.set(typed_port)
        elif port_values:
            self.app.var_port.set(port_values[0])

        if typed_baud:
            self.app.var_baud.set(typed_baud)
        elif baud_values:
            self.app.var_baud.set(baud_values[0])

        if hasattr(self.app, "refresh_ports") and callable(self.app.refresh_ports):
            try:
                self.app.refresh_ports()
            except:
                pass

    def rebuild_grid(self):
        for widget in self.dash_scroll.winfo_children():
            widget.destroy()

        for cmd, state in self.app.sensor_state.items():
            state["card_widget"] = None
            state["widget_progress_bar"] = None
            state["widget_value_label"] = None

        active_sensors = [k for k, v in self.app.sensor_state.items() if v["show_var"].get()]

        total_items = len(active_sensors)
        self.total_pages = math.ceil(total_items / self.items_per_page)
        if self.total_pages < 1:
            self.total_pages = 1

        if self.current_page >= self.total_pages:
            self.current_page = max(0, self.total_pages - 1)

        self.lbl_page.configure(
            text=translate("ui_tab_dashboard_page").format(self.current_page + 1, self.total_pages)
        )

        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_sensors = active_sensors[start_idx:end_idx]

        cols = 3
        for i, cmd in enumerate(page_sensors):
            row = i // cols
            col = i % cols
            state = self.app.sensor_state[cmd]

            try:
                limit = float(state["limit_var"].get())
            except:
                limit = 100

            container = ctk.CTkFrame(self.dash_scroll, fg_color=ThemeManager.get("CARD_BG"))

            display_name = state["name"]
            if len(display_name) > 18:
                display_name = display_name[:15] + "..."
            if state["unit"]:
                display_name += f" ({state['unit']})"

            lbl_title = ctk.CTkLabel(
                container,
                text=display_name,
                font=("Arial", 14, "bold"),
                text_color=ThemeManager.get("TEXT_MAIN")
            )
            lbl_title.pack(pady=(10, 0))

            gauge = AnalogGauge(
                container,
                width=180,
                height=180,
                min_val=0,
                max_val=limit,
                unit=state["unit"]
            )
            gauge.pack(pady=5)

            state["card_widget"] = container
            state["widget_progress_bar"] = gauge

            tooltip_text = state.get("description", state["name"])
            ToolTip(container, text=tooltip_text, delay=1000)

            container.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

        self.dash_scroll.grid_columnconfigure(0, weight=1)
        self.dash_scroll.grid_columnconfigure(1, weight=1)
        self.dash_scroll.grid_columnconfigure(2, weight=1)

    def next_page(self):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.rebuild_grid()

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.rebuild_grid()
