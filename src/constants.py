import os

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SRC_DIR)
PRO_PACK_DIR = os.path.join(PROJECT_ROOT, "pro_packs")

STANDARD_SENSORS = {
    "RPM": (
        "Engine RPM", "", True, True, 6000,
        "Revolutions Per Minute: How fast the engine crankshaft is spinning."
    ),
    "SPEED": (
        "Vehicle Speed", "km/h", True, True, 160,
        "Current vehicle speed as reported by the ECU."
    ),
    "COOLANT_TEMP": (
        "Coolant Temp", "°C", True, True, 120,
        "Engine Coolant Temperature: If this exceeds 110°C, the engine is overheating."
    ),
    "CONTROL_MODULE_VOLTAGE": (
        "Voltage", "V", True, False, 16,
        "ECU Voltage: Should be ~12.6V (engine off) or ~14.0V (engine running). Low voltage indicates alternator/battery issues."
    ),
    "ENGINE_LOAD": (
        "Engine Load", "%", True, False, 100,
        "Calculated Load Value: How hard the engine is working relative to its maximum capacity."
    ),
    "THROTTLE_POS": (
        "Throttle Pos", "%", False, True, 100,
        "Throttle Position: How far the gas pedal or throttle plate is open."
    ),
    "INTAKE_TEMP": (
        "Intake Air Temp", "°C", False, False, 80,
        "Intake Air Temperature (IAT): The temperature of air entering the engine. Cooler air makes more power."
    ),
    "MAF": (
        "MAF Air Flow", "g/s", False, False, 200,
        "Mass Air Flow: The exact weight of air entering the engine. Used to calculate fuel injection."
    ),
    "FUEL_LEVEL": (
        "Fuel Level", "%", False, False, 100,
        "Fuel Tank Level percentage."
    ),
    "BAROMETRIC_PRESSURE": (
        "Barometric", "kPa", False, False, 200,
        "Atmospheric Pressure: Varies based on weather and altitude."
    ),
    "TIMING_ADVANCE": (
        "Timing Adv", "°", False, False, 60,
        "Ignition Timing Advance: The angle relative to Top Dead Center (TDC) when the spark plug fires. Higher values mean earlier spark."
    ),
    "RUN_TIME": (
        "Run Time", "sec", False, False, 3600,
        "Time elapsed since the engine was started."
    )
}