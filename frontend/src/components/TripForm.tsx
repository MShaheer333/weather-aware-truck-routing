import { useMemo, useState } from "react";
import type { AnalyzeRequest, CheckpointInterval, Place } from "../api/types";
import { nextHour, toLocalInputValue } from "../lib/format";
import { PlaceInput } from "./PlaceInput";

interface Props {
  loading: boolean;
  onSubmit: (req: AnalyzeRequest) => void;
}

const INTERVALS: CheckpointInterval[] = [10, 25, 50];
const MAX_LOAD_LB = 150_000;
const MAX_DAYS_AHEAD = 10;

export function TripForm({ loading, onSubmit }: Props) {
  const [origin, setOrigin] = useState<Place | null>(null);
  const [destination, setDestination] = useState<Place | null>(null);
  const [departure, setDeparture] = useState(() => toLocalInputValue(nextHour()));
  const [load, setLoad] = useState("40000");
  const [interval, setInterval] = useState<CheckpointInterval>(25);
  const [error, setError] = useState<string | null>(null);

  const bounds = useMemo(() => {
    const now = new Date();
    return { min: toLocalInputValue(now), max: toLocalInputValue(new Date(now.getTime() + MAX_DAYS_AHEAD * 86_400_000)) };
  }, []);

  const swap = () => {
    setOrigin(destination);
    setDestination(origin);
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const loadLb = Number(load);
    const when = new Date(departure);
    if (!origin || !destination) return setError("Choose an origin and a destination from the suggestions.");
    if (Number.isNaN(when.getTime())) return setError("Enter a valid departure date and time.");
    if (!Number.isFinite(loadLb) || loadLb < 0 || loadLb > MAX_LOAD_LB)
      return setError(`Load weight must be between 0 and ${MAX_LOAD_LB.toLocaleString()} lb.`);
    setError(null);
    onSubmit({
      origin,
      destination,
      departure_time: when.toISOString(),
      load_weight_lb: loadLb,
      checkpoint_interval_miles: interval,
    });
  };

  return (
    <form className="trip-form" onSubmit={submit} noValidate>
      <PlaceInput label="Origin" placeholder="e.g. Chicago, IL" place={origin} onChange={setOrigin} />
      <button type="button" className="swap" onClick={swap} title="Swap origin and destination" aria-label="Swap origin and destination">
        ⇅
      </button>
      <PlaceInput label="Destination" placeholder="e.g. Atlanta, GA" place={destination} onChange={setDestination} />

      <div className="row">
        <div className="field">
          <label htmlFor="departure">Departure</label>
          <input id="departure" type="datetime-local" value={departure} min={bounds.min} max={bounds.max} onChange={(e) => setDeparture(e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="load">Load weight (lb)</label>
          <input id="load" type="number" inputMode="numeric" min={0} max={MAX_LOAD_LB} step={500} value={load} onChange={(e) => setLoad(e.target.value)} />
        </div>
      </div>

      <div className="field">
        <span className="label">Weather checkpoint every</span>
        <div className="segmented" role="radiogroup" aria-label="Checkpoint interval">
          {INTERVALS.map((miles) => (
            <button key={miles} type="button" role="radio" aria-checked={interval === miles} className={interval === miles ? "on" : ""} onClick={() => setInterval(miles)}>
              {miles} mi
            </button>
          ))}
        </div>
      </div>

      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="primary" type="submit" disabled={loading}>
        {loading ? "Analyzing weather along 3 routes…" : "Find safest route"}
      </button>
      <p className="hint">Times use your browser’s time zone. Wind rules: with a load over 30,000 lb, 45+ mph is No Travel; over 40,000 lb, 35+ mph is Severe.</p>
    </form>
  );
}
