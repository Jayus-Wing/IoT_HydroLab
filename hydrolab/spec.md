# HydroLab Pro Grow - RPi Spec

## Overview

Python application running on a Raspberry Pi 4 that reads sensors, drives actuators, publishes data to cloud services, and captures plant snapshots. This is the "backend" — there is no server; the RPi talks directly to Firebase, MQTT, and the camera.

## Hardware

### Sensors

| Sensor | Interface | Address/Bus | Library | Notes |
|--------|-----------|-------------|---------|-------|
| SHT30 (temp + humidity) | I2C bus 1 | 0x44 | smbus2 | Proven working — see `i2c_test.py` |
| Water level | N/A | N/A | N/A | **Faked** — hardcoded to 75% |

### Actuators

All actuators are driven via 3.3V GPIO hi/lo toggling relay modules. No PWM, no throttle — just on/off.

| Actuator | GPIO Pin | Type | Notes |
|----------|----------|------|-------|
| Heat peltier | TBD | Relay (on/off) | Dedicated heating peltier |
| Cool peltier | TBD | Relay (on/off) | Dedicated cooling peltier |
| Water pump | TBD | Relay (on/off) | Manual only — no automatic mode |
| Ultrasonic mister | TBD | Relay (on/off) | |
| Grow light | TBD | Relay (on/off) | Follows schedule or manual override |

**Peltier mapping (one logical actuator):**
The frontend exposes a single tri-state control: `"off"` / `"heating"` / `"cooling"`. The RPi maps this to two relays:
- `"off"` → both relays off
- `"heating"` → heat peltier relay on, cool peltier relay off
- `"cooling"` → cool peltier relay on, heat peltier relay off

**Fans:** Two heatsink fans are always on (hardwired to power). Not software-controlled.

### Camera

- Raspberry Pi Camera Module v1.3
- Captures JPEG snapshots on an interval
- Library: `picamera2` (libcamera-based, standard on recent Raspberry Pi OS)

## Architecture

```
                       +------------------+
                       |   Firebase RTDB  |
                       |  (settings,      |
                       |   setpoints,     |
                       |   actuators,     |
                       |   sensors)       |
                       +--------+---------+
                         ^  read |  ^ write
                         |  settings|  sensor values
                         |       |  actuator state
                         |       v  |
+----------+  I2C    +--+----------+--+   MQTT    +------------+   Telegraf  +-----------+
| SHT30    +-------->|               +----------->| Mosquitto  +------------>| InfluxDB  |
+----------+         |   RPi Python  |            +------------+            +-----------+
                     |   Application |
+----------+  GPIO   |               |   upload   +------------------+
| Relays   |<--------+               +----------->| Firebase Storage |
| (5x)     |         +--+--------+--+             | (snapshots)      |
+----------+             |        |                +------------------+
                         |        |
                   +-----+--+  +-+--------+
                   | Camera  |  | Console  |
                   | v1.3    |  | (logs)   |
                   +---------+  +----------+
```

## Software Dependencies

```
smbus2          # I2C communication with SHT30
RPi.GPIO        # GPIO relay control
picamera2       # Camera capture
paho-mqtt       # MQTT publishing to Mosquitto
firebase-admin  # Firebase RTDB + Storage (Admin SDK, no auth needed)
```

## Code Structure

```
hydrolab/
  i2c_test.py          # Existing SHT30 test script
  spec.md              # This file
  main.py              # Entry point — main loop, orchestration
  sensors.py           # SHT30 reading (based on i2c_test.py), water level fake
  actuators.py         # GPIO relay control, peltier mapping logic
  requirements.txt     # pip dependencies
```

## Main Loop

The application runs a single-threaded loop. Each iteration:

1. **Read settings** from Firebase RTDB (`settings/`, `setpoints/`)
2. **Read sensors** (SHT30 via I2C, water level hardcoded)
3. **Write sensor values** to Firebase RTDB (`sensors/`)
4. **Publish sensor data** to MQTT (`hydrolab/environment`)
5. **Run actuator logic** (compare sensor readings to setpoints, decide actuator states)
6. **Drive actuators** (set GPIO pins based on computed states)
7. **Write actuator state** to Firebase RTDB (`actuators/`)
8. **Publish actuator state** to MQTT (`hydrolab/actuators`)
9. **Sleep** for `publish_interval` seconds

