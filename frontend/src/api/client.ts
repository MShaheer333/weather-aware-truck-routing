import type { AnalyzeRequest, AnalyzeResponse, Place } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "";

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError("Cannot reach the server. Check your connection and try again.");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(extractMessage(body) ?? `Request failed (${res.status})`);
  }
  return body as T;
}

/** Flatten both our `{error:{message}}` envelope and DRF's field-error objects into one sentence. */
function extractMessage(body: unknown): string | null {
  if (!body || typeof body !== "object") return null;
  const b = body as Record<string, unknown>;
  if (b.error && typeof b.error === "object") return String((b.error as { message?: string }).message ?? "");
  const parts = Object.entries(b).map(([field, msgs]) => `${field.replace(/_/g, " ")}: ${[msgs].flat().join(" ")}`);
  return parts.length ? parts.join("; ") : null;
}

export function geocode(query: string, signal?: AbortSignal): Promise<Place[]> {
  return request<{ results: Place[] }>(`/api/geocode/?q=${encodeURIComponent(query)}`, { signal }).then((r) => r.results);
}

export function analyzeTrip(payload: AnalyzeRequest, signal?: AbortSignal): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>("/api/analyze/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });
}
