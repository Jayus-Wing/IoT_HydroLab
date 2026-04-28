#!/usr/bin/env python3
import json
import os
import time
import logging
import threading
from datetime import datetime

from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, db, storage
import paho.mqtt.client as mqtt
from picamera2 import Picamera2

from sensors import read_sht30, get_water_level
from actuators import init_gpio, set_peltier, set_pump, set_mister, set_grow_light, cleanup

load_dotenv()

# --- Configuration ---
FIREBASE_CRED_PATH = os.getenv("FIREBASE_CRED_PATH", "serviceAccountKey.json")
FIREBASE_DB_URL = os.environ["FIREBASE_DB_URL"]
FIREBASE_STORAGE_BUCKET = os.environ["FIREBASE_STORAGE_BUCKET"]

MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))

TEMP_DEADBAND = 1.0       # C
HUMIDITY_DEADBAND = 5.0   # %RH

SNAPSHOT_WIDTH = 640
SNAPSHOT_HEIGHT = 480

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("hydrolab")


# --- Firebase init ---
def init_firebase():
    cred = credentials.Certificate(FIREBASE_CRED_PATH)
    firebase_admin.initialize_app(cred, {
        "databaseURL": FIREBASE_DB_URL,
        "storageBucket": FIREBASE_STORAGE_BUCKET,
    })
    log.info("Firebase initialized")


# --- MQTT init ---
def init_mqtt():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, MQTT_PORT)
    client.loop_start()
    log.info("MQTT connected to %s:%d", MQTT_BROKER, MQTT_PORT)
    return client


# --- Camera init ---
def init_camera():
    cam = Picamera2()
    config = cam.create_still_configuration(main={"size": (SNAPSHOT_WIDTH, SNAPSHOT_HEIGHT)})
    cam.configure(config)
    cam.start()
    time.sleep(1)  # let camera warm up
    log.info("Camera initialized")
    return cam


# --- Shared state (updated by Firebase listeners) ---
_lock = threading.Lock()

_settings = {"publish_interval": 30, "snapshot_interval": 300}
_setpoints = {
    "temperature": 24.0,
    "humidity": 65.0,
    "grow_light_on": "06:00",
    "grow_light_off": "18:00",
}
_actuators = {
    "peltier": {"state": "off", "manual_override": False},
    "pump": {"state": False, "manual_override": False},
    "mister": {"state": False, "manual_override": False},
    "grow_light": {"state": False, "manual_override": False},
}

# Latest sensor readings (written by main loop, read by listeners)
_latest_temp = None
_latest_humidity = None


def _on_settings_change(event):
    global _settings
    data = db.reference("settings").get()
    if data is None:
        return
    with _lock:
        _settings = data
    log.info("Settings updated via listener: %s", data)


def _on_setpoints_change(event):
    global _setpoints
    data = db.reference("setpoints").get()
    if data is None:
        return
    with _lock:
        _setpoints = data
    log.info("Setpoints updated via listener: %s", data)
    _react_to_change()


def _on_actuators_change(event):
    global _actuators
    data = db.reference("actuators").get()
    if data is None:
        return
    with _lock:
        _actuators = data
    log.info("Actuators updated via listener: %s", data)
    _react_to_change()


def _react_to_change():
    """Re-compute and drive GPIOs immediately when setpoints or actuators change."""
    with _lock:
        temp = _latest_temp
        humidity = _latest_humidity
        setpoints = dict(_setpoints)
        current_actuators = dict(_actuators)
    if temp is None or humidity is None:
        return  # no sensor data yet, skip
    actuator_states = compute_actuator_states(temp, humidity, setpoints, current_actuators)
    drive_actuators(actuator_states)
    log.info("GPIOs updated reactively")


def start_listeners():
    db.reference("settings").listen(_on_settings_change)
    db.reference("setpoints").listen(_on_setpoints_change)
    db.reference("actuators").listen(_on_actuators_change)
    log.info("Firebase listeners started")


# --- Firebase writes ---
def write_sensors(temp, humidity, water_level):
    now = int(time.time())
    db.reference("sensors").update({
        "temperature": {"value": round(temp, 2), "updated_at": now},
        "humidity": {"value": round(humidity, 2), "updated_at": now},
        "water_level": {"value": water_level, "updated_at": now},
    })


def write_actuator_state(actuator_states):
    now = int(time.time())
    updates = {}
    for name, state_info in actuator_states.items():
        updates[name] = {
            "state": state_info["state"],
            "manual_override": state_info["manual_override"],
            "updated_at": now,
        }
    db.reference("actuators").update(updates)


# --- MQTT publish ---
def publish_environment(mqtt_client, temp, humidity, water_level):
    payload = json.dumps({
        "temperature": round(temp, 2),
        "humidity": round(humidity, 2),
        "water_level": water_level,
    })
    mqtt_client.publish("hydrolab/environment", payload)


def publish_actuators(mqtt_client, actuator_states):
    payload = json.dumps({
        "peltier": actuator_states["peltier"]["state"],
        "pump": actuator_states["pump"]["state"],
        "mister": actuator_states["mister"]["state"],
        "grow_light": actuator_states["grow_light"]["state"],
    })
    mqtt_client.publish("hydrolab/actuators", payload)


# --- Snapshot ---
def capture_and_upload(camera):
    timestamp = int(time.time())
    local_path = f"/tmp/snapshot_{timestamp}.jpg"
    camera.capture_file(local_path)

    remote_path = f"snapshots/{timestamp}.jpg"
    bucket = storage.bucket()
    blob = bucket.blob(remote_path)
    blob.upload_from_filename(local_path)
    log.info("Snapshot uploaded: %s", remote_path)


# --- Actuator logic ---
def compute_actuator_states(temp, humidity, setpoints, current_actuators):
    states = {}

    # Peltier (temperature control)
    peltier_info = current_actuators.get("peltier", {})
    if peltier_info.get("manual_override", False):
        states["peltier"] = {
            "state": peltier_info.get("state", "off"),
            "manual_override": True,
        }
    else:
        target_temp = setpoints.get("temperature", 24.0)
        if temp < target_temp - TEMP_DEADBAND:
            peltier_state = "heating"
        elif temp > target_temp + TEMP_DEADBAND:
            peltier_state = "cooling"
        else:
            peltier_state = "off"
        states["peltier"] = {"state": peltier_state, "manual_override": False}

    # Mister (humidity control)
    mister_info = current_actuators.get("mister", {})
    if mister_info.get("manual_override", False):
        states["mister"] = {
            "state": mister_info.get("state", False),
            "manual_override": True,
        }
    else:
        target_humidity = setpoints.get("humidity", 65.0)
        if humidity < target_humidity - HUMIDITY_DEADBAND:
            mister_state = True
        elif humidity > target_humidity:
            mister_state = False
        else:
            # In the deadband — keep current state
            mister_state = mister_info.get("state", False)
        states["mister"] = {"state": mister_state, "manual_override": False}

    # Grow light (schedule)
    light_info = current_actuators.get("grow_light", {})
    if light_info.get("manual_override", False):
        states["grow_light"] = {
            "state": light_info.get("state", False),
            "manual_override": True,
        }
    else:
        now_time = datetime.now().strftime("%H:%M")
        on_time = setpoints.get("grow_light_on", "06:00")
        off_time = setpoints.get("grow_light_off", "18:00")
        if on_time <= off_time:
            light_on = on_time <= now_time < off_time
        else:
            # Overnight schedule (e.g., 22:00 - 06:00)
            light_on = now_time >= on_time or now_time < off_time
        states["grow_light"] = {"state": light_on, "manual_override": False}

    # Pump (always manual)
    pump_info = current_actuators.get("pump", {})
    states["pump"] = {
        "state": pump_info.get("state", False),
        "manual_override": pump_info.get("manual_override", False),
    }

    return states


def drive_actuators(actuator_states):
    set_peltier(actuator_states["peltier"]["state"])
    set_pump(actuator_states["pump"]["state"])
    set_mister(actuator_states["mister"]["state"])
    set_grow_light(actuator_states["grow_light"]["state"])


# --- Main ---
def main():
    global _latest_temp, _latest_humidity

    init_firebase()
    mqtt_client = init_mqtt()
    init_gpio()
    camera = init_camera()
    start_listeners()

    last_snapshot_time = 0

    log.info("Entering main loop")

    try:
        while True:
            loop_start = time.time()

            # Read cached config (updated by listeners)
            with _lock:
                publish_interval = _settings.get("publish_interval", 30)
                snapshot_interval = _settings.get("snapshot_interval", 300)
                setpoints = dict(_setpoints)
                current_actuators = dict(_actuators)

            # Read sensors
            try:
                temp, humidity = read_sht30()
            except Exception as e:
                log.error("SHT30 read failed: %s", e)
                time.sleep(publish_interval)
                continue

            water_level = get_water_level()

            # Update latest readings so listeners can use them
            with _lock:
                _latest_temp = temp
                _latest_humidity = humidity

            log.info("T=%.1f°C  RH=%.1f%%  WL=%.0f%%", temp, humidity, water_level)

            # Write sensor values to Firebase
            try:
                write_sensors(temp, humidity, water_level)
            except Exception as e:
                log.error("Firebase sensor write failed: %s", e)

            # Publish to MQTT
            try:
                publish_environment(mqtt_client, temp, humidity, water_level)
            except Exception as e:
                log.error("MQTT environment publish failed: %s", e)

            # Compute and drive actuators
            actuator_states = compute_actuator_states(temp, humidity, setpoints, current_actuators)
            drive_actuators(actuator_states)

            # Write actuator state to Firebase + MQTT
            try:
                write_actuator_state(actuator_states)
                publish_actuators(mqtt_client, actuator_states)
            except Exception as e:
                log.error("Actuator state publish failed: %s", e)

            # Snapshot check
            if time.time() - last_snapshot_time >= snapshot_interval:
                try:
                    capture_and_upload(camera)
                    last_snapshot_time = time.time()
                except Exception as e:
                    log.error("Snapshot failed: %s", e)

            # Sleep until next publish
            elapsed = time.time() - loop_start
            sleep_time = max(0, publish_interval - elapsed)
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        log.info("Shutting down")
    finally:
        cleanup()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        camera.stop()


if __name__ == "__main__":
    main()
