import type { RouteResult } from "../api/types";
import { formatDateTime } from "../lib/format";
import { RiskBadge } from "./RiskBadge";

export function CheckpointTable({ route }: { route: RouteResult }) {
  return (
    <section className="checkpoints" aria-label={`${route.name} checkpoints`}>
      <h3>{route.name} checkpoints</h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Mile</th>
              <th>ETA</th>
              <th>Wind</th>
              <th>Rain</th>
              <th>Snow</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {route.checkpoints.map((c) => (
              <tr key={c.mile} title={c.risk.load_rule ?? undefined}>
                <td>{c.mile}</td>
                <td>{formatDateTime(c.eta)}</td>
                <td>{c.weather.wind_mph.toFixed(0)} mph</td>
                <td>{c.weather.rain_in_hr.toFixed(2)}</td>
                <td>{c.weather.snow_in_hr.toFixed(1)}</td>
                <td>
                  <RiskBadge level={c.risk.level} />
                  {c.risk.load_rule && <span className="load-flag" title={c.risk.load_rule}> ⚖</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="hint">Rain and snow in inches per hour. ⚖ = escalated by the load-weight rule.</p>
    </section>
  );
}
