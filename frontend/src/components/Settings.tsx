import { useEffect, useState } from "react";
import { ref, onValue, update } from "firebase/database";
import { db } from "@/firebase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";

interface SettingsData {
  publish_interval: number;
  snapshot_interval: number;
}

export default function Settings() {
  const [settings, setSettings] = useState<SettingsData | null>(null);

  useEffect(() => {
    const settingsRef = ref(db, "settings");
    const unsub = onValue(settingsRef, (snapshot) => {
      if (snapshot.exists()) {
        setSettings(snapshot.val());
      }
    });
    return () => unsub();
  }, []);

  const updateSetting = (key: string, value: string) => {
    const num = parseInt(value, 10);
    if (!isNaN(num) && num > 0) {
      update(ref(db, "settings"), { [key]: num });
    }
  };

  if (!settings) {
    return <p className="text-muted-foreground">Loading settings...</p>;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Settings</h2>

      <Card>
        <CardHeader>
          <CardTitle>Data Collection</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="publish-interval">
                Sensor Publish Interval (seconds)
              </Label>
              <Input
                id="publish-interval"
                type="number"
                min={5}
                max={3600}
                value={settings.publish_interval}
                onChange={(e) => updateSetting("publish_interval", e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                How often the RPi publishes sensor data to MQTT/InfluxDB
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="snapshot-interval">
                Snapshot Interval (seconds)
              </Label>
              <Input
                id="snapshot-interval"
                type="number"
                min={60}
                max={3600}
                value={settings.snapshot_interval}
                onChange={(e) => updateSetting("snapshot_interval", e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                How often the RPi captures a camera snapshot
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
