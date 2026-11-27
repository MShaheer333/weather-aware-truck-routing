export type RiskLevel = 0 | 1 | 2 | 3 | 4; // Low, Moderate, High, Severe, No Travel
export type LatLng = [number, number];

export interface Place {
  label: string;
  lat: number;
  lon: number;
}

export type CheckpointInterval = 10 | 25 | 50;

export interface AnalyzeRequest {
  origin: Place;
  destination: Place;
  departure_time: string; // ISO 8601 with offset
  load_weight_lb: number;
  checkpoint_interval_miles: CheckpointInterval;
}

export interface Weather {
  wind_mph: number;
  rain_in_hr: number;
  snow_in_hr: number;
}

export interface Checkpoint {
  mile: number;
  lat: number;
  lon: number;
  eta: string;
  weather: Weather;
  risk: {
    level: RiskLevel;
    label: string;
    wind: RiskLevel;
    rain: RiskLevel;
    snow: RiskLevel;
    load_rule: string | null;
  };
}

export type MilesByLevel = Record<"low" | "moderate" | "high" | "severe" | "no_travel", number>;

export interface RouteResult {
  id: number;
  name: string;
  summary: string;
  rank: number;
  is_recommended: boolean;
  distance_miles: number;
  duration_seconds: number;
  departure: string;
  arrival: string;
  metrics: {
    miles_by_level: MilesByLevel;
    avg_risk: number;
    max_level: RiskLevel;
    max_level_label: string;
  };
  segments: { level: RiskLevel; path: LatLng[] }[];
  checkpoints: Checkpoint[];
}

export interface HeatmapPoint {
  lat: number;
  lon: number;
  levels: RiskLevel[];
  wind: number[];
  rain: number[];
  snow: number[];
}

export interface AnalyzeResponse {
  request: AnalyzeRequest;
  recommended_route_id: number;
  recommendation: string;
  routes: RouteResult[];
  heatmap: { hours: number; start: string; points: HeatmapPoint[] };
  warnings: string[];
}
