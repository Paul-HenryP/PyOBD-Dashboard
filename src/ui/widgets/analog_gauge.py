import tkinter as tk
import customtkinter as ctk
from ui.theme import ThemeManager


class AnalogGauge(ctk.CTkFrame):
    def __init__(self, parent, width=150, height=150, min_val=0, max_val=100, unit=""):
        super().__init__(parent, width=width, height=height, fg_color="transparent")

        self.min_val = min_val
        self.max_val = max_val
        self.unit = unit
        self.current_value = min_val

        self.canvas = tk.Canvas(
            self,
            width=width,
            height=height,
            bg=ThemeManager.get("GAUGE_BG"),
            highlightthickness=0
        )
        self.canvas.pack(expand=True, fill="both")

        self.size = width
        self.padding = 15
        self.arc_start = 135
        self.arc_extent = 270

        # Init drawing elements
        self.bg_arc = self.canvas.create_arc(0, 0, 0, 0, style="arc", width=12)
        self.active_arc = self.canvas.create_arc(0, 0, 0, 0, style="arc", width=12)
        self.text_val = self.canvas.create_text(0, 0, text="--", font=("Arial", 24, "bold"))
        self.text_unit = self.canvas.create_text(0, 0, text=unit, font=("Arial", 10))

        self.redraw_colors()
        self.update_value(self.min_val)

    def redraw_colors(self):
        try:
            self.canvas.configure(bg=ThemeManager.get("GAUGE_BG"))

            self.canvas.itemconfigure(self.bg_arc, outline=ThemeManager.get("ACCENT_DIM"))
            self.canvas.itemconfigure(self.active_arc, outline=ThemeManager.get("ACCENT"))
            self.canvas.itemconfigure(self.text_val, fill=ThemeManager.get("ACCENT"))
            self.canvas.itemconfigure(self.text_unit, fill=ThemeManager.get("TEXT_DIM"))

            # Coordinates
            p = self.padding
            s = self.size

            self.canvas.coords(self.bg_arc, p, p, s - p, s - p)
            self.canvas.coords(self.active_arc, p, p, s - p, s - p)
            self.canvas.coords(self.text_val, s / 2, s / 2)
            self.canvas.coords(self.text_unit, s / 2, s / 2 + 25)

            self.canvas.itemconfigure(self.bg_arc, start=self.arc_start, extent=self.arc_extent)
            self.canvas.itemconfigure(self.active_arc, start=self.arc_start)

            self.update_value(self.current_value)
        except Exception:
            pass

    def update_value(self, value):
        try:
            self.current_value = value

            if self.max_val <= self.min_val: self.max_val = self.min_val + 1

            if value < self.min_val: value = self.min_val
            if value > self.max_val: value = self.max_val

            pct = (value - self.min_val) / (self.max_val - self.min_val)
            angle = -1 * (pct * self.arc_extent)

            color = ThemeManager.get("ACCENT")
            if pct > 0.90:
                color = ThemeManager.get("WARNING")

            self.canvas.itemconfigure(self.active_arc, extent=angle, outline=color)
            self.canvas.itemconfigure(self.text_val, text=str(int(value)), fill=color)
        except Exception:
            pass