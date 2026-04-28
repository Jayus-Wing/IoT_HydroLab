# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HydroLab Pro Grow — frontend dashboard for a hydroponic greenhouse prototype (school IoT project). The deliverable is a 3-minute in-class demo. Polish matters; internal shortcuts are acceptable.

## Architecture

No backend server. The browser SPA talks directly to cloud services:

- **Firebase RTDB** — live sensor values, actuator state, setpoints, settings (via Firebase JS SDK v9)
- **Firebase Storage** — plant snapshot images (JPEGs from RPi camera)
- **InfluxDB Cloud** — time-series history for sensors and actuator states (via `@influxdata/influxdb-client`)
- **Mosquitto (MQTT)** — RPi publishes to `hydrolab/environment` and `hydrolab/actuators`; Telegraf bridges to InfluxDB

The RPi writes to both Firebase (latest values) and MQTT/InfluxDB (history). The frontend reads live data from Firebase and historical data from InfluxDB.

## Tech Stack

- React + Vite
- Tailwind CSS + shadcn/ui
- Recharts (time-series charts)
- Firebase JS SDK v9 (modular) for RTDB and Storage
- `@influxdata/influxdb-client` for Flux queries

## Commands

Not yet scaffolded. Once initialized with Vite:
- `npm run dev` — start dev server (localhost)
- `npm run build` — production build
- `npm run lint` — lint

## Key Files

- `spec.md` — full project specification including data models, RTDB structure, InfluxDB schema, MQTT topics
- `README.md` — hardware pin assignments and sensor/actuator inventory

## Domain Terminology

- **Setpoint** — target value for an environmental variable (e.g., temperature target)
- **Actuator** — hardware that manipulates the environment (peltier, pump, mister, grow light)
- **Sensor** — hardware that measures the environment (temperature, humidity)

## Development Philosophy

- **Prototype-only mindset.** No unnecessary abstractions, helpers, or utilities. Write direct, inline code. Three similar lines is better than a premature abstraction.
- **No future-proofing.** This will never become a production app. Don't design for extensibility, configurability, or scale.
- **Verbose over clever.** Prefer readable, straightforward code over DRY or elegant patterns.
- **Ask, don't assume.** When encountering ambiguity or blockers, ask the user rather than guessing or powering through.

## Important Constraints

- Localhost only, no authentication, hardcoded credentials are fine
- Water level sensor is faked (hardcoded) — must not trigger pump automation
- Pump is manual-only (no setpoint, no auto mode)
- Peltier is tri-state: heating / cooling / off
- Each actuator has a `manual_override` flag; when true, RPi ignores setpoints for that actuator
- Snapshot interval is separate from sensor publish interval
