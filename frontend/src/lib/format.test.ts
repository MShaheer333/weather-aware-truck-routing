import { describe, expect, it } from "vitest";
import { addHours, formatDuration, nextHour, toLocalInputValue } from "./format";

describe("format", () => {
  it("formats durations", () => {
    expect(formatDuration(45 * 60)).toBe("45m");
    expect(formatDuration(15 * 3600 + 39 * 60)).toBe("15h 39m");
    expect(formatDuration(3600)).toBe("1h 00m");
  });

  it("rounds to the next whole hour", () => {
    const d = nextHour(new Date(2026, 0, 5, 9, 41));
    expect([d.getHours(), d.getMinutes()]).toEqual([10, 0]);
  });

  it("builds datetime-local values", () => {
    expect(toLocalInputValue(new Date(2026, 0, 5, 9, 5))).toBe("2026-01-05T09:05");
  });

  it("adds hours to ISO strings", () => {
    expect(addHours("2026-01-01T00:00:00Z", 48).toISOString()).toBe("2026-01-03T00:00:00.000Z");
  });
});
