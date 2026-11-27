import "leaflet/dist/leaflet.css";
import { useState } from "react";
import { MapContainer, TileLayer } from "react-leaflet";
import type { AnalyzeResponse } from "../../api/types";
import { RISK_LABEL } from "../../lib/risk";
import { HeatmapControl } from "./HeatmapControl";
import { MapRouteSummary } from "./MapRouteSummary";
import { HeatmapLayer } from "./HeatmapLayer";
import { RouteLayers } from "./RouteLayers";
import type { HoverInfo } from "./RiskHeatLayer";

interface Props {
  result: AnalyzeResponse | null;
  selectedId: number;
  onSelect: (id: number) => void;
  loading: boolean;
}

type Hover = (HoverInfo & { x: number; y: number }) | null;

export function MapView({ result, selectedId, onSelect, loading }: Props) {
  const [heatOn, setHeatOn] = useState(true);
  const [hour, setHour] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [hover, setHover] = useState<Hover>(null);

  return (
    <div className="map-wrap">
      <MapContainer center={[39.5, -98.35]} zoom={4} preferCanvas className="map" zoomControl>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url={import.meta.env.VITE_TILE_URL ?? "https://tile.openstreetmap.org/{z}/{x}/{y}.png"}
          maxZoom={19}
        />
        {result && (
          <>
            {heatOn && <HeatmapLayer points={result.heatmap.points} hour={hour} onHover={setHover} />}
            <RouteLayers routes={result.routes} selectedId={selectedId} request={result.request} onSelect={onSelect} />
          </>
        )}
      </MapContainer>

      {hover && heatOn && (
        <div className="heat-tip" style={{ left: hover.x + 14, top: hover.y + 14 }}>
          <b>{RISK_LABEL[hover.level]}</b> at +{hover.hour} h
          <div>Wind {hover.point.wind[hover.hour].toFixed(0)} mph</div>
          <div>Rain {hover.point.rain[hover.hour].toFixed(2)} in/hr</div>
          <div>Snow {hover.point.snow[hover.hour].toFixed(1)} in/hr</div>
        </div>
      )}

      {result && <MapRouteSummary routes={result.routes} selectedId={selectedId} onSelect={onSelect} />}

      {result && (
        <HeatmapControl
          enabled={heatOn}
          onToggle={setHeatOn}
          hour={hour}
          maxHour={result.heatmap.hours - 1}
          start={result.heatmap.start}
          onHour={setHour}
          playing={playing}
          onPlaying={setPlaying}
        />
      )}

      {loading && (
        <div className="map-loading" role="status">
          <span className="spinner" /> Finding routes and checking the forecast at each checkpoint…
        </div>
      )}

      {!result && !loading && <div className="map-empty">Enter a trip to compare routes by weather risk.</div>}
    </div>
  );
}