Snapshot capture runs on a separate timer (every `snapshot_interval` seconds). It can be tracked with a simple timestamp comparison — no threads needed.

## Actuator Logic

### Temperature (Peltier)

When `manual_override` is `false`:
- If `sensors/temperature` < `setpoints/temperature` - 1.0 → set peltier to `"heating"`
- If `sensors/temperature` > `setpoints/temperature` + 1.0 → set peltier to `"cooling"`
- Otherwise → set peltier to `"off"` (within deadband)

The 1.0C deadband prevents rapid toggling.

When `manual_override` is `true`:
- Use `actuators/peltier/state` as-is from Firebase

### Humidity (Mister)

When `manual_override` is `false`:
- If `sensors/humidity` < `setpoints/humidity` - 5.0 → mister on
- If `sensors/humidity` > `setpoints/humidity` → mister off

When `manual_override` is `true`:
- Use `actuators/mister/state` as-is from Firebase

### Grow Light

When `manual_override` is `false`:
- If current time is between `setpoints/grow_light_on` and `setpoints/grow_light_off` → light on
- Otherwise → light off

When `manual_override` is `true`:
- Use `actuators/grow_light/state` as-is from Firebase

### Pump

Always manual. Reads `actuators/pump/state` from Firebase and sets GPIO accordingly. No setpoint, no automatic logic.

## Firebase Integration

Uses `firebase-admin` SDK (server-side, no browser auth needed).

**Reads (every loop iteration):**
- `setpoints/` — temperature, humidity, grow light schedule
- `settings/` — publish_interval, snapshot_interval
- `actuators/` — manual_override flags and manual states

**Writes (every loop iteration):**
- `sensors/temperature` — `{value, updated_at}`
- `sensors/humidity` — `{value, updated_at}`
- `sensors/water_level` — `{value: 75.0, updated_at}` (hardcoded)
- `actuators/{name}` — `{state, manual_override, updated_at}`

**Initialization:**
- Requires a Firebase service account JSON key file
- Path configured via environment variable or hardcoded path

## MQTT Integration

Uses `paho-mqtt` to publish to a Mosquitto broker.

**Broker:** localhost (Mosquitto running on the RPi or a local machine)

**Topics and payloads** (JSON, published every `publish_interval`):

`hydrolab/environment`:
```json
{"temperature": 23.5, "humidity": 62.0, "water_level": 75.0}
```

`hydrolab/actuators`:
```json
{"peltier": "heating", "pump": false, "mister": false, "grow_light": true}
```

## Camera / Snapshots

- Capture a JPEG every `snapshot_interval` seconds
- Upload to Firebase Storage at path `snapshots/{unix_timestamp}.jpg`
- Resolution: 640x480 (sufficient for demo, keeps file size small)
- Tracked via a `last_snapshot_time` variable — each loop checks if enough time has elapsed

## Configuration

The RPi reads runtime configuration from Firebase RTDB `settings/`:

| Setting | Path | Default | Unit |
|---------|------|---------|------|
| Publish interval | `settings/publish_interval` | 30 | seconds |
| Snapshot interval | `settings/snapshot_interval` | 300 | seconds |

Additionally, the RPi needs local configuration (not in Firebase):

| Setting | Source | Notes |
|---------|--------|-------|
| Firebase service account key | Local JSON file | Required for firebase-admin |
| MQTT broker host | Hardcoded or env var | Default: `localhost` |
| MQTT broker port | Hardcoded or env var | Default: `1883` |
| GPIO pin assignments | Hardcoded in actuators.py | Updated once hardware is finalized |

## Startup Behavior

1. Initialize Firebase Admin SDK with service account key
2. Initialize MQTT client and connect to broker
3. Initialize GPIO pins as outputs (all relays off initially)
4. Initialize camera
5. Read initial settings and setpoints from Firebase RTDB
6. Enter main loop

## Error Handling

Minimal — this is a prototype:
- If SHT30 read fails, log the error and skip that iteration
- If Firebase/MQTT is unreachable, log and retry next iteration
- If camera capture fails, log and skip
- No crash recovery, watchdog, or systemd service (just run manually for the demo)

## Out of Scope

- Multi-threading / async
- Systemd service / auto-start
- OTA updates
- Safety limits (max temp cutoff, pump timeout)
- Plant segmentation (reach goal — addressed separately once core works)
- PID control (simple bang-bang with deadband is sufficient)
