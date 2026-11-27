import type { MilesByLevel, RiskLevel } from "../api/types";

export const RISK_LEVELS: RiskLevel[] = [0, 1, 2, 3, 4];

export const RISK_LABEL: Record<RiskLevel, string> = {
  0: "Low",
  1: "Moderate",
  2: "High",
  3: "Severe",
  4: "No Travel",
};

// Sequential green -> red ramp, with a dark purple end so "No Travel" reads as categorically worse.
export const RISK_COLOR: Record<RiskLevel, string> = {
  0: "#2e9e5b",
  1: "#e6c229",
  2: "#f08a24",
  3: "#d93a2f",
  4: "#6b1d8a",
};

export const MILES_KEY: Record<RiskLevel, keyof MilesByLevel> = {
  0: "low",
  1: "moderate",
  2: "high",
  3: "severe",
  4: "no_travel",
};
