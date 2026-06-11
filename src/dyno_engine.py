import time


class DynoEngine:
    def __init__(self):
        self.reset()

    def reset(self):
        self.start_time = None
        self.last_time = None
        self.last_speed_ms = 0
        self.smoothed_accel = 0
        self.peak_hp = 0
        self.peak_torque = 0
        self.data_points = []

    def calculate_step(self, weight_kg, speed_kmh, rpm):
        current_time = time.time()
        speed_ms = speed_kmh / 3.6

        if self.last_time is None:
            self.last_time = current_time
            self.last_speed_ms = speed_ms
            return 0, 0

        dt = current_time - self.last_time
        dv = speed_ms - self.last_speed_ms

        if dt < 0.1:
            return 0, 0

        raw_accel = dv / dt

        # 2. SMOOTHING FILTER (Critical for OBD integer speed steps)
        # 30% new reading, 70% previous reading
        self.smoothed_accel = (self.smoothed_accel * 0.7) + (raw_accel * 0.3)

        # 3. Physics Forces
        # F = ma (Adding 15% for rotational mass / drivetrain inertia)
        force_accel = (weight_kg * self.smoothed_accel) * 1.15

        # Aerodynamic Drag (Approximation for a standard car: CdA ~0.7)
        # F_drag = 0.5 * rho * CdA * v^2
        rho = 1.225  # Air density
        cda = 0.75  # Standard car drag area
        force_aero = 0.5 * rho * cda * (speed_ms ** 2)

        total_force = force_accel + force_aero

        power_watts = total_force * speed_ms

        if power_watts < 0 or raw_accel < 0:
            power_watts = 0

        hp = power_watts / 745.7

        kw = power_watts / 1000
        if rpm > 500:
            torque = (kw * 9549) / rpm
        else:
            torque = 0

        if hp < 0: hp = 0
        if torque < 0: torque = 0

        if hp > self.peak_hp: self.peak_hp = hp
        if torque > self.peak_torque: self.peak_torque = torque

        self.last_time = current_time
        self.last_speed_ms = speed_ms

        return hp, torque