class DiagnosticEngine:
    @staticmethod
    def analyze(data, thresholds):
        issues = []

        def get_val(key):
            return float(data.get(key, 0))

        # Rule: Overheating
        temp = get_val("COOLANT_TEMP")
        try:
            limit_temp = float(thresholds.get("COOLANT_TEMP", 110))
        except ValueError:
            limit_temp = 110.0

        if temp > limit_temp:
            issues.append(f"CRITICAL: Engine Overheating! ({temp}°C > {limit_temp}°C)")

        # Rule: Battery Health
        volts = get_val("CONTROL_MODULE_VOLTAGE")
        rpm = get_val("RPM")

        if rpm > 500:
            if volts < 13.0:
                issues.append("WARNING: Alternator output low (<13V) while engine running.")
            elif volts > 15.0:
                issues.append("WARNING: Voltage Regulator failure (High Voltage > 15V).")
        else:
            if 0 < volts < 11.8:
                issues.append("WARNING: Battery charge is critically low (<11.8V).")

        # Rule: High RPM on Cold Engine
        if rpm > 3500 and temp < 60 and temp > 0:
            issues.append("ADVICE: High RPM detected on cold engine. Risk of wear.")

        # Rule: High Load at Idle
        load = get_val("ENGINE_LOAD")
        speed = get_val("SPEED")
        if speed == 0 and load > 50 and rpm < 1000 and rpm > 0:
            issues.append("WARNING: High Engine Load at idle. Possible stalling or vacuum leak.")

        # Rule: User Thresholds
        for sensor, limit_str in thresholds.items():
            try:
                limit_val = float(limit_str)
                if limit_val > 0:
                    val = get_val(sensor)
                    if val > limit_val:
                        if sensor != "COOLANT_TEMP":
                            issues.append(f"ALERT: {sensor} exceeded limit ({val} > {limit_val})")
            except ValueError:
                continue

        return issues