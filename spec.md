# HydroLab Pro Grow - Frontend Spec

## Overview

**Description:** Frontend for the "HydroLab Pro Grow", a hydroponic greenhouse prototype targeting researchers and technical audiences looking to study and characterize plant species. Designed for controlled experiments at a small scale, not production growing.

**Scope:** This is a school project. The deliverable is a 3-minute in-class demo. The system should appear polished but corner-cutting on internals is acceptable. Features beyond demo scope can be faked or omitted.

**Hosting:** Localhost only. No authentication. Hardcoded credentials are acceptable.

## Architecture

```
[RPi 4 + Sensors/Actuators]
        |
        |--- MQTT ---------> InfluxDB Cloud (time-series sensor data)
        |--- Firebase SDK --> Firebase RTDB  (settings, actuator state, setpoints)
        |--- Firebase SDK --> Firebase Storage (plant snapshots)
        |
[Browser SPA]
        |--- InfluxDB JS client --> InfluxDB Cloud (query sensor history)
        |--- Firebase JS SDK -----> Firebase RTDB  (read/write settings + actuator state)
        |--- Firebase JS SDK -----> Firebase Storage (fetch snapshots)
```

There is no backend server. The frontend communicates directly with cloud services via client SDKs. The RPi device publishes data independently.

## Tech Stack (Recommended)

**Framework: React + Vite**
- Fast scaffolding, hot reload, simple build. Vite is zero-config for a project this size.
- React over Vue/Svelte because the ecosystem for charting and UI component libraries is largest, and most tutorial/help resources exist for it.

**UI: Tailwind CSS + shadcn/ui**
- Tailwind gives you a polished look fast without writing custom CSS.
- shadcn/ui provides copy-paste React components (cards, toggles, sliders, tabs) that look professional out of the box. Not a heavy dependency -- components are copied into your project, not imported from a library.
- This combo will make the demo look clean with minimal effort.

**Charts: Recharts**
- Simple React-native charting library. Easier to integrate than Chart.js in React, and far simpler than embedding Grafana (which would require deploying and configuring a separate service).
- Handles time-series line charts, which is the primary visualization need here.

**Data:**
- `firebase` JS SDK (v9 modular) for RTDB and Storage
- `@influxdata/influxdb-client` for querying sensor data via Flux queries

**Why not Grafana?** Grafana requires its own server, auth config, and dashboard setup. For a 3-minute demo, native charts in the app will look more integrated and are simpler to deploy (just `npm run dev`).

## Functionalities

### 1. Plant Snapshots

- Display periodic snapshots from RPi cameras
- **Storage:** Firebase Storage. The RPi uploads JPEG snapshots on an interval (e.g., every 5-15 minutes) to a known path like `snapshots/{camera_id}/{timestamp}.jpg`. The frontend lists and displays the most recent images.
- Gallery or carousel view of recent snapshots with timestamps

- Single camera, one angle
- Snapshot interval: every 5 minutes

### 2. Sensor Data Display

Live and historical readings from InfluxDB:

| Sensor          | Unit   | Notes                           |
|-----------------|--------|---------------------------------|
| Temperature     | C      | Ambient chamber temperature     |
| Humidity        | %RH    | Relative humidity               |
| Water level     | %      | **Faked for now** (placeholder) |
| Plant health    | TBD    | **Out of scope for prototype**  |

- Time-series charts (Recharts) showing recent history (e.g., last 1h, 6h, 24h)
- Current/live values displayed prominently (big numbers or gauge cards)

### 3. Actuator State Display

Shows the current ON/OFF state of hardware actuators. State is read from Firebase RTDB.

| Actuator            | Type    | Notes                              |
|---------------------|---------|------------------------------------|
| Peltier module      | Tri-state | Heating / cooling / off          |
| Water pump          | Toggle  | On / off                           |
| Ultrasonic mister   | Toggle  | On / off                           |
| Grow light          | Toggle  | On / off                           |

- Each actuator shows its current state and allows manual override (toggle/button)
- When manually toggled, the frontend writes the new state to Firebase RTDB. The RPi listens and actuates accordingly.

### 4. Setpoints (Environment Targets)

User-defined target values for the growing environment. Stored in Firebase RTDB. The RPi reads these and drives actuators to reach them.

| Setpoint              | Unit   | Notes                                 |
|-----------------------|--------|---------------------------------------|
| Chamber temperature   | C      | Target ambient temp                   |
| Humidity              | %RH    | Target relative humidity              |
| Grow light schedule   | time   | On/off times or hours-per-day         |

- Editable inputs (sliders, number inputs, or time pickers)
- Changes write directly to Firebase RTDB
- Display current setpoint alongside current actual reading for comparison

- No water level setpoint -- pump is manual toggle only
- Grow light schedule: simple on/off time window (e.g., 06:00-18:00)

### 5. Settings

- Sensor polling/display refresh interval
- Snapshot capture interval (if the RPi reads this from Firebase)
- Any other configurable parameters

- Datapoint frequency controls the RPi's publish rate to MQTT/InfluxDB. The setting is stored in Firebase RTDB and read by the RPi.

## Cloud Infrastructure

