import { useEffect, useRef } from "react";
import type { LeafletMouseEvent } from "leaflet";
import { useMap } from "react-leaflet";
import type { HeatmapPoint } from "../../api/types";
import { type HoverInfo, RiskHeatLayer } from "./RiskHeatLayer";

interface Props {
  points: HeatmapPoint[];
  hour: number;
  onHover: (info: (HoverInfo & { x: number; y: number }) | null) => void;
}

/** React bridge for RiskHeatLayer: data and hour are pushed imperatively to keep the slider smooth. */
export function HeatmapLayer({ points, hour, onHover }: Props) {
  const map = useMap();
  const layerRef = useRef<RiskHeatLayer | null>(null);
  const hoverRef = useRef(onHover);
  hoverRef.current = onHover;

  useEffect(() => {
    if (!map.getPane("riskHeat")) {
      const pane = map.createPane("riskHeat");
      pane.style.zIndex = "350"; // above tiles, below route lines and markers
      pane.style.pointerEvents = "none";
    }
    const layer = new RiskHeatLayer();
    layer.addTo(map);
    layerRef.current = layer;

    let pending: LeafletMouseEvent | null = null;
    let raf = 0;
    const flush = () => {
      raf = 0;
      if (!pending) return;
      const info = layer.hit(pending.containerPoint);
      hoverRef.current(info ? { ...info, x: pending.containerPoint.x, y: pending.containerPoint.y } : null);
    };
    const onMove = (e: LeafletMouseEvent) => {
      pending = e;
      if (!raf) raf = requestAnimationFrame(flush);
    };
    const onOut = () => {
      pending = null;
      hoverRef.current(null);
    };
    map.on("mousemove", onMove);
    map.on("mouseout", onOut);
    map.on("movestart", onOut);

    return () => {
      map.off("mousemove", onMove);
      map.off("mouseout", onOut);
      map.off("movestart", onOut);
      cancelAnimationFrame(raf);
      layer.remove();
      layerRef.current = null;
    };
  }, [map]);

  useEffect(() => layerRef.current?.setData(points), [points]);
  useEffect(() => layerRef.current?.setHour(hour), [hour]);

  return null;
}
