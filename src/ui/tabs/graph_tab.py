import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class GraphTab:
    def __init__(self, parent_frame, app_instance):
        self.frame = parent_frame
        self.app = app_instance

        controls = ctk.CTkFrame(self.frame)
        controls.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(controls, text="Left Axis (Blue):", text_color="#3498db", font=("Arial", 12, "bold")).pack(
            side="left", padx=5)
        self.app.menu_left = ctk.CTkOptionMenu(controls, variable=self.app.var_graph_left, values=["RPM"])
        self.app.menu_left.pack(side="left", padx=5)

        ctk.CTkLabel(controls, text="Right Axis (Red):", text_color="#e74c3c", font=("Arial", 12, "bold")).pack(
            side="left", padx=5)
        self.app.menu_right = ctk.CTkOptionMenu(controls, variable=self.app.var_graph_right, values=["SPEED"])
        self.app.menu_right.pack(side="left", padx=5)

        self.fig, self.ax1 = plt.subplots(figsize=(6, 4), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b')
        self.ax1.set_facecolor('#2b2b2b')
        self.ax1.tick_params(axis='y', labelcolor='#3498db', colors='white')
        self.ax1.tick_params(axis='x', colors='white')
        self.ax1.grid(True, color='#404040', linestyle='--', alpha=0.5)

        self.ax2 = self.ax1.twinx()
        self.ax2.tick_params(axis='y', labelcolor='#e74c3c', colors='white')
        self.ax2.spines['bottom'].set_color('white');
        self.ax2.spines['top'].set_color('white')
        self.ax2.spines['left'].set_color('white');
        self.ax2.spines['right'].set_color('white')

        self.line_rpm, = self.ax1.plot([], [], color='#3498db', linewidth=2)
        self.line_speed, = self.ax2.plot([], [], color='#e74c3c', linewidth=2)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    def update(self):
        left_key = self.app.var_graph_left.get()
        right_key = self.app.var_graph_right.get()

        data_left = self.app.sensor_history[left_key]
        data_right = self.app.sensor_history[right_key]
        x_data = list(range(len(data_left)))

        self.line_rpm.set_data(x_data, data_left)
        self.line_speed.set_data(x_data, data_right)

        if data_left:
            max_l = max(data_left) if max(data_left) > 0 else 100
            self.ax1.set_ylim(0, max_l * 1.2)
            self.ax1.set_xlim(0, len(data_left))

        if data_right:
            max_r = max(data_right) if max(data_right) > 0 else 100
            self.ax2.set_ylim(0, max_r * 1.2)
            self.ax2.set_xlim(0, len(data_right))

        name_left = self.app.sensor_state[left_key]["name"] if left_key in self.app.sensor_state else left_key
        name_right = self.app.sensor_state[right_key]["name"] if right_key in self.app.sensor_state else right_key

        self.ax1.set_ylabel(name_left, color='#3498db', fontsize=10, fontweight='bold')
        self.ax2.set_ylabel(name_right, color='#e74c3c', fontsize=10, fontweight='bold')

        self.canvas.draw_idle()