import customtkinter as ctk
from ui.tooltip import ToolTip


class DashboardTab:
    def __init__(self, parent_frame, app_instance):
        self.frame = parent_frame
        self.app = app_instance

        self.frame_controls = ctk.CTkFrame(self.frame, height=50)
        self.frame_controls.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(self.frame_controls, text="Port:", font=("Arial", 12)).pack(side="left", padx=(10, 5))
        self.app.combo_ports = ctk.CTkOptionMenu(self.frame_controls, variable=self.app.var_port,
                                                 values=self.app.get_serial_ports(), width=120)
        self.app.combo_ports.pack(side="left", padx=5)

        ctk.CTkButton(self.frame_controls, text="⟳", width=30, command=self.app.refresh_ports).pack(side="left", padx=2)

        self.app.btn_connect = ctk.CTkButton(self.frame_controls, text="CONNECT", fg_color="green",
                                             command=self.app.on_connect_click, width=200)
        self.app.btn_connect.pack(side="left", padx=50)

        self.dash_scroll = ctk.CTkScrollableFrame(self.frame)
        self.dash_scroll.pack(fill="both", expand=True, padx=5, pady=5)

    def rebuild_grid(self):
        for cmd, state in self.app.sensor_state.items():
            if state["card_widget"]:
                state["card_widget"].grid_forget()

        active_sensors = [k for k, v in self.app.sensor_state.items() if v["show_var"].get()]
        cols = 3

        for i, cmd in enumerate(active_sensors):
            row = i // cols;
            col = i % cols
            state = self.app.sensor_state[cmd]

            card = state["card_widget"]

            if card is None:
                card = ctk.CTkFrame(self.dash_scroll)
                self.dash_scroll.grid_columnconfigure(col, weight=1)

                full_name = state['name']
                display_name = full_name

                if len(display_name) > 18:
                    display_name = display_name[:15] + "..."

                if state['unit']:
                    display_name += f" ({state['unit']})"

                lbl_title = ctk.CTkLabel(card, text=display_name, font=("Arial", 12, "bold"), text_color="gray")
                lbl_title.pack(pady=(10, 0))

                val_lbl = ctk.CTkLabel(card, text="--", font=("Arial", 32, "bold"), text_color="#3498db")
                val_lbl.pack(pady=(0, 5))

                bar = ctk.CTkProgressBar(card, width=200, height=10, progress_color="#3498db")
                bar.set(0)
                bar.pack(pady=(0, 15))

                state["card_widget"] = card
                state["widget_value_label"] = val_lbl
                state["widget_progress_bar"] = bar

                tooltip_text = state.get("description", state['name'])

                ToolTip(card, text=tooltip_text, delay=1000)
                ToolTip(lbl_title, text=tooltip_text, delay=1000)
                ToolTip(val_lbl, text=tooltip_text, delay=1000)

            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")