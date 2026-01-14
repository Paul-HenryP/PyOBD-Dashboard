from obd_handler import OBDHandler
from gui import DashboardApp

SIMULATION_MODE = True

if __name__ == "__main__":
    handler = OBDHandler(simulation=SIMULATION_MODE)
    app = DashboardApp(handler)
    app.mainloop()