import type { RouteResult } from "../../api/types";
import { formatDateTime, formatDuration, formatMiles } from "../../lib/format";
import { RISK_COLOR, RISK_LABEL } from "../../lib/risk";

interface Props {
  routes: RouteResult[];
  selectedId: number;
  onSelect: (id: number) => void;
}

/** Compact route summaries drawn on the map itself (distance, time, arrival, worst risk). */
export function MapRouteSummary({ routes, selectedId, onSelect }: Props) {
  return (
    <div className="map-summary" role="radiogroup" aria-label="Routes">
      {routes
        .slice()
        .sort((a, b) => a.rank - b.rank)
        .map((r) => (
          <button
            key={r.id}
            type="button"
            role="radio"
            aria-checked={r.id === selectedId}
            className={r.id === selectedId ? "on" : ""}
            onClick={() => onSelect(r.id)}
          >
            <i style={{ background: RISK_COLOR[r.metrics.max_level] }} title={`Worst risk: ${RISK_LABEL[r.metrics.max_level]}`} />
            <span className="name">
              {r.name}
              {r.is_recommended && " ★"}
            </span>
            <span>
              {formatMiles(r.distance_miles)} · {formatDuration(r.duration_seconds)}
            </span>
            <span className="muted">Arrive {formatDateTime(r.arrival)}</span>
          </button>
        ))}
    </div>
  );
}
