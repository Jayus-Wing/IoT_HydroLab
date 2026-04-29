import { useEffect, useState } from "react";
import { ref, onValue, update } from "firebase/database";
import { db } from "@/firebase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";

interface SetpointData {
  temperature: number;
  humidity: number;
  grow_light_on: string;
  grow_light_off: string;
}

interface SensorLive {
  temperature: { value: number };
  humidity: { value: number };
}

export default function Setpoints({ module }: { module: string }) {
  const [setpoints, setSetpoints] = useState<SetpointData | null>(null);
  const [sensors, setSensors] = useState<SensorLive | null>(null);

  useEffect(() => {
    const setpointsRef = ref(db, `modules/${module}/setpoints`);
    const unsub = onValue(setpointsRef, (snapshot) => {
      if (snapshot.exists()) {
        setSetpoints(snapshot.val());
      }
    });
    return () => unsub();
  }, [module]);

  useEffect(() => {
    const sensorsRef = ref(db, `modules/${module}/sensors`);
    const unsub = onValue(sensorsRef, (snapshot) => {
      if (snapshot.exists()) {
        setSensors(snapshot.val());
      }
    });
    return () => unsub();
  }, [module]);

  const updateSetpoint = (key: string, value: number | string) => {
    update(ref(db, `modules/${module}/setpoints`), { [key]: value });
  };

  if (!setpoints) {
    return <p className="text-muted-foreground">Loading setpoints...</p>;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Setpoints</h2>

      <div className="grid grid-cols-1 gap-4">
        {/* Temperature setpoint */}
        <Card>
          <CardHeader>
            <CardTitle>Temperature Target</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Current: {sensors?.temperature?.value?.toFixed(1) ?? "--"}°C
              </span>
              <span className="text-sm font-medium">
                Target: {setpoints.temperature}°C
              </span>
            </div>
            <Slider
              value={[setpoints.temperature]}
              min={10}
              max={40}
              step={0.5}
              onValueCommit={(value) => updateSetpoint("temperature", value[0])}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>10°C</span>
              <span>40°C</span>
            </div>
          </CardContent>
        </Card>

        {/* Humidity setpoint */}
        <Card>
          <CardHeader>
            <CardTitle>Humidity Target</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-muted-foreground">
                Current: {sensors?.humidity?.value?.toFixed(1) ?? "--"}%RH
              </span>
              <span className="text-sm font-medium">
                Target: {setpoints.humidity}%RH
              </span>
            </div>
            <Slider
              value={[setpoints.humidity]}
              min={20}
              max={100}
              step={1}
              onValueCommit={(value) => updateSetpoint("humidity", value[0])}
            />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>20%</span>
              <span>100%</span>
            </div>
          </CardContent>
        </Card>

        {/* Grow light schedule */}
        <Card>
          <CardHeader>
            <CardTitle>Grow Light Schedule</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor={`${module}-light-on`}>Turn On</Label>
                <Input
                  id={`${module}-light-on`}
                  type="time"
                  value={setpoints.grow_light_on}
                  onChange={(e) => updateSetpoint("grow_light_on", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor={`${module}-light-off`}>Turn Off</Label>
                <Input
                  id={`${module}-light-off`}
                  type="time"
                  value={setpoints.grow_light_off}
                  onChange={(e) => updateSetpoint("grow_light_off", e.target.value)}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
