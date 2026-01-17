from obd_handler import OBDHandler
from ui.main_window import DashboardApp

SIMULATION_MODE = False

if __name__ == "__main__":
    handler = OBDHandler(simulation=SIMULATION_MODE)
    app = DashboardApp(handler)
    app.mainloop()