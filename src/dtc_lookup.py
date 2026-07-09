import sqlite3
import os


class DTCDatabase:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, "data", "ad_database.sqlite")
        self.conn = None

        if os.path.exists(self.db_path):
            try:
                self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            except Exception as e:
                print(f"Error loading offline DTC database: {e}")

    def lookup(self, code, original_desc):
        if not self.conn:
            return original_desc

        is_unknown = not original_desc or "unknown" in original_desc.lower() or "n/a" in original_desc.lower()

        if not is_unknown:
            return original_desc

        try:
            cursor = self.conn.cursor()

            query = """
                SELECT d.definition, m.name 
                FROM ad_dtc d
                LEFT JOIN ad_dtc_scope_link l ON d.id = l.dtc_id
                LEFT JOIN ad_vehicle v ON l.vehicle_id = v.id
                LEFT JOIN ad_manufacturer m ON v.manufacturer_id = m.id
                WHERE d.code = ?
            """

            clean_code = str(code).strip().upper()
            cursor.execute(query, (clean_code,))
            results = cursor.fetchall()

            if results:
                descriptions = set()
                for definition, manu in results:
                    if not definition:
                        continue

                    if manu and manu.lower() not in ["generic", "none", ""]:
                        descriptions.add(f"{definition} [{manu}]")
                    else:
                        descriptions.add(definition)

                if descriptions:
                    return " OR ".join(list(descriptions))

        except Exception as e:
            print(f"SQL Lookup Error for {code}: {e}")

        return original_desc