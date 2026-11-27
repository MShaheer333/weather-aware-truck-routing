import { useEffect } from "react";
import { addHours, formatDateTime } from "../../lib/format";
import { Legend } from "../Legend";

interface Props {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  hour: number;
  maxHour: number;
  start: string;
  onHour: (hour: number) => void;
  playing: boolean;
  onPlaying: (playing: boolean) => void;
}

const FRAME_MS = 350;

export function HeatmapControl({ enabled, onToggle, hour, maxHour, start, onHour, playing, onPlaying }: Props) {
  useEffect(() => {
    if (!enabled || !playing) return;
    const id = setInterval(() => onHour(hour >= maxHour ? 0 : hour + 1), FRAME_MS);
    return () => clearInterval(id);
  }, [enabled, playing, hour, maxHour, onHour]);

  return (
    <div className="heat-control">
      <div className="heat-head">
        <label className="switch">
          <input type="checkbox" checked={enabled} onChange={(e) => onToggle(e.target.checked)} />
          <span>Weather heatmap</span>
        </label>
        <Legend />
      </div>
      {enabled && (
        <div className="heat-body">
          <button type="button" className="play" onClick={() => onPlaying(!playing)} aria-label={playing ? "Pause forecast animation" : "Play forecast animation"}>
            {playing ? "❚❚" : "▶"}
          </button>
          <input
            type="range"
            min={0}
            max={maxHour}
            step={1}
            value={hour}
            onChange={(e) => {
              onPlaying(false);
              onHour(Number(e.target.value));
            }}
            aria-label="Forecast hour after departure"
            aria-valuetext={`${hour} hours after departure`}
          />
          <div className="heat-time">
            <b>{hour === 0 ? "Departure" : `+${hour} h`}</b>
            <span>{formatDateTime(addHours(start, hour))}</span>
          </div>
        </div>
      )}
    </div>
  );
}
