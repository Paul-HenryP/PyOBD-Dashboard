import customtkinter as ctk
import math
from ui.tooltip import ToolTip
from ui.theme import ThemeManager
from ui.widgets.analog_gauge import AnalogGauge


class DashboardTab:
    def __init__(self, parent_frame, app_instance):
        self.frame = parent_frame
        self.app = app_instance

        self.current_page = 0
        self.items_per_page = 15
        self.total_pages = 1

        self.frame_controls = ctk.CTkFrame(self.frame, height=50, fg_color=ThemeManager.get("BACKGROUND"))
        self.frame_controls.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(self.frame_controls, text="Port:", font=("Arial", 12),
                     text_color=ThemeManager.get("TEXT_MAIN")).pack(side="left", padx=(10, 5))

        self.app.var_port = ctk.StringVar(value="Auto")
        self.combo_ports = ctk.CTkOptionMenu(
            self.frame_controls,
            variable=self.app.var_port,
            values=self.app.get_serial_ports(),
            width=100,
            fg_color=ThemeManager.get("CARD_BG"),
            text_color=ThemeManager.get("ACCENT"),
            button_color=ThemeManager.get("ACCENT_DIM")
        )
        self.combo_ports.pack(side="left", padx=5)

        ctk.CTkButton(self.frame_controls, text="⟳", width=30, fg_color=ThemeManager.get("CARD_BG"),
                      command=self.app.refresh_ports).pack(side="left", padx=2)

        self.app.btn_connect = ctk.CTkButton(
            self.frame_controls,
            text="CONNECT",
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

        self.lbl_page = ctk.CTkLabel(self.frame_controls, text="Page 1/1", width=80,
                                     text_color=ThemeManager.get("TEXT_MAIN"))
        self.lbl_page.pack(side="right", padx=5)

        self.btn_prev = ctk.CTkButton(self.frame_controls, text="<", width=40, command=self.prev_page,
                                      fg_color=ThemeManager.get("CARD_BG"))
        self.btn_prev.pack(side="right", padx=5)

        self.dash_scroll = ctk.CTkScrollableFrame(self.frame, fg_color=ThemeManager.get("BACKGROUND"))
        self.dash_scroll.pack(fill="both", expand=True, padx=0, pady=0)

    def rebuild_grid(self):
        for cmd, state in self.app.sensor_state.items():
            if state["card_widget"]:
                state["card_widget"].grid_forget()

        active_sensors = [k for k, v in self.app.sensor_state.items() if v["show_var"].get()]

        total_items = len(active_sensors)
        self.total_pages = math.ceil(total_items / self.items_per_page)
        if self.total_pages < 1: self.total_pages = 1

        if self.current_page >= self.total_pages:
            self.current_page = self.total_pages - 1
        if self.current_page < 0:
            self.current_page = 0

        self.lbl_page.configure(text=f"Page {self.current_page + 1}/{self.total_pages}")

        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_sensors = active_sensors[start_idx:end_idx]

        cols = 3
        for i, cmd in enumerate(page_sensors):
            row = i // cols;
            col = i % cols
            state = self.app.sensor_state[cmd]

            container = state["card_widget"]

            if container is None:
                try:
                    limit = float(state['limit_var'].get())
                except:
                    limit = 100

                container = ctk.CTkFrame(self.dash_scroll, fg_color=ThemeManager.get("CARD_BG"))

                display_name = state['name']
                if len(display_name) > 18:
                    display_name = display_name[:15] + "..."
                if state['unit']:
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
                    unit=state['unit']
                )
                gauge.pack(pady=5)

                val_lbl = ctk.CTkLabel(container, text="--", text_color=ThemeManager.get("ACCENT"))

                state["card_widget"] = container
                state["widget_progress_bar"] = gauge
                state["widget_title_label"] = lbl_title
                state["widget_value_label"] = val_lbl

                tooltip_text = state.get("description", state['name'])
                ToolTip(container, text=tooltip_text, delay=1000)

            state["card_widget"].grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

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