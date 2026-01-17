import tkinter as tk


class ToolTip:
    def __init__(self, widget, text, delay=1000):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.tip_window = None
        self.id = None

        self.widget.bind("<Enter>", self.schedule)
        self.widget.bind("<Leave>", self.unschedule)
        self.widget.bind("<ButtonPress>", self.unschedule)

    def schedule(self, event=None):
        self.unschedule()
        self.id = self.widget.after(self.delay, self.show)

    def unschedule(self, event=None):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)
        self.hide()

    def show(self):
        if self.tip_window:
            return

        x = self.widget.winfo_pointerx() + 15
        y = self.widget.winfo_pointery() + 15

        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")
        self.tip_window.attributes("-topmost", True)

        label = tk.Label(
            self.tip_window,
            text=self.text,
            justify='left',
            background="#2b2b2b",
            foreground="#e0e0e0",
            relief='solid',
            borderwidth=1,
            font=("Arial", 10, "normal")
        )
        label.pack(ipadx=5, ipady=2)

    def hide(self):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None