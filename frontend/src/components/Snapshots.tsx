import { useEffect, useState } from "react";
import { ref as storageRef, listAll, getDownloadURL } from "firebase/storage";
import { storage } from "@/firebase";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Snapshot {
  url: string;
  name: string;
}

export default function Snapshots() {
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    const fetchSnapshots = async () => {
      try {
        const listRef = storageRef(storage, "snapshots");
        const result = await listAll(listRef);

        // Sort by name (timestamp) descending so newest is first
        const sorted = result.items.sort((a, b) => b.name.localeCompare(a.name));
        const recent = sorted.slice(0, 12);

        const snaps = await Promise.all(
          recent.map(async (item) => ({
            url: await getDownloadURL(item),
            name: item.name,
          }))
        );

        setSnapshots(snaps);
        setSelectedIndex(0);
      } catch (error) {
        console.error("Error fetching snapshots:", error);
      }
    };

    fetchSnapshots();
    // Refresh every 5 minutes
    const interval = setInterval(fetchSnapshots, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  const formatSnapshotName = (name: string) => {
    // Try to parse timestamp from filename (e.g., "1714300000.jpg" or ISO string)
    const withoutExt = name.replace(/\.[^.]+$/, "");
    const asNumber = Number(withoutExt);
    if (!isNaN(asNumber)) {
      // Unix timestamp (seconds or milliseconds)
      const ts = asNumber > 1e12 ? asNumber : asNumber * 1000;
      return new Date(ts).toLocaleString();
    }
    return withoutExt;
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Plant Snapshots</h2>

      {snapshots.length === 0 ? (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            No snapshots available
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {/* Main image */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-normal text-muted-foreground">
                {formatSnapshotName(snapshots[selectedIndex].name)}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <img
                src={snapshots[selectedIndex].url}
                alt={`Plant snapshot ${snapshots[selectedIndex].name}`}
                className="w-full rounded-lg object-contain max-h-[400px]"
              />
            </CardContent>
          </Card>

          {/* Thumbnail strip */}
          {snapshots.length > 1 && (
            <div className="flex gap-2 overflow-x-auto pb-2">
              {snapshots.map((snap, i) => (
                <button
                  key={snap.name}
                  onClick={() => setSelectedIndex(i)}
                  className={`flex-shrink-0 rounded-md overflow-hidden border-2 transition-colors ${
                    i === selectedIndex
                      ? "border-primary"
                      : "border-transparent hover:border-muted-foreground/30"
                  }`}
                >
                  <img
                    src={snap.url}
                    alt={`Thumbnail ${snap.name}`}
                    className="w-20 h-14 object-cover"
                  />
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
