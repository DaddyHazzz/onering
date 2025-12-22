/**
 * src/__tests__/momentum-graph.spec.ts
 * Momentum SVG path generator tests: determinism, empty handling, bounds.
 */

import { describe, it, expect } from "vitest";
import {
  generateMomentumPath,
  generateDemoMomentumData,
  MomentumDataPoint,
} from "../features/momentum/graph";

describe("Momentum Graph Generator", () => {
  describe("Determinism", () => {
    it("generates same path for same input", () => {
      const data: MomentumDataPoint[] = [
        { date: "2025-12-15", score: 50 },
        { date: "2025-12-16", score: 60 },
        { date: "2025-12-17", score: 70 },
        { date: "2025-12-18", score: 65 },
      ];

      const result1 = generateMomentumPath(data);
      const result2 = generateMomentumPath(data);

      expect(result1.pathD).toBe(result2.pathD);
      expect(result1.trend).toBe(result2.trend);
      expect(result1.trendBanner).toBe(result2.trendBanner);
      expect(result1.points).toEqual(result2.points);
    });

    it("path is deterministic despite array order (sorts internally)", () => {
      const data1: MomentumDataPoint[] = [
        { date: "2025-12-17", score: 70 },
        { date: "2025-12-15", score: 50 },
        { date: "2025-12-16", score: 60 },
      ];

      const data2: MomentumDataPoint[] = [
        { date: "2025-12-15", score: 50 },
        { date: "2025-12-16", score: 60 },
        { date: "2025-12-17", score: 70 },
      ];

      const result1 = generateMomentumPath(data1);
      const result2 = generateMomentumPath(data2);

      // Both should produce same path (sorted internally)
      expect(result1.pathD).toBe(result2.pathD);
    });
  });

  describe("Trend Detection", () => {
    it("detects upward trend when last > first + 5", () => {
      const data: MomentumDataPoint[] = [
        { date: "2025-12-15", score: 30 },
        { date: "2025-12-16", score: 40 },
        { date: "2025-12-17", score: 50 },
        { date: "2025-12-18", score: 65 },
      ];

      const result = generateMomentumPath(data);
      expect(result.trend).toBe("up");
      expect(result.trendBanner).toContain("rising");
    });

    it("detects downward trend when first > last + 5", () => {
      const data: MomentumDataPoint[] = [
        { date: "2025-12-15", score: 80 },
        { date: "2025-12-16", score: 70 },
        { date: "2025-12-17", score: 60 },
        { date: "2025-12-18", score: 50 },
      ];

      const result = generateMomentumPath(data);
      expect(result.trend).toBe("down");
      expect(result.trendBanner).toContain("dipping");
    });

    it("detects flat trend when change <= 5", () => {
      const data: MomentumDataPoint[] = [
        { date: "2025-12-15", score: 60 },
        { date: "2025-12-16", score: 62 },
        { date: "2025-12-17", score: 63 },
        { date: "2025-12-18", score: 61 },
      ];

      const result = generateMomentumPath(data);
      expect(result.trend).toBe("flat");
      expect(result.trendBanner).toContain("stable");
    });
  });

  describe("Bounds & Clamping", () => {
    it("clamps scores to [0, 100]", () => {
      const data: MomentumDataPoint[] = [
        { date: "2025-12-15", score: -50 },
        { date: "2025-12-16", score: 50 },
        { date: "2025-12-17", score: 150 },
      ];

      const result = generateMomentumPath(data);
      result.points.forEach((p) => {
        expect(p.score).toBeGreaterThanOrEqual(0);
        expect(p.score).toBeLessThanOrEqual(100);
      });
    });

    it("min/max reflect clamped range", () => {
      const data: MomentumDataPoint[] = [
        { date: "2025-12-15", score: 20 },
        { date: "2025-12-16", score: 50 },
        { date: "2025-12-17", score: 80 },
      ];

      const result = generateMomentumPath(data);
      expect(result.min).toBe(20);
      expect(result.max).toBe(80);
    });

    it("handles single data point", () => {
      const data: MomentumDataPoint[] = [
        { date: "2025-12-15", score: 65 },
      ];

      const result = generateMomentumPath(data);
      expect(result.points).toHaveLength(1);
      expect(result.pathD).toBeTruthy();
      expect(result.trend).toBe("flat");
    });
  });

  describe("Empty & Graceful Fallback", () => {
    it("handles empty array gracefully", () => {
      const result = generateMomentumPath([]);
      expect(result.pathD).toBe("");
      expect(result.points).toEqual([]);
      expect(result.trend).toBe("flat");
      expect(result.trendBanner).toContain("building");
    });

    it("handles null input gracefully", () => {
      const result = generateMomentumPath(null as any);
      expect(result.pathD).toBe("");
      expect(result.points).toEqual([]);
      expect(result.trend).toBe("flat");
    });

    it("returns supportive hint for empty data", () => {
      const result = generateMomentumPath([]);
      expect(result.trendHint).toContain("Start tracking");
    });
  });

  describe("SVG Path Generation", () => {
    it("generates valid SVG path", () => {
      const data: MomentumDataPoint[] = [
        { date: "2025-12-15", score: 50 },
        { date: "2025-12-16", score: 60 },
        { date: "2025-12-17", score: 70 },
      ];

      const result = generateMomentumPath(data);
      // SVG path should start with M (move) and contain L (line) commands
      expect(result.pathD).toMatch(/^M\s+\d+/);
      expect(result.pathD).toMatch(/L\s+\d+/);
    });

    it("path has correct number of points", () => {
      const data: MomentumDataPoint[] = [
        { date: "2025-12-15", score: 50 },
        { date: "2025-12-16", score: 60 },
        { date: "2025-12-17", score: 70 },
      ];

      const result = generateMomentumPath(data);
      expect(result.points).toHaveLength(data.length);
    });

    it("points have valid x/y coordinates and labels", () => {
      const data: MomentumDataPoint[] = [
        { date: "2025-12-15", score: 50 },
        { date: "2025-12-16", score: 60 },
      ];

      const result = generateMomentumPath(data);
      result.points.forEach((p) => {
        expect(typeof p.x).toBe("number");
        expect(typeof p.y).toBe("number");
        expect(typeof p.label).toBe("string");
        expect(p.label.length).toBeGreaterThan(0);
        expect(typeof p.score).toBe("number");
      });
    });
  });

  describe("Demo Data Generation", () => {
    it("generates 7 days of demo data", () => {
      const data = generateDemoMomentumData();
      expect(data).toHaveLength(7);
    });

    it("demo data is deterministic (today's run always gives same relative scores)", () => {
      const data1 = generateDemoMomentumData();
      const data2 = generateDemoMomentumData();

      // Same day should give same results (deterministic based on day of week)
      expect(data1.map((d) => d.score)).toEqual(data2.map((d) => d.score));
    });

    it("demo data has scores in valid range", () => {
      const data = generateDemoMomentumData();
      data.forEach((d) => {
        expect(d.score).toBeGreaterThanOrEqual(0);
        expect(d.score).toBeLessThanOrEqual(100);
      });
    });

    it("demo data dates are in ascending order", () => {
      const data = generateDemoMomentumData();
      for (let i = 1; i < data.length; i++) {
        expect(data[i].date >= data[i - 1].date).toBe(true);
      }
    });
  });

  describe("Trend Hints", () => {
    it("provides supportive copy for all trends", () => {
      const upData: MomentumDataPoint[] = [
        { date: "2025-12-15", score: 30 },
        { date: "2025-12-18", score: 80 },
      ];

      const downData: MomentumDataPoint[] = [
        { date: "2025-12-15", score: 80 },
        { date: "2025-12-18", score: 30 },
      ];

      const flatData: MomentumDataPoint[] = [
        { date: "2025-12-15", score: 60 },
        { date: "2025-12-18", score: 62 },
      ];

      const upResult = generateMomentumPath(upData);
      const downResult = generateMomentumPath(downData);
      const flatResult = generateMomentumPath(flatData);

      // All should have non-empty, supportive hints
      expect(upResult.trendHint).toBeTruthy();
      expect(downResult.trendHint).toBeTruthy();
      expect(flatResult.trendHint).toBeTruthy();

      // No shame language
      const allHints = [
        upResult.trendHint,
        downResult.trendHint,
        flatResult.trendHint,
      ];
      const shameWords = ["worthless", "fail", "stupid", "broken"];
      allHints.forEach((hint) => {
        shameWords.forEach((word) => {
          expect(hint.toLowerCase()).not.toContain(word);
        });
      });
    });
  });
});
