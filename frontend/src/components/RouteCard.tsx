import type { RouteResult } from "../api/types";
import { formatDateTime, formatDuration, formatMiles } from "../lib/format";
import { MILES_KEY, RISK_COLOR, RISK_LABEL, RISK_LEVELS } from "../lib/risk";
import { RiskBadge } from "./RiskBadge";

interface Props {
  route: RouteResult;
  selected: boolean;
  isFastest: boolean;
  onSelect: () => void;
}

export function RouteCard({ route, selected, isFastest, onSelect }: Props) {
  const { miles_by_level: miles, avg_risk, max_level } = route.metrics;
  const total = route.distance_miles || 1;

  return (
    <button type="button" className={`route-card ${selected ? "selected" : ""}`} onClick={onSelect} aria-pressed={selected}>
      <div className="route-card-head">
        <strong>{route.name}</strong>
        {route.is_recommended && <span className="tag good">★ Recommended</span>}
        {isFastest && <span className="tag">Fastest</span>}
        <span className="spacer" />
        <RiskBadge level={max_level} label={`Worst: ${RISK_LABEL[max_level]}`} />
      </div>
      {route.summary && <div className="muted">via {route.summary}</div>}

      <div className="stats">
        <div><b>{formatMiles(route.distance_miles)}</b><span>distance</span></div>
        <div><b>{formatDuration(route.duration_seconds)}</b><span>drive time</span></div>
        <div><b>{formatDateTime(route.arrival)}</b><span>arrival</span></div>
      </div>

      <div className="riskbar" role="img" aria-label={`Miles by risk: ${RISK_LEVELS.map((l) => `${RISK_LABEL[l]} ${miles[MILES_KEY[l]]}`).join(", ")}`}>
        {RISK_LEVELS.map((l) => {
          const width = (miles[MILES_KEY[l]] / total) * 100;
          return width > 0 ? <span key={l} style={{ width: `${width}%`, background: RISK_COLOR[l] }} /> : null;
        })}
      </div>
      <div className="risk-miles">
        <span>Severe <b>{miles.severe}</b> mi</span>
        <span>High <b>{miles.high}</b> mi</span>
        {miles.no_travel > 0 && <span className="danger">No Travel <b>{miles.no_travel}</b> mi</span>}
        <span>Avg risk <b>{avg_risk.toFixed(2)}</b>/4</span>
      </div>
    </button>
  );
}
