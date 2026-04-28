import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import SensorDisplay from "@/components/SensorDisplay";
import ActuatorControls from "@/components/ActuatorControls";
import Setpoints from "@/components/Setpoints";
import Snapshots from "@/components/Snapshots";
import Settings from "@/components/Settings";

function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="max-w-6xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            HydroLab Pro Grow
          </h1>
          <p className="text-muted-foreground">
            Hydroponic greenhouse monitoring and control
          </p>
        </div>

        <Separator />

        <Tabs defaultValue="dashboard" className="space-y-4">
          <TabsList>
            <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
            <TabsTrigger value="controls">Controls</TabsTrigger>
            <TabsTrigger value="snapshots">Snapshots</TabsTrigger>
            <TabsTrigger value="settings">Settings</TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard" className="space-y-6">
            <SensorDisplay />
            <Setpoints />
          </TabsContent>

          <TabsContent value="controls">
            <ActuatorControls />
          </TabsContent>

          <TabsContent value="snapshots">
            <Snapshots />
          </TabsContent>

          <TabsContent value="settings">
            <Settings />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

export default App;
