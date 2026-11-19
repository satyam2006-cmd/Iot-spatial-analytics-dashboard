from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


# Use the database located beside this Python file.
DATABASE_FILE = Path(__file__).resolve().parent / "iot_sensor.db"

DEFAULT_ALERT_THRESHOLD = 500


def get_connection():
    if not DATABASE_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Database not found: {DATABASE_FILE}"
        )

    connection = sqlite3.connect(str(DATABASE_FILE))
    connection.row_factory = sqlite3.Row
    return connection


def initialize_settings():
    """Create persistent settings without modifying sensor_readings."""
    connection = sqlite3.connect(str(DATABASE_FILE))

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS api_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            )
        """)

        connection.execute("""
            INSERT OR IGNORE INTO api_settings
                (setting_key, setting_value)
            VALUES ('alert_threshold', ?)
        """, (str(DEFAULT_ALERT_THRESHOLD),))

        connection.commit()
    finally:
        connection.close()


def get_alert_threshold():
    connection = get_connection()

    try:
        row = connection.execute("""
            SELECT setting_value
            FROM api_settings
            WHERE setting_key = 'alert_threshold'
        """).fetchone()

        if row is None:
            return DEFAULT_ALERT_THRESHOLD

        return int(row["setting_value"])
    finally:
        connection.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if DATABASE_FILE.exists():
        initialize_settings()
    yield


app = FastAPI(
    title="Week 1 IoT Sensor API",
    description=(
        "REST API for historical MQ-135 ADC readings "
        "and configurable threshold alerts."
    ),
    version="1.0.0",
    lifespan=lifespan
)


class AlertConfig(BaseModel):
    threshold: int = Field(ge=0, le=1023)


@app.get("/")
def home():
    return {
        "project": "Week 1 IoT and Data Science",
        "device": "ESP8266 NodeMCU",
        "sensor": "MQ-135",
        "database": DATABASE_FILE.name,
        "docs": "/docs",
        "endpoints": [
            "/api/health",
            "/api/readings",
            "/api/readings/latest",
            "/api/alerts/config",
            "/api/alerts",
            "/api/alerts/status"
        ]
    }


@app.get("/api/health")
def health():
    connection = get_connection()

    try:
        count = connection.execute("""
            SELECT COUNT(*) AS total
            FROM sensor_readings
        """).fetchone()["total"]

        return {
            "status": "ok",
            "database": DATABASE_FILE.name,
            "total_readings": count
        }
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail=str(error))
    finally:
        connection.close()


@app.get("/api/readings")
def get_readings(
    limit: int = Query(default=50, ge=1, le=500),
    min_adc: int | None = Query(default=None, ge=0, le=1023),
    max_adc: int | None = Query(default=None, ge=0, le=1023)
):
    if min_adc is not None and max_adc is not None:
        if min_adc > max_adc:
            raise HTTPException(
                status_code=400,
                detail="min_adc cannot be greater than max_adc"
            )

    sql = """
        SELECT id, device, sensor, sequence,
               uptime_ms, mq135_adc, collected_at
        FROM sensor_readings
        WHERE 1 = 1
    """
    params = []

    if min_adc is not None:
        sql += " AND mq135_adc >= ?"
        params.append(min_adc)

    if max_adc is not None:
        sql += " AND mq135_adc <= ?"
        params.append(max_adc)

    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    connection = get_connection()

    try:
        rows = connection.execute(sql, params).fetchall()

        return {
            "count": len(rows),
            "filters": {
                "limit": limit,
                "min_adc": min_adc,
                "max_adc": max_adc
            },
            "readings": [dict(row) for row in rows]
        }
    except sqlite3.Error as error:
        raise HTTPException(status_code=500, detail=str(error))
    finally:
        connection.close()


@app.get("/api/readings/latest")
def get_latest_reading():
    connection = get_connection()

    try:
        row = connection.execute("""
            SELECT id, device, sensor, sequence,
                   uptime_ms, mq135_adc, collected_at
            FROM sensor_readings
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="No sensor readings have been stored yet"
            )

        return {"reading": dict(row)}
    finally:
        connection.close()


@app.get("/api/alerts/config")
def read_alert_config():
    return {
        "threshold": get_alert_threshold(),
        "comparison": "MQ-135 ADC >= threshold",
        "range": {"minimum": 0, "maximum": 1023}
    }


@app.put("/api/alerts/config")
def update_alert_config(config: AlertConfig):
    connection = get_connection()

    try:
        connection.execute("""
            INSERT INTO api_settings (setting_key, setting_value)
            VALUES ('alert_threshold', ?)
            ON CONFLICT(setting_key)
            DO UPDATE SET setting_value = excluded.setting_value
        """, (str(config.threshold),))

        connection.commit()

        return {
            "message": "Alert threshold updated",
            "threshold": config.threshold,
            "alert_condition": f"MQ-135 ADC >= {config.threshold}"
        }
    finally:
        connection.close()


@app.get("/api/alerts")
def get_alerts(
    limit: int = Query(default=50, ge=1, le=500)
):
    threshold = get_alert_threshold()
    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT id, device, sensor, sequence,
                   uptime_ms, mq135_adc, collected_at
            FROM sensor_readings
            WHERE mq135_adc >= ?
            ORDER BY id DESC
            LIMIT ?
        """, (threshold, limit)).fetchall()

        return {
            "threshold": threshold,
            "count": len(rows),
            "alerts": [dict(row) for row in rows],
            "note": (
                "These are stored readings meeting the current threshold. "
                "They are not a calibrated air-safety assessment."
            )
        }
    finally:
        connection.close()


@app.get("/api/alerts/status")
def get_alert_status():
    threshold = get_alert_threshold()
    connection = get_connection()

    try:
        row = connection.execute("""
            SELECT id, device, sensor, sequence,
                   uptime_ms, mq135_adc, collected_at
            FROM sensor_readings
            ORDER BY id DESC
            LIMIT 1
        """).fetchone()

        if row is None:
            return {
                "status": "NO_DATA",
                "threshold": threshold,
                "message": "Waiting for the first stored sensor reading"
            }

        reading = dict(row)
        triggered = reading["mq135_adc"] >= threshold

        return {
            "status": "ALERT" if triggered else "NORMAL",
            "threshold": threshold,
            "latest_adc": reading["mq135_adc"],
            "reading": reading,
            "message": (
                "ADC threshold reached"
                if triggered
                else "Latest ADC reading is below the threshold"
            )
        }
    finally:
        connection.close()