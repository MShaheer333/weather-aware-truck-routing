import { RISK_COLOR, RISK_LABEL, RISK_LEVELS } from "../lib/risk";

export function Legend() {
  return (
    <ul className="legend" aria-label="Risk levels">
      {RISK_LEVELS.map((l) => (
        <li key={l}>
          <i style={{ background: RISK_COLOR[l] }} />
          {RISK_LABEL[l]}
        </li>
      ))}
    </ul>
  );
}
