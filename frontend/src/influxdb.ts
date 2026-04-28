import { InfluxDB } from "@influxdata/influxdb-client";

const INFLUX_URL = "http://localhost:8086";
const INFLUX_TOKEN = "YOUR_INFLUX_TOKEN";
const INFLUX_ORG = "YOUR_ORG";
export const INFLUX_BUCKET = "hydrolab";

const client = new InfluxDB({ url: INFLUX_URL, token: INFLUX_TOKEN });
export const queryApi = client.getQueryApi(INFLUX_ORG);
