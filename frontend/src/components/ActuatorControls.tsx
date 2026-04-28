import { useEffect, useState } from "react";
import { ref, onValue, update } from "firebase/database";
import { db } from "@/firebase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface ActuatorState {
  state: boolean | string;
  manual_override: boolean;
  updated_at: number;
}

interface Actuators {
  peltier: ActuatorState;
  pump: ActuatorState;
  mister: ActuatorState;
  grow_light: ActuatorState;
}

export default function ActuatorControls() {
  const [actuators, setActuators] = useState<Actuators | null>(null);

  useEffect(() => {
    const actuatorsRef = ref(db, "actuators");
    const unsub = onValue(actuatorsRef, (snapshot) => {
      if (snapshot.exists()) {
        setActuators(snapshot.val());
      }
    });
    return () => unsub();
  }, []);

  const toggleActuator = (name: string, currentState: boolean) => {
    update(ref(db, `actuators/${name}`), {
      state: !currentState,
      manual_override: true,
      updated_at: Date.now(),
    });
  };

  const setPeltierState = (value: string) => {
    update(ref(db, "actuators/peltier"), {
      state: value,
      manual_override: true,
      updated_at: Date.now(),
    });
  };

  const setManualOverride = (name: string, override: boolean) => {
    update(ref(db, `actuators/${name}`), {
      manual_override: override,
    });
  };

  const formatTimestamp = (ts: number) => {
    if (!ts) return "never";
    return new Date(ts).toLocaleTimeString();
  };

  if (!actuators) {
    return <p className="text-muted-foreground">Loading actuators...</p>;
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Actuators</h2>

      <div className="grid grid-cols-2 gap-4">
        {/* Peltier - tri-state */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Peltier Module
              {actuators.peltier.manual_override ? (
                <Badge variant="outline">Manual</Badge>
              ) : (
                <Badge variant="secondary">Auto</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Select
              value={actuators.peltier.state as string}
              onValueChange={setPeltierState}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="off">Off</SelectItem>
                <SelectItem value="heating">Heating</SelectItem>
                <SelectItem value="cooling">Cooling</SelectItem>
              </SelectContent>
            </Select>
            <div className="flex items-center justify-between">
              <Label htmlFor="peltier-override" className="text-xs text-muted-foreground">
                Manual Override
              </Label>
              <Switch
                id="peltier-override"
                size="sm"
                checked={actuators.peltier.manual_override}
                onCheckedChange={(v) => setManualOverride("peltier", v)}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Last changed: {formatTimestamp(actuators.peltier.updated_at)}
            </p>
          </CardContent>
        </Card>

        {/* Pump */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Water Pump
              <Badge variant="outline">Manual Only</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>{actuators.pump.state ? "Running" : "Off"}</Label>
              <Switch
                checked={actuators.pump.state as boolean}
                onCheckedChange={() =>
                  toggleActuator("pump", actuators.pump.state as boolean)
                }
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Last changed: {formatTimestamp(actuators.pump.updated_at)}
            </p>
          </CardContent>
        </Card>

        {/* Mister */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Ultrasonic Mister
              {actuators.mister.manual_override ? (
                <Badge variant="outline">Manual</Badge>
              ) : (
                <Badge variant="secondary">Auto</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>{actuators.mister.state ? "On" : "Off"}</Label>
              <Switch
                checked={actuators.mister.state as boolean}
                onCheckedChange={() =>
                  toggleActuator("mister", actuators.mister.state as boolean)
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="mister-override" className="text-xs text-muted-foreground">
                Manual Override
              </Label>
              <Switch
                id="mister-override"
                size="sm"
                checked={actuators.mister.manual_override}
                onCheckedChange={(v) => setManualOverride("mister", v)}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Last changed: {formatTimestamp(actuators.mister.updated_at)}
            </p>
          </CardContent>
        </Card>

        {/* Grow Light */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              Grow Light
              {actuators.grow_light.manual_override ? (
                <Badge variant="outline">Manual</Badge>
              ) : (
                <Badge variant="secondary">Auto</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>{actuators.grow_light.state ? "On" : "Off"}</Label>
              <Switch
                checked={actuators.grow_light.state as boolean}
                onCheckedChange={() =>
                  toggleActuator("grow_light", actuators.grow_light.state as boolean)
                }
              />
            </div>
            <div className="flex items-center justify-between">
              <Label htmlFor="light-override" className="text-xs text-muted-foreground">
                Manual Override
              </Label>
              <Switch
                id="light-override"
                size="sm"
                checked={actuators.grow_light.manual_override}
                onCheckedChange={(v) => setManualOverride("grow_light", v)}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Last changed: {formatTimestamp(actuators.grow_light.updated_at)}
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
