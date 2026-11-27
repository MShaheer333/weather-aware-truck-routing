import L from "leaflet";
import { memo, useEffect, useMemo } from "react";
import { CircleMarker, Marker, Pane, Polyline, Popup, Tooltip, useMap } from "react-leaflet";
import type { AnalyzeRequest, Checkpoint, LatLng, RouteResult } from "../../api/types";
import { formatDateTime, formatDuration, formatMiles } from "../../lib/format";
import { RISK_COLOR, RISK_LABEL } from "../../lib/risk";

interface Props {
  routes: RouteResult[];
  selectedId: number;
  request: AnalyzeRequest;
  onSelect: (id: number) => void;
}

const pin = (text: string, color: string) =>
  L.divIcon({
    className: "pin",
    html: `<span style="background:${color}">${text}</span>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });

function FitToRoutes({ routes }: { routes: RouteResult[] }) {
  const map = useMap();
  useEffect(() => {
    const points = routes.flatMap((r) => r.segments.flatMap((s) => s.path));
    if (points.length) map.fitBounds(L.latLngBounds(points), { padding: [40, 40] });
  }, [routes, map]);
  return null;
}

function CheckpointPopup({ route, c }: { route: RouteResult; c: Checkpoint }) {
  return (
    <div className="popup">
      <strong>
        {route.name} · mile {c.mile}
      </strong>{" "}
      · {RISK_LABEL[c.risk.level]}
      <div>ETA {formatDateTime(c.eta)}</div>
      <div>Wind {c.weather.wind_mph.toFixed(0)} mph ({RISK_LABEL[c.risk.wind]})</div>
      <div>Rain {c.weather.rain_in_hr.toFixed(2)} in/hr ({RISK_LABEL[c.risk.rain]})</div>
      <div>Snow {c.weather.snow_in_hr.toFixed(1)} in/hr ({RISK_LABEL[c.risk.snow]})</div>
      {c.risk.load_rule && <div className="popup-rule">⚖ {c.risk.load_rule}</div>}
    </div>
  );
}

function RouteLayersImpl({ routes, selectedId, request, onSelect }: Props) {
  const flattened = useMemo(
    () => new Map<number, LatLng[]>(routes.map((r) => [r.id, r.segments.flatMap((s) => s.path)])),
    [routes],
  );
  const selected = routes.find((r) => r.id === selectedId) ?? routes[0];
  const others = routes.filter((r) => r.id !== selected.id);

  return (
    <>
      <FitToRoutes routes={routes} />

      {/* Alternatives: neutral dashed line + small risk-coloured checkpoints. Click to select. */}
      <Pane name="alt-routes" style={{ zIndex: 410 }}>
        {others.map((r) => (
          <Polyline
            key={r.id}
            positions={flattened.get(r.id)!}
            pathOptions={{ color: "#64748b", weight: 5, opacity: 0.75, dashArray: "2 9", lineCap: "round" }}
            eventHandlers={{ click: () => onSelect(r.id) }}
          >
            <Tooltip sticky>
              <b>{r.name}</b> via {r.summary || "—"}
              <br />
              {formatMiles(r.distance_miles)} · {formatDuration(r.duration_seconds)} · worst: {RISK_LABEL[r.metrics.max_level]}
              <br />
              <i>Click to select</i>
            </Tooltip>
          </Polyline>
        ))}
      </Pane>
      <Pane name="alt-checkpoints" style={{ zIndex: 415 }}>
        {others.flatMap((r) =>
          r.checkpoints.map((c) => (
            <CircleMarker
              key={`${r.id}-${c.mile}`}
              center={[c.lat, c.lon]}
              radius={4}
              pathOptions={{ color: "#fff", weight: 1.5, fillColor: RISK_COLOR[c.risk.level], fillOpacity: 1 }}
            >
              <Popup>
                <CheckpointPopup route={r} c={c} />
              </Popup>
            </CircleMarker>
          )),
        )}
      </Pane>

      <Pane name="selected-route" style={{ zIndex: 420 }}>
        <Polyline positions={flattened.get(selected.id)!} pathOptions={{ color: "#ffffff", weight: 10, opacity: 0.95, lineCap: "round", lineJoin: "round" }} interactive={false} />
        {selected.segments.map((s, i) => (
          <Polyline key={`${selected.id}-${i}`} positions={s.path} pathOptions={{ color: RISK_COLOR[s.level], weight: 6, lineCap: "butt", lineJoin: "round" }} interactive={false} />
        ))}
      </Pane>

      <Pane name="checkpoints" style={{ zIndex: 430 }}>
        {selected.checkpoints.map((c) => (
          <CircleMarker
            key={`${selected.id}-${c.mile}`}
            center={[c.lat, c.lon]}
            radius={6}
            pathOptions={{ color: "#fff", weight: 2, fillColor: RISK_COLOR[c.risk.level], fillOpacity: 1 }}
          >
            <Popup>
              <CheckpointPopup route={selected} c={c} />
            </Popup>
          </CircleMarker>
        ))}
      </Pane>

      <Marker position={[request.origin.lat, request.origin.lon]} icon={pin("A", "#0f4c5c")} zIndexOffset={1000}>
        <Tooltip direction="top" offset={[0, -12]}>{request.origin.label || "Origin"}</Tooltip>
      </Marker>
      <Marker position={[request.destination.lat, request.destination.lon]} icon={pin("B", "#0f4c5c")} zIndexOffset={1000}>
        <Tooltip direction="top" offset={[0, -12]}>{request.destination.label || "Destination"}</Tooltip>
      </Marker>
    </>
  );
}

export const RouteLayers = memo(RouteLayersImpl);
