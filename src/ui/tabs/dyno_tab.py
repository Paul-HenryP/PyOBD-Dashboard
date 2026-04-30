import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import messagebox
import time
from dyno_engine import DynoEngine
from ui.theme import ThemeManager
from translation import translate

class DynoTab:
    def __init__(self, parent_frame, app_instance):
        self.frame = parent_frame
        self.app = app_instance
        self.dyno = DynoEngine()

        self.is_recording = False
        self.current_weight = 1600

        self.drag_armed = False
        self.drag_running = False
        self.drag_start_time = 0
        self.drag_best_time = None

        self.panel_left = ctk.CTkFrame(self.frame, width=300, fg_color=ThemeManager.get("CARD_BG"))
        self.panel_left.pack(side="left", fill="y", padx=10, pady=10)

        header_frame = ctk.CTkFrame(self.panel_left, fg_color="transparent")
        header_frame.pack(fill="x", pady=20, padx=10)
        ctk.CTkLabel(header_frame, text=translate("ui_tab_dyno_performance"), font=("Arial", 20, "bold"),
                     text_color=ThemeManager.get("ACCENT")).pack(side="left")
        ctk.CTkButton(header_frame, text="?", width=30, height=30, fg_color=ThemeManager.get("ACCENT_DIM"),
                      command=self.show_help).pack(side="right")

        self.mode_tabs = ctk.CTkTabview(self.panel_left, height=400, fg_color="transparent")
        self.mode_tabs.pack(fill="both", expand=True, padx=5)
        self.tab_dyno = self.mode_tabs.add(translate("ui_tab_dyno_mode_dyno"))
        self.tab_drag = self.mode_tabs.add(translate("ui_tab_dyno_drag"))

        ctk.CTkLabel(self.tab_dyno, text=translate("ui_tab_dyno_car_weight"), text_color=ThemeManager.get("TEXT_MAIN")).pack(
            pady=(10, 0))
        self.entry_weight = ctk.CTkEntry(self.tab_dyno, placeholder_text=translate("ui_tab_dyno_car_weight_entry_placeholder"))
        self.entry_weight.insert(0, "1600")
        self.entry_weight.pack(pady=5)

        self.lbl_hp = ctk.CTkLabel(self.tab_dyno, text=translate("ui_tab_dyno_hp").format(0), font=("Arial", 30, "bold"),
                                   text_color=ThemeManager.get("TEXT_MAIN"))
        self.lbl_hp.pack(pady=(20, 5))
        ctk.CTkLabel(self.tab_dyno, text=translate("ui_tab_dyno_peak_power"), text_color=ThemeManager.get("TEXT_DIM")).pack()

        self.lbl_tq = ctk.CTkLabel(self.tab_dyno, text=translate("ui_tab_dyno_torque").format(0), font=("Arial", 30, "bold"),
                                   text_color=ThemeManager.get("TEXT_MAIN"))
        self.lbl_tq.pack(pady=(20, 5))
        ctk.CTkLabel(self.tab_dyno, text=translate("ui_tab_dyno_torque_title"), text_color=ThemeManager.get("TEXT_DIM")).pack()

        self.btn_record = ctk.CTkButton(
            self.tab_dyno, text=translate("ui_tab_dyno_start"),
            fg_color=ThemeManager.get("ACCENT"), height=50,
            font=("Arial", 14, "bold"), command=self.toggle_recording
        )
        self.btn_record.pack(side="bottom", pady=20, padx=10, fill="x")

        self.lbl_drag_status = ctk.CTkLabel(self.tab_drag, text=translate("ui_tab_dyno_drag_status_stop"), font=("Arial", 16, "bold"),
                                            text_color="gray")
        self.lbl_drag_status.pack(pady=(30, 10))

        self.lbl_timer = ctk.CTkLabel(self.tab_drag, text=translate("ui_tab_dyno_drag_timer").format(0), font=("Arial", 48, "bold"),
                                      text_color=ThemeManager.get("ACCENT"))
        self.lbl_timer.pack(pady=20)

        self.lbl_best = ctk.CTkLabel(self.tab_drag, text=translate("ui_tab_dyno_drag_best").format(0), text_color=ThemeManager.get("TEXT_DIM"))
        self.lbl_best.pack(pady=10)

        ctk.CTkButton(self.tab_drag, text=translate("ui_tab_dyno_drag_reset"), fg_color=ThemeManager.get("WARNING"), command=self.reset_drag).pack(
            side="bottom", pady=20)

        self.panel_right = ctk.CTkFrame(self.frame, fg_color=ThemeManager.get("BACKGROUND"))
        self.panel_right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')
        self.ax.set_facecolor('#2b2b2b')
        self.ax.set_xlabel(translate("ui_tab_dyno_graph_x_axis"), color='white')
        self.ax.set_ylabel(translate("ui_tab_dyno_graph_y_axis"), color=ThemeManager.get("ACCENT"), fontweight='bold')
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        self.ax.grid(True, color='#404040', linestyle='--', alpha=0.5)

        self.line_hp, = self.ax.plot([], [], color=ThemeManager.get("ACCENT"), linewidth=2, label="HP")

        self.ax2 = self.ax.twinx()
        self.ax2.set_ylabel(translate("ui_tab_dyno_graph_y2_axis"), color=ThemeManager.get("WARNING"), fontweight='bold')
        self.ax2.tick_params(axis='y', labelcolor=ThemeManager.get("WARNING"), colors='white')
        self.ax2.spines['bottom'].set_color('white');
        self.ax2.spines['top'].set_color('white')
        self.ax2.spines['left'].set_color('white');
        self.ax2.spines['right'].set_color('white')

        self.line_tq, = self.ax2.plot([], [], color=ThemeManager.get("WARNING"), linewidth=2, label="Torque")

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.panel_right)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        self.x_rpm = []
        self.y_hp = []
        self.y_tq = []

    def show_help(self):
        messagebox.showinfo(translate("ui_tab_dyno_help_title"), translate("ui_tab_dyno_help_message"))

    def toggle_recording(self):
        if self.is_recording:
            self.is_recording = False
            self.btn_record.configure(text=translate("ui_tab_dyno_start"), fg_color=ThemeManager.get("ACCENT"))
        else:
            try:
                weight = float(self.entry_weight.get())
            except ValueError:
                weight = 1600

            self.dyno.reset()
            self.x_rpm.clear();
            self.y_hp.clear();
            self.y_tq.clear()
            self.is_recording = True
            self.current_weight = weight
            self.btn_record.configure(text=translate("ui_tab_dyno_stop"), fg_color=ThemeManager.get("WARNING"))

    def update_dyno(self, speed_kmh, rpm):
        if self.is_recording:
            hp, torque = self.dyno.calculate_step(self.current_weight, speed_kmh, rpm)
            self.lbl_hp.configure(text=translate("ui_tab_dyno_hp").format(int(self.dyno.peak_hp)))
            self.lbl_tq.configure(text=translate("ui_tab_dyno_torque").format(int(self.dyno.peak_torque)))

            if rpm > 1000 and hp > 0:
                self.x_rpm.append(rpm)
                self.y_hp.append(hp)
                self.y_tq.append(torque)

                self.line_hp.set_data(self.x_rpm, self.y_hp)
                self.line_tq.set_data(self.x_rpm, self.y_tq)

                if self.x_rpm:
                    self.ax.set_xlim(min(self.x_rpm), max(self.x_rpm) + 500)
                    self.ax.set_ylim(0, max(self.y_hp) * 1.2)
                    self.ax2.set_ylim(0, max(self.y_tq) * 1.2)
                self.canvas.draw_idle()

        self._update_drag_strip(speed_kmh)

    def _update_drag_strip(self, speed):
        if not self.drag_running:
            if speed == 0:
                self.drag_armed = True
                self.lbl_drag_status.configure(text=translate("ui_tab_dyno_drag_status_ready"), text_color="green")
            elif self.drag_armed and speed > 0:
                self.drag_armed = False
                self.drag_running = True
                self.drag_start_time = time.time()
                self.lbl_drag_status.configure(text=translate("ui_tab_dyno_drag_status_go"), text_color=ThemeManager.get("ACCENT"))
            else:
                self.lbl_drag_status.configure(text=translate("ui_tab_dyno_drag_status_stop"), text_color="gray")

        elif self.drag_running:
            elapsed = time.time() - self.drag_start_time
            self.lbl_timer.configure(text=translate("ui_tab_dyno_timer").format(elapsed))

            if speed >= 100:

                self.drag_running = False
                self.lbl_drag_status.configure(text=translate("ui_tab_dyno_drag_status_finished"), text_color=ThemeManager.get("WARNING"))

                if self.drag_best_time is None or elapsed < self.drag_best_time:
                    self.drag_best_time = elapsed
                    self.lbl_best.configure(text=translate("ui_tab_dyno_best").format(elapsed))
    def reset_drag(self):
        self.drag_running = False
        self.drag_armed = False
        self.lbl_timer.configure(text=translate("ui_tab_dyno_timer").format(0.0))
        self.lbl_drag_status.configure(text=translate("ui_tab_dyno_drag_status_stop"), text_color="gray")