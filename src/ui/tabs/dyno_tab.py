import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkinter import messagebox
import time
from dyno_engine import DynoEngine
from ui.theme import ThemeManager

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
        ctk.CTkLabel(header_frame, text="PERFORMANCE", font=("Arial", 20, "bold"),
                     text_color=ThemeManager.get("ACCENT")).pack(side="left")
        ctk.CTkButton(header_frame, text="?", width=30, height=30, fg_color=ThemeManager.get("ACCENT_DIM"),
                      command=self.show_help).pack(side="right")

        self.mode_tabs = ctk.CTkTabview(self.panel_left, height=400, fg_color="transparent")
        self.mode_tabs.pack(fill="both", expand=True, padx=5)
        self.tab_dyno = self.mode_tabs.add("Dyno")
        self.tab_drag = self.mode_tabs.add("0-100 km/h")

        ctk.CTkLabel(self.tab_dyno, text="Car Weight (kg):", text_color=ThemeManager.get("TEXT_MAIN")).pack(
            pady=(10, 0))
        self.entry_weight = ctk.CTkEntry(self.tab_dyno, placeholder_text="e.g. 1500")
        self.entry_weight.insert(0, "1600")
        self.entry_weight.pack(pady=5)

        self.lbl_hp = ctk.CTkLabel(self.tab_dyno, text="0 HP", font=("Arial", 30, "bold"),
                                   text_color=ThemeManager.get("TEXT_MAIN"))
        self.lbl_hp.pack(pady=(20, 5))
        ctk.CTkLabel(self.tab_dyno, text="Peak Power", text_color=ThemeManager.get("TEXT_DIM")).pack()

        self.lbl_tq = ctk.CTkLabel(self.tab_dyno, text="0 Nm", font=("Arial", 30, "bold"),
                                   text_color=ThemeManager.get("TEXT_MAIN"))
        self.lbl_tq.pack(pady=(20, 5))
        ctk.CTkLabel(self.tab_dyno, text="Peak Torque", text_color=ThemeManager.get("TEXT_DIM")).pack()

        self.btn_record = ctk.CTkButton(
            self.tab_dyno, text="START DYNO RUN",
            fg_color=ThemeManager.get("ACCENT"), height=50,
            font=("Arial", 14, "bold"), command=self.toggle_recording
        )
        self.btn_record.pack(side="bottom", pady=20, padx=10, fill="x")

        self.lbl_drag_status = ctk.CTkLabel(self.tab_drag, text="STOP CAR TO ARM", font=("Arial", 16, "bold"),
                                            text_color="gray")
        self.lbl_drag_status.pack(pady=(30, 10))

        self.lbl_timer = ctk.CTkLabel(self.tab_drag, text="0.00 s", font=("Arial", 48, "bold"),
                                      text_color=ThemeManager.get("ACCENT"))
        self.lbl_timer.pack(pady=20)

        self.lbl_best = ctk.CTkLabel(self.tab_drag, text="Best: --", text_color=ThemeManager.get("TEXT_DIM"))
        self.lbl_best.pack(pady=10)

        ctk.CTkButton(self.tab_drag, text="RESET", fg_color=ThemeManager.get("WARNING"), command=self.reset_drag).pack(
            side="bottom", pady=20)

        self.panel_right = ctk.CTkFrame(self.frame, fg_color=ThemeManager.get("BACKGROUND"))
        self.panel_right.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        self.fig, self.ax = plt.subplots(figsize=(6, 4), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')
        self.ax.set_facecolor('#2b2b2b')
        self.ax.set_xlabel('RPM', color='white')
        self.ax.set_ylabel('Power (HP)', color=ThemeManager.get("ACCENT"), fontweight='bold')
        self.ax.tick_params(axis='x', colors='white')
        self.ax.tick_params(axis='y', colors='white')
        self.ax.grid(True, color='#404040', linestyle='--', alpha=0.5)

        self.line_hp, = self.ax.plot([], [], color=ThemeManager.get("ACCENT"), linewidth=2, label="HP")

        self.ax2 = self.ax.twinx()
        self.ax2.set_ylabel('Torque (Nm)', color=ThemeManager.get("WARNING"), fontweight='bold')
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
        msg = (
            "PERFORMANCE MODES:\n\n"
            "1. VIRTUAL DYNO (Power Measurement):\n"
            "   - Enter vehicle weight.\n"
            "   - Start Run -> 3rd Gear -> Full Throttle -> Redline -> Stop.\n"
            "   - Displays HP/Torque curve based on acceleration physics.\n\n"
            "2. DRAG STRIP (0-100 km/h):\n"
            "   - Simply stop the car completely (0 km/h).\n"
            "   - Status will change to 'READY'.\n"
            "   - Launch the car!\n"
            "   - Timer stops automatically at 100 km/h."
        )
        messagebox.showinfo("Instructions", msg)

    def toggle_recording(self):
        if self.is_recording:
            self.is_recording = False
            self.btn_record.configure(text="START DYNO RUN", fg_color=ThemeManager.get("ACCENT"))
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
            self.btn_record.configure(text="STOP", fg_color=ThemeManager.get("WARNING"))

    def update_dyno(self, speed_kmh, rpm):
        if self.is_recording:
            hp, torque = self.dyno.calculate_step(self.current_weight, speed_kmh, rpm)
            self.lbl_hp.configure(text=f"{int(self.dyno.peak_hp)} HP")
            self.lbl_tq.configure(text=f"{int(self.dyno.peak_torque)} Nm")

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
                self.lbl_drag_status.configure(text="READY TO LAUNCH", text_color="green")
            elif self.drag_armed and speed > 0:
                self.drag_armed = False
                self.drag_running = True
                self.drag_start_time = time.time()
                self.lbl_drag_status.configure(text="GO! GO! GO!", text_color=ThemeManager.get("ACCENT"))
            else:
                self.lbl_drag_status.configure(text="STOP CAR TO ARM", text_color="gray")

        elif self.drag_running:
            elapsed = time.time() - self.drag_start_time
            self.lbl_timer.configure(text=f"{elapsed:.2f} s")

            if speed >= 100:

                self.drag_running = False
                self.lbl_drag_status.configure(text="FINISHED!", text_color=ThemeManager.get("WARNING"))

                if self.drag_best_time is None or elapsed < self.drag_best_time:
                    self.drag_best_time = elapsed
                    self.lbl_best.configure(text=f"Best: {elapsed:.2f} s")

    def reset_drag(self):
        self.drag_running = False
        self.drag_armed = False
        self.lbl_timer.configure(text="0.00 s")
        self.lbl_drag_status.configure(text="STOP CAR TO ARM", text_color="gray")