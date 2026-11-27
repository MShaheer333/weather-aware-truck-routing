import { useCallback, useMemo, useRef, useState } from "react";
import { analyzeTrip } from "./api/client";
import type { AnalyzeRequest, AnalyzeResponse } from "./api/types";
import { CheckpointTable } from "./components/CheckpointTable";
import { MapView } from "./components/map/MapView";
import { RouteCard } from "./components/RouteCard";
import { TripForm } from "./components/TripForm";

export default function App() {
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [selectedId, setSelectedId] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);

  const analyze = useCallback(async (req: AnalyzeRequest) => {
    controller.current?.abort(); // a newer search supersedes an in-flight one
    const ctrl = new AbortController();
    controller.current = ctrl;
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeTrip(req, ctrl.signal);
      setResult(data);
      setSelectedId(data.recommended_route_id);
    } catch (e) {
      if (!ctrl.signal.aborted) setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      if (!ctrl.signal.aborted) setLoading(false);
    }
  }, []);

  const fastestId = useMemo(
    () => result?.routes.reduce((a, b) => (b.duration_seconds < a.duration_seconds ? b : a)).id,
    [result],
  );
  const selected = result?.routes.find((r) => r.id === selectedId);
  const ranked = useMemo(() => result?.routes.slice().sort((a, b) => a.rank - b.rank) ?? [], [result]);

  return (
    <div className="app">
      <aside className="panel">
        <header>
          <h1>Weather-Aware Truck Routing</h1>
          <p className="muted">Pick the safest of three routes using forecast weather at your truck’s arrival time.</p>
        </header>

        <TripForm loading={loading} onSubmit={analyze} />

        {error && <div className="alert error" role="alert">{error}</div>}

        {result && (
          <section className="results" aria-live="polite">
            <div className="recommendation">
              <strong>Recommendation</strong>
              <p>{result.recommendation}</p>
            </div>
            {result.warnings.map((w) => (
              <div className="alert warn" key={w}>{w}</div>
            ))}

            <h2>Routes</h2>
            {ranked.map((r) => (
              <RouteCard key={r.id} route={r} selected={r.id === selectedId} isFastest={r.id === fastestId} onSelect={() => setSelectedId(r.id)} />
            ))}

            {selected && <CheckpointTable route={selected} />}
          </section>
        )}
      </aside>

      <main className="map-area">
        <MapView result={result} selectedId={selectedId} onSelect={setSelectedId} loading={loading} />
      </main>
    </div>
  );
}
