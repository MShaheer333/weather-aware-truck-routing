import { useEffect, useId, useState } from "react";
import { geocode } from "../api/client";
import type { Place } from "../api/types";
import { useDebounced } from "../hooks/useDebounced";

interface Props {
  label: string;
  placeholder: string;
  place: Place | null;
  onChange: (place: Place | null) => void;
}

/** Text input with debounced geocoding suggestions. `place` is only set once a suggestion is chosen. */
export function PlaceInput({ label, placeholder, place, onChange }: Props) {
  const id = useId();
  const [text, setText] = useState(place?.label ?? "");
  const [results, setResults] = useState<Place[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(0);
  const debounced = useDebounced(text.trim(), 500);

  useEffect(() => {
    if (debounced.length < 3 || (place && debounced === place.label)) {
      setResults([]);
      return;
    }
    const controller = new AbortController();
    setLoading(true);
    geocode(debounced, controller.signal)
      .then((found) => {
        setResults(found);
        setActive(0);
      })
      .catch(() => {
        if (!controller.signal.aborted) setResults([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [debounced, place]);

  const choose = (p: Place) => {
    setText(p.label);
    setOpen(false);
    onChange(p);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (!open || results.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((i) => (i + 1) % results.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((i) => (i - 1 + results.length) % results.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      choose(results[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div className="field place-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        autoComplete="off"
        placeholder={placeholder}
        value={text}
        role="combobox"
        aria-expanded={open && results.length > 0}
        aria-controls={`${id}-list`}
        aria-invalid={!place && text.length > 0}
        onChange={(e) => {
          setText(e.target.value);
          setOpen(true);
          if (place) onChange(null);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={onKeyDown}
      />
      {place && <span className="field-ok" title="Location found">✓</span>}
      {open && (loading || results.length > 0) && (
        <ul className="suggestions" id={`${id}-list`} role="listbox">
          {loading && results.length === 0 && <li className="muted">Searching…</li>}
          {results.map((r, i) => (
            <li
              key={`${r.lat},${r.lon}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? "active" : ""}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(r);
              }}
              onMouseEnter={() => setActive(i)}
            >
              {r.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