| Service              | Purpose                              | Status       |
|----------------------|--------------------------------------|--------------|
| InfluxDB Cloud       | Time-series sensor data storage      | Not yet set up |
| Firebase RTDB        | Settings, actuator state, setpoints  | Not yet set up |
| Firebase Storage     | Plant snapshot images                | Not yet set up |
| MQTT Broker          | RPi -> InfluxDB ingestion            | Not yet set up |

**MQTT Broker:** Mosquitto (used in class). Telegraf subscribes to Mosquitto topics and writes to InfluxDB.

## Data Model

### Firebase RTDB

```json
{
  "actuators": {
    "peltier": {
      "state": "off",              // "off" | "heating" | "cooling"
      "manual_override": false,
      "updated_at": 1714300000
    },
    "pump": {
      "state": false,
      "manual_override": false,
      "updated_at": 1714300000
    },
    "mister": {
      "state": false,
      "manual_override": false,
      "updated_at": 1714300000
    },
    "grow_light": {
      "state": false,
      "manual_override": false,
      "updated_at": 1714300000
    }
  },
  "setpoints": {
    "temperature": 24.0,           // celsius
    "humidity": 65.0,              // %RH
    "grow_light_on": "06:00",      // HH:MM
    "grow_light_off": "18:00"      // HH:MM
  },
  "sensors": {
    "temperature": {
      "value": 23.5,              // celsius, latest reading
      "updated_at": 1714300000
    },
    "humidity": {
      "value": 62.0,             // %RH, latest reading
      "updated_at": 1714300000
    },
    "water_level": {
      "value": 75.0,             // %, HARDCODED/FAKED
      "updated_at": 1714300000
    }
  },
  "settings": {
    "publish_interval": 30,        // seconds between MQTT publishes
    "snapshot_interval": 300       // seconds between camera snapshots
  }
}
```

**Manual override behavior:**
- When `manual_override` is `false`, the RPi drives the actuator automatically based on setpoints (e.g., peltier heats/cools to reach temperature setpoint, grow light follows schedule).
- When `manual_override` is `true`, the RPi uses the `state` value as-is and ignores setpoints/schedules for that actuator.
- The frontend toggle for an actuator sets both `state` and `manual_override: true`. A separate "return to auto" button sets `manual_override: false`.
- The pump has no automatic mode (no water level setpoint), so its `manual_override` is effectively always `true`. It could be omitted for the pump, but keeping it uniform simplifies the frontend code.

**Water level safety note:**
- Water level is hardcoded in `sensors/water_level`. Since the pump has no setpoint and no automatic mode, the faked value cannot trigger unintended pump activation. The pump only runs when a user explicitly toggles it.

**Sensor data flow:**
- RPi writes latest readings to `sensors/` in Firebase RTDB (for live display)
- RPi publishes the same readings via MQTT -> Telegraf -> InfluxDB (for time-series history)
- Frontend reads live values from Firebase RTDB, queries historical data from InfluxDB

### InfluxDB

**Bucket:** `hydrolab`
**Retention:** 30 days (InfluxDB Cloud free-tier default, sufficient for demo)

**Measurement: `environment`** (sensor readings)

| Field         | Type  | Unit | Notes                |
|---------------|-------|------|----------------------|
| temperature   | float | C    | Ambient chamber temp |
| humidity      | float | %RH  | Relative humidity    |
| water_level   | float | %    | Faked                |

| Tag    | Value      | Notes                                    |
|--------|------------|------------------------------------------|
| device | `"rpi-01"` | Single device, but good practice to tag  |

**Measurement: `actuators`** (actuator state changes)

| Field      | Type   | Unit | Notes                              |
|------------|--------|------|------------------------------------|
| peltier    | string | --   | "off" / "heating" / "cooling"      |
| pump       | bool   | --   | on / off                           |
| mister     | bool   | --   | on / off                           |
| grow_light | bool   | --   | on / off                           |

| Tag    | Value      |
|--------|------------|
| device | `"rpi-01"` |

**MQTT topics:**

| Topic                      | Payload                                                                  |
|----------------------------|--------------------------------------------------------------------------|
| `hydrolab/environment`     | `{"temperature": 23.5, "humidity": 62.0, "water_level": 75.0}`          |
| `hydrolab/actuators`       | `{"peltier": "heating", "pump": false, "mister": false, "grow_light": true}` |

- Both published by the RPi at the `publish_interval` rate from settings
- Snapshot interval is separate (configured via `snapshot_interval` in settings) since images are larger
- Telegraf subscribes to both topics, parses JSON, writes to the corresponding InfluxDB measurements

### Firebase Storage

Path convention: `snapshots/{timestamp}.jpg`
- Single camera, so no camera ID needed
- Timestamp format: ISO 8601 or Unix epoch
- Frontend queries the most recent N images by listing the directory

## Terminology

| Term       | Meaning                                                                 |
|------------|-------------------------------------------------------------------------|
| Setpoint   | A target value for an environmental variable (standard control theory term) |
| Actuator   | A hardware element that manipulates the environment (standard term)     |
| Sensor     | A hardware element that measures the environment                        |

## Out of Scope (for prototype)

- Authentication / authorization
- Safety limits on actuators (e.g., max temp, pump timeout)
- Plant health metric computation
- Water level measurement (will be faked)
- Multi-user support
- Deployment beyond localhost
- Error handling for device disconnection
