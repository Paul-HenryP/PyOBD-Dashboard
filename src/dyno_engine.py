import time

class DynoEngine:
    def __init__(self):
        self.reset()

    def reset(self):
        self.start_time = None
        self.last_time = None
        self.last_speed_ms = 0
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

        accel = dv / dt

        force = (weight_kg * accel) * 1.15

        power_watts = force * speed_ms

        hp = power_watts / 745.7

        kw = power_watts / 1000
        if rpm > 0:
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