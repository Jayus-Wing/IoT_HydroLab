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
import cv2

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

MODULES = ["module_1", "module_2"]

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
    cam = cv2.VideoCapture(0)
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, SNAPSHOT_WIDTH)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, SNAPSHOT_HEIGHT)
    if not cam.isOpened():
        log.error("Failed to open USB camera")
        return None
    log.info("USB camera initialized")
    return cam


# --- Shared state (updated by Firebase listeners) ---
_lock = threading.Lock()

_settings = {"publish_interval": 30, "snapshot_interval": 300}

_module_state = {}
for _m in MODULES:
    _module_state[_m] = {
        "setpoints": {
            "temperature": 24.0,
            "humidity": 65.0,
            "grow_light_on": "06:00",
            "grow_light_off": "18:00",
        },
        "actuators": {
            "peltier": {"state": "off", "manual_override": False},
            "pump": {"state": False, "manual_override": False},
            "mister": {"state": False, "manual_override": False},
            "grow_light": {"state": False, "manual_override": False},
        },
        "latest_temp": None,
        "latest_humidity": None,
    }


def _on_settings_change(event):
    global _settings
    data = db.reference("settings").get()
    if data is None:
        return
    with _lock:
        _settings = data
    log.info("Settings updated via listener")


def _make_module_setpoints_listener(module):
    def _on_change(event):
        data = db.reference(f"modules/{module}/setpoints").get()
        if data is None:
            return
        with _lock:
            _module_state[module]["setpoints"] = data
        log.info("%s setpoints updated via listener", module)
        _react_to_change(module)
    return _on_change


def _make_module_actuators_listener(module):
    def _on_change(event):
        data = db.reference(f"modules/{module}/actuators").get()
        if data is None:
            return
        with _lock:
            _module_state[module]["actuators"] = data
        log.info("%s actuators updated via listener", module)
        _react_to_change(module)
    return _on_change


def _react_to_change(module):
    with _lock:
        temp = _module_state[module]["latest_temp"]
        humidity = _module_state[module]["latest_humidity"]
        setpoints = dict(_module_state[module]["setpoints"])
        current_actuators = dict(_module_state[module]["actuators"])
    if temp is None or humidity is None:
        return
    actuator_states = compute_actuator_states(temp, humidity, setpoints, current_actuators)
    drive_actuators(module, actuator_states)
    log.info("%s GPIOs updated reactively", module)


def start_listeners():
    db.reference("settings").listen(_on_settings_change)
    for module in MODULES:
        db.reference(f"modules/{module}/setpoints").listen(_make_module_setpoints_listener(module))
        db.reference(f"modules/{module}/actuators").listen(_make_module_actuators_listener(module))
    log.info("Firebase listeners started")


# --- Firebase writes ---
def write_sensors(module, temp, humidity, water_level):
    now = int(time.time())
    db.reference(f"modules/{module}/sensors").update({
        "temperature": {"value": round(temp, 2), "updated_at": now},
        "humidity": {"value": round(humidity, 2), "updated_at": now},
        "water_level": {"value": water_level, "updated_at": now},
    })


def write_actuator_state(module, actuator_states):
    now = int(time.time())
    updates = {}
    for name, state_info in actuator_states.items():
        updates[name] = {
            "state": state_info["state"],
            "manual_override": state_info["manual_override"],
            "updated_at": now,
        }
    db.reference(f"modules/{module}/actuators").update(updates)


# --- MQTT publish ---
def publish_environment(mqtt_client, module, temp, humidity, water_level):
    payload = json.dumps({
        "temperature": round(temp, 2),
        "humidity": round(humidity, 2),
        "water_level": water_level,
    })
    mqtt_client.publish(f"hydrolab/{module}/environment", payload)


def publish_actuators(mqtt_client, module, actuator_states):
    payload = json.dumps({
        "peltier": actuator_states["peltier"]["state"],
        "pump": actuator_states["pump"]["state"],
        "mister": actuator_states["mister"]["state"],
        "grow_light": actuator_states["grow_light"]["state"],
    })
    mqtt_client.publish(f"hydrolab/{module}/actuators", payload)


# --- Snapshot ---
def capture_and_upload(camera):
    if camera is None:
        return
    ret, frame = camera.read()
    if not ret:
        log.error("Failed to capture frame from USB camera")
        return
    timestamp = int(time.time())
    local_path = f"/tmp/snapshot_{timestamp}.jpg"
    cv2.imwrite(local_path, frame)

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
            light_on = now_time >= on_time or now_time < off_time
        states["grow_light"] = {"state": light_on, "manual_override": False}

    # Pump (always manual)
    pump_info = current_actuators.get("pump", {})
    states["pump"] = {
        "state": pump_info.get("state", False),
        "manual_override": pump_info.get("manual_override", False),
    }

    return states


def drive_actuators(module, actuator_states):
    set_peltier(module, actuator_states["peltier"]["state"])
    set_pump(module, actuator_states["pump"]["state"])
    set_mister(module, actuator_states["mister"]["state"])
    set_grow_light(module, actuator_states["grow_light"]["state"])


# --- Main ---
def main():
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

            with _lock:
                publish_interval = _settings.get("publish_interval", 30)
                snapshot_interval = _settings.get("snapshot_interval", 300)

            for module in MODULES:
                with _lock:
                    setpoints = dict(_module_state[module]["setpoints"])
                    current_actuators = dict(_module_state[module]["actuators"])

                # Read sensors
                try:
                    temp, humidity = read_sht30(module)
                except Exception as e:
                    log.error("%s SHT30 read failed: %s", module, e)
                    continue

                water_level = get_water_level()

                with _lock:
                    _module_state[module]["latest_temp"] = temp
                    _module_state[module]["latest_humidity"] = humidity

                log.info("%s  T=%.1f°C  RH=%.1f%%  WL=%.0f%%", module, temp, humidity, water_level)

                # Write sensor values to Firebase
                try:
                    write_sensors(module, temp, humidity, water_level)
                except Exception as e:
                    log.error("%s Firebase sensor write failed: %s", module, e)

                # Publish to MQTT
                try:
                    publish_environment(mqtt_client, module, temp, humidity, water_level)
                except Exception as e:
                    log.error("%s MQTT environment publish failed: %s", module, e)

                # Compute and drive actuators
                actuator_states = compute_actuator_states(temp, humidity, setpoints, current_actuators)
                drive_actuators(module, actuator_states)

                # Write actuator state to Firebase + MQTT
                try:
                    write_actuator_state(module, actuator_states)
                    publish_actuators(mqtt_client, module, actuator_states)
                except Exception as e:
                    log.error("%s actuator state publish failed: %s", module, e)

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
        if camera is not None:
            camera.release()


if __name__ == "__main__":
    main()
