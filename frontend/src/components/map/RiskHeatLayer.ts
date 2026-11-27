import L from "leaflet";
import type { HeatmapPoint, RiskLevel } from "../../api/types";
import { RISK_COLOR } from "../../lib/risk";

/** Each sample colours the road within this many miles; blobs overlap into a continuous corridor. */
const RADIUS_MILES = 24;
const MIN_RADIUS_PX = 10;
const MAX_RADIUS_PX = 170;
const METERS_PER_MILE = 1609.344;
// Per-level opacity: calm weather stays faint, dangerous weather is hard to miss.
const CENTER_ALPHA = [0.38, 0.5, 0.62, 0.74, 0.85];

const RGB: [number, number, number][] = (Object.values(RISK_COLOR) as string[]).map((hex) => [
  parseInt(hex.slice(1, 3), 16),
  parseInt(hex.slice(3, 5), 16),
  parseInt(hex.slice(5, 7), 16),
]);

export interface HoverInfo {
  point: HeatmapPoint;
  hour: number;
  level: RiskLevel;
}

/**
 * Canvas layer that paints soft, risk-coloured blobs. Unlike a stock heat plugin it does not sum
 * intensities (which would make dense sampling look riskier); the worst level in an area wins by
 * painting low risk first and high risk last. Radius is geographic, so the corridor keeps its true
 * width at every zoom. Changing the forecast hour only repaints one canvas: no React work, no network.
 */
export class RiskHeatLayer extends L.Layer {
  private canvas: HTMLCanvasElement | null = null;
  private points: HeatmapPoint[] = [];
  private hour = 0;
  private frame = 0;

  constructor() {
    super({ pane: "riskHeat" } as L.LayerOptions);
  }

  setData(points: HeatmapPoint[]): void {
    this.points = points;
    this.schedule();
  }

  setHour(hour: number): void {
    if (hour === this.hour) return;
    this.hour = hour;
    this.schedule();
  }

  /** Nearest sample under a container-pixel position, if the pointer is inside its blob. */
  hit(containerPoint: L.Point): HoverInfo | null {
    const map = this._map;
    if (!map) return null;
    let best: HoverInfo | null = null;
    let bestDist = Infinity;
    for (const point of this.points) {
      const p = map.latLngToContainerPoint([point.lat, point.lon]);
      const dist = p.distanceTo(containerPoint);
      if (dist < bestDist && dist <= this.radiusPx(point.lat) * 0.7) {
        bestDist = dist;
        best = { point, hour: this.hour, level: point.levels[this.hour] };
      }
    }
    return best;
  }

  // --- Leaflet lifecycle ----------------------------------------------------------------------
  onAdd(_map: L.Map): this {
    const canvas = L.DomUtil.create("canvas", "risk-heat leaflet-zoom-animated") as HTMLCanvasElement;
    canvas.style.pointerEvents = "none";
    this.canvas = canvas;
    this.getPane()!.appendChild(canvas);
    this.resize();
    this.schedule();
    return this;
  }

  onRemove(_map: L.Map): this {
    cancelAnimationFrame(this.frame);
    this.canvas?.remove();
    this.canvas = null;
    return this;
  }

  /** Leaflet binds/unbinds these (with `this` as context) whenever the layer is added/removed. */
  getEvents(): { [name: string]: L.LeafletEventHandlerFn } {
    return {
      move: this.schedule,
      moveend: this.schedule,
      resize: this.onResize,
      zoomanim: (e) => this.animateZoom(e as L.ZoomAnimEvent),
    };
  }

  private onResize() {
    this.resize();
    this.schedule();
  }

  private resize() {
    if (!this.canvas || !this._map) return;
    const size = this._map.getSize();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = size.x * dpr;
    this.canvas.height = size.y * dpr;
    this.canvas.style.width = `${size.x}px`;
    this.canvas.style.height = `${size.y}px`;
  }

  private animateZoom(e: L.ZoomAnimEvent) {
    if (!this.canvas || !this._map) return;
    /* eslint-disable @typescript-eslint/no-explicit-any */
    const map = this._map as any;
    const scale = map.getZoomScale(e.zoom);
    const offset = map._getCenterOffset(e.center)._multiplyBy(-scale).subtract(map._getMapPanePos());
    L.DomUtil.setTransform(this.canvas, offset, scale);
  }

  private schedule() {
    if (this.frame) return;
    this.frame = requestAnimationFrame(() => {
      this.frame = 0;
      this.draw();
    });
  }

  private radiusPx(lat: number): number {
    const map = this._map!;
    const metersPerPixel = (156543.03392 * Math.cos((lat * Math.PI) / 180)) / 2 ** map.getZoom();
    const px = (RADIUS_MILES * METERS_PER_MILE) / metersPerPixel;
    return Math.min(MAX_RADIUS_PX, Math.max(MIN_RADIUS_PX, px));
  }

  private draw() {
    const map = this._map;
    const canvas = this.canvas;
    if (!map || !canvas) return;
    L.DomUtil.setPosition(canvas, map.containerPointToLayerPoint([0, 0]));
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    const hour = this.hour;
    const visible = new L.Bounds([-MAX_RADIUS_PX, -MAX_RADIUS_PX], [map.getSize().x + MAX_RADIUS_PX, map.getSize().y + MAX_RADIUS_PX]);
    const items: { x: number; y: number; r: number; level: number }[] = [];
    for (const p of this.points) {
      const pt = map.latLngToContainerPoint([p.lat, p.lon]);
      if (!visible.contains(pt)) continue;
      items.push({ x: pt.x, y: pt.y, r: this.radiusPx(p.lat), level: p.levels[hour] ?? 0 });
    }
    items.sort((a, b) => a.level - b.level); // worst risk painted last, so it stays on top

    for (const { x, y, r, level } of items) {
      const [R, G, B] = RGB[level];
      const a = CENTER_ALPHA[level];
      const g = ctx.createRadialGradient(x, y, 0, x, y, r);
      g.addColorStop(0, `rgba(${R},${G},${B},${a})`);
      g.addColorStop(0.55, `rgba(${R},${G},${B},${a * 0.7})`);
      g.addColorStop(1, `rgba(${R},${G},${B},0)`);
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(x, y, r, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}
