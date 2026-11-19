import json
import sqlite3
import time
from datetime import datetime, timezone

import requests

# ---------------- Configuration ----------------
ESP8266_IP = "10.218.153.46"  # Replace with your ESP8266 IP
DATA_URL = f"http://{ESP8266_IP}/data"

DATABASE_FILE = "iot_sensor.db"
POLL_INTERVAL = 2

# ---------------- Database setup ----------------
def initialize_database():
    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device TEXT NOT NULL,
                sensor TEXT NOT NULL,
                sequence INTEGER NOT NULL,
                uptime_ms INTEGER NOT NULL,
                mq135_adc INTEGER NOT NULL,
                collected_at TEXT NOT NULL,
                UNIQUE(device, sequence)
            )
        """)
        conn.commit()

# ---------------- Data validation ----------------
def validate_reading(data):
    required = {
        "valid": bool,
        "device": str,
        "sensor": str,
        "sequence": int,
        "uptime_ms": int,
        "mq135_adc": int,
    }

    for field, expected_type in required.items():
        if field not in data:
            raise ValueError(f"Missing field: {field}")

        if type(data[field]) is not expected_type:
            raise ValueError(f"Invalid type for {field}")

    if data["valid"] is not True:
        raise ValueError("Sensor reports invalid data")

    if data["sensor"] != "MQ-135":
        raise ValueError("Unexpected sensor type")

    if not 0 <= data["mq135_adc"] <= 1023:
        raise ValueError("ADC reading is outside 0–1023")

    return data

# ---------------- Save reading ----------------
def save_reading(data):
    collected_at = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(DATABASE_FILE) as conn:
        cursor = conn.execute("""
            INSERT OR IGNORE INTO sensor_readings
            (device, sensor, sequence, uptime_ms,
             mq135_adc, collected_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data["device"],
            data["sensor"],
            data["sequence"],
            data["uptime_ms"],
            data["mq135_adc"],
            collected_at
        ))
        conn.commit()
        return cursor.rowcount == 1

# ---------------- Main collector ----------------
def main():
    initialize_database()
    print("MQ-135 collector started.")
    print(f"Database: {DATABASE_FILE}")
    print(f"Sensor endpoint: {DATA_URL}")
    print("Press Ctrl+C to stop.\n")

    while True:
        try:
            response = requests.get(DATA_URL, timeout=5)
            response.raise_for_status()

            data = validate_reading(response.json())
            inserted = save_reading(data)

            status = "SAVED" if inserted else "DUPLICATE"
            print(
                f"{status} | Sequence={data['sequence']} | "
                f"ADC={data['mq135_adc']} | "
                f"UTC={datetime.now(timezone.utc).isoformat()}"
            )

        except requests.RequestException as error:
            print(f"Network error: {error}")

        except (ValueError, json.JSONDecodeError) as error:
            print(f"Data validation error: {error}")

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCollector stopped. Database has been saved.")