import { useEffect, useState } from "react";
import { ref, onValue } from "firebase/database";
import { db } from "@/firebase";
import { queryApi, INFLUX_BUCKET } from "@/influxdb";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface SensorData {
  temperature: { value: number; updated_at: number };
  humidity: { value: number; updated_at: number };
  water_level: { value: number; updated_at: number };
}

interface HistoryPoint {
  time: string;
  temperature?: number;
  humidity?: number;
  water_level?: number;
}

const TIME_RANGES: Record<string, string> = {
  "1h": "-1h",
  "6h": "-6h",
  "24h": "-24h",
};

export default function SensorDisplay({ module }: { module: string }) {
  const [sensors, setSensors] = useState<SensorData | null>(null);
  const [history, setHistory] = useState<HistoryPoint[]>([]);
  const [timeRange, setTimeRange] = useState("1h");

  // Live sensor data from Firebase
  useEffect(() => {
    const sensorsRef = ref(db, `modules/${module}/sensors`);
    const unsub = onValue(sensorsRef, (snapshot) => {
      if (snapshot.exists()) {
        setSensors(snapshot.val());
      }
    });
    return () => unsub();
  }, [module]);

  // Historical data from InfluxDB
  useEffect(() => {
    const fluxQuery = `
      from(bucket: "${INFLUX_BUCKET}")
        |> range(start: ${TIME_RANGES[timeRange]})
        |> filter(fn: (r) => r._measurement == "environment")
        |> filter(fn: (r) => r.module == "${module}")
        |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)
        |> yield(name: "mean")
    `;

    const points: HistoryPoint[] = [];
    const seen = new Map<string, HistoryPoint>();

    queryApi.queryRows(fluxQuery, {
      next(row, tableMeta) {
        const o = tableMeta.toObject(row);
        const timeKey = o._time as string;
        if (!seen.has(timeKey)) {
          seen.set(timeKey, { time: timeKey });
        }
        const point = seen.get(timeKey)!;
        point[o._field as keyof HistoryPoint] = o._value as number;
      },
      error(error) {
        console.error("InfluxDB query error:", error);
      },
      complete() {
        const sorted = Array.from(seen.values()).sort(
          (a, b) => new Date(a.time).getTime() - new Date(b.time).getTime()
        );
        setHistory(sorted);
      },
    });
  }, [timeRange, module]);

  const formatTime = (time: string) => {
    const d = new Date(time);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Sensors</h2>

      {/* Live values */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Temperature</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {sensors?.temperature?.value?.toFixed(1) ?? "--"}
              <span className="text-lg text-muted-foreground ml-1">°C</span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Humidity</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {sensors?.humidity?.value?.toFixed(1) ?? "--"}
              <span className="text-lg text-muted-foreground ml-1">%RH</span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Water Level</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">
              {sensors?.water_level?.value?.toFixed(0) ?? "--"}
              <span className="text-lg text-muted-foreground ml-1">%</span>
            </p>
          </CardContent>
        </Card>
      </div>

      {/* History chart */}
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle>Sensor History</CardTitle>
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">Last 1h</SelectItem>
              <SelectItem value="6h">Last 6h</SelectItem>
              <SelectItem value="24h">Last 24h</SelectItem>
            </SelectContent>
          </Select>
        </CardHeader>
        <CardContent>
          {history.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">
              No data for this time range
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={history}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="time"
                  tickFormatter={formatTime}
                  stroke="hsl(var(--muted-foreground))"
                  fontSize={12}
                />
                <YAxis
                  yAxisId="temp"
                  stroke="hsl(var(--chart-1))"
                  fontSize={12}
                  label={{ value: "°C", position: "insideLeft", offset: 10 }}
                />
                <YAxis
                  yAxisId="percent"
                  orientation="right"
                  stroke="hsl(var(--chart-2))"
                  fontSize={12}
                  label={{ value: "%", position: "insideRight", offset: 10 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "hsl(var(--popover))",
                    border: "1px solid hsl(var(--border))",
                    borderRadius: "8px",
                    color: "hsl(var(--popover-foreground))",
                  }}
                  labelFormatter={formatTime}
                />
                <Legend />
                <Line
                  yAxisId="temp"
                  type="monotone"
                  dataKey="temperature"
                  stroke="hsl(var(--chart-1))"
                  strokeWidth={2}
                  dot={false}
                  name="Temperature (°C)"
                />
                <Line
                  yAxisId="percent"
                  type="monotone"
                  dataKey="humidity"
                  stroke="hsl(var(--chart-2))"
                  strokeWidth={2}
                  dot={false}
                  name="Humidity (%RH)"
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
