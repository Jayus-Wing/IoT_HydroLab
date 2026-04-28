import { InfluxDB } from "@influxdata/influxdb-client";

const INFLUX_URL = import.meta.env.VITE_INFLUX_URL;
const INFLUX_TOKEN = import.meta.env.VITE_INFLUX_TOKEN;
const INFLUX_ORG = import.meta.env.VITE_INFLUX_ORG;
export const INFLUX_BUCKET = import.meta.env.VITE_INFLUX_BUCKET;

const client = new InfluxDB({ url: INFLUX_URL, token: INFLUX_TOKEN });
export const queryApi = client.getQueryApi(INFLUX_ORG);
