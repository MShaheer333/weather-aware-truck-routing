import type { RiskLevel } from "../api/types";
import { RISK_COLOR, RISK_LABEL } from "../lib/risk";

export function RiskBadge({ level, label }: { level: RiskLevel; label?: string }) {
  // Dark text on the yellow band keeps contrast above 4.5:1; white elsewhere.
  const text = level === 1 ? "#1d1d1d" : "#fff";
  return (
    <span className="badge" style={{ background: RISK_COLOR[level], color: text }}>
      {label ?? RISK_LABEL[level]}
    </span>
  );
}
