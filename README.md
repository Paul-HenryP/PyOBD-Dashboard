# PyOBD Professional Dashboard

A modern, open-source OBD-II diagnostic tool and dashboard built with Python. Designed to work with **ELM327 USB adapters**, this tool allows you to monitor vehicle sensors in real-time, read/clear check engine lights, and log data for analysis.

## Features

*   **Live Dashboard:** Real-time visualization of RPM, Speed, Coolant Temp, Voltage, and more.
*   **Live Graphing:** Distinct multi-axis graphing to correlate data (e.g., RPM vs. Fuel Pressure).
*   **Automated Analysis:** Built-in logic engine to detect anomalies (e.g., high load at idle, overheating) based on sensor combinations.
*   **Customizable Layout:** Toggle which sensors you want to see on the screen via the Settings tab.
*   **Data Logging:** Automatically save sensor data to CSV files for Excel/Sheets analysis.
*   **Diagnostics:** Read and Clear Diagnostic Trouble Codes (DTCs / Check Engine Light).
*   **Safety Backups:** "Full Backup" feature saves a snapshot of the car's state (Freeze Frame data + Codes) to a JSON file before you wipe them.
*   **Demo Mode:** Built-in simulation to test features without being connected to a car.
*   **Dark Mode UI:** Built with `CustomTkinter` for a modern look.

## Professional Data Packs

The open-source version supports standard OBD-II protocols (Emissions, RPM, Speed, Temps). However, manufacturers often hide specific data (Hybrid Battery Health, DPF Soot Levels, Transmission Temp) behind proprietary codes.

**Pro Packs are available for purchase on our Gumroad store.**

These JSON packs unlock manufacturer-specific sensors for brands like Toyota, VW, Ford, and BMW etc.

👉 [**Visit the PyOBD Data Store**]([https://paulhenryp.gumroad.com/?section=rVBpcW3kPr3ISlhBzRP7Qw%3D%3D#N34-S8KrTX-u9xtW8d-3Zw==])

Do you have a specific car? If you help me verify the PIDs, I will give you the Pro Pack for free.

### How to install a Pro Pack:
1.  Purchase/Download the `.json` file for your car model.
2.  Place the file inside the `pro_packs/` folder in the application directory.
3.  Open the App → **Settings** → **Manage Pro Packs**.
4.  Enable the pack and click "Save & Reload".

## Hardware Requirements

*   **Computer:** Windows, Linux, or macOS.
*   **Adapter:** ELM327 USB Adapter.
    *   *Recommended:* Version with **PIC18F25K80** chip and **FTDI** or **CH340** USB drivers.
    *   *Note:* Avoid generic "blue" KKL/VAG-COM cables; they are not ELM327 compatible.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Paul-HenryP/PyOBD-Dashboard.git
    cd PyOBD-Dashboard
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Connect your Adapter:**
    *   Plug the ELM327 USB into your computer.
    *   Plug the other end into your car's OBD-II port.
    *   Turn the ignition to **ON** (Engine can be off or running).

## Usage

**Running via Python:**
```bash
python src/main.py
```

## Using the Interface:
Select your USB Port from the dropdown (or use "Auto").
Select "Demo Mode" to test the interface without a cable.
Click Connect.
## Disclaimer
This software is provided "as is". Clearing fault codes does not fix the underlying mechanical problem. Always backup your codes using the "Full Backup" feature before clearing them so you have a record for your mechanic.
License
Open Source. Feel free to fork and improve!
### Other info
Used icon:
<a href="https://www.flaticon.com/free-icons/motor" title="motor icons">Motor icons created by Freepik - Flaticon</a>
