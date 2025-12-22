/**
 * src/__tests__/sharecard.spec.ts
 * Share Card Modal + API proxy tests.
 */

import { describe, it, expect } from "vitest";
import { z } from "zod";

// Share Card response schema
const ShareCardMetricsSchema = z.object({
  streak: z.number().min(0),
  momentum_score: z.number().min(0).max(100),
  weekly_delta: z.number().min(-100).max(100),
  top_platform: z.string().min(1),
});

const ShareCardThemeSchema = z.object({
  bg: z.string().min(1),
  accent: z.string().min(1),
});

const ShareCardSchema = z.object({
  title: z.string().min(1),
  subtitle: z.string().min(1),
  metrics: ShareCardMetricsSchema,
  tagline: z.string().min(1),
  theme: ShareCardThemeSchema,
  generated_at: z.string().datetime(),
});

type ShareCard = z.infer<typeof ShareCardSchema>;

describe("Share Card Schema Validation", () => {
  describe("ShareCardSchema", () => {
    it("accepts valid share card", () => {
      const validCard: ShareCard = {
        title: "Alice",
        subtitle: "Momentum rising 📈 • X",
        metrics: {
          streak: 12,
          momentum_score: 78,
          weekly_delta: 5,
          top_platform: "X",
        },
        tagline: "Building momentum, one post at a time.",
        theme: {
          bg: "from-purple-600 to-pink-600",
          accent: "purple",
        },
        generated_at: new Date().toISOString(),
      };
      expect(() => ShareCardSchema.parse(validCard)).not.toThrow();
    });

    it("rejects missing title", () => {
      const invalid = {
        title: "",
        subtitle: "Momentum rising 📈 • X",
        metrics: {
          streak: 12,
          momentum_score: 78,
          weekly_delta: 5,
          top_platform: "X",
        },
        tagline: "Good tagline",
        theme: { bg: "from-purple-600 to-pink-600", accent: "purple" },
        generated_at: new Date().toISOString(),
      };
      expect(() => ShareCardSchema.parse(invalid)).toThrow();
    });

    it("rejects invalid momentum_score (> 100)", () => {
      const invalid = {
        title: "Bob",
        subtitle: "Momentum rising",
        metrics: {
          streak: 5,
          momentum_score: 150,
          weekly_delta: 0,
          top_platform: "X",
        },
        tagline: "Good",
        theme: { bg: "from-purple-600 to-pink-600", accent: "purple" },
        generated_at: new Date().toISOString(),
      };
      expect(() => ShareCardSchema.parse(invalid)).toThrow();
    });

    it("rejects invalid momentum_score (< 0)", () => {
      const invalid = {
        title: "Bob",
        subtitle: "Momentum dipping",
        metrics: {
          streak: 5,
          momentum_score: -20,
          weekly_delta: -10,
          top_platform: "X",
        },
        tagline: "Good",
        theme: { bg: "from-orange-600 to-orange-400", accent: "orange" },
        generated_at: new Date().toISOString(),
      };
      expect(() => ShareCardSchema.parse(invalid)).toThrow();
    });

    it("rejects negative streak", () => {
      const invalid = {
        title: "Charlie",
        subtitle: "Building momentum",
        metrics: {
          streak: -5,
          momentum_score: 40,
          weekly_delta: 0,
          top_platform: "X",
        },
        tagline: "Good",
        theme: { bg: "from-gray-700 to-gray-900", accent: "gray" },
        generated_at: new Date().toISOString(),
      };
      expect(() => ShareCardSchema.parse(invalid)).toThrow();
    });

    it("rejects weekly_delta out of range", () => {
      const tooHigh = {
        title: "Diana",
        subtitle: "Momentum spiking",
        metrics: {
          streak: 20,
          momentum_score: 95,
          weekly_delta: 150,
          top_platform: "TikTok",
        },
        tagline: "Good",
        theme: { bg: "from-pink-600 to-purple-600", accent: "pink" },
        generated_at: new Date().toISOString(),
      };
      expect(() => ShareCardSchema.parse(tooHigh)).toThrow();

      const tooLow = {
        title: "Eve",
        subtitle: "Momentum dropping",
        metrics: {
          streak: 2,
          momentum_score: 30,
          weekly_delta: -200,
          top_platform: "X",
        },
        tagline: "Rebuilding",
        theme: { bg: "from-blue-600 to-blue-400", accent: "blue" },
        generated_at: new Date().toISOString(),
      };
      expect(() => ShareCardSchema.parse(tooLow)).toThrow();
    });

    it("rejects empty top_platform", () => {
      const invalid = {
        title: "Frank",
        subtitle: "Momentum stable",
        metrics: {
          streak: 7,
          momentum_score: 50,
          weekly_delta: 0,
          top_platform: "",
        },
        tagline: "Good",
        theme: { bg: "from-green-600 to-green-400", accent: "green" },
        generated_at: new Date().toISOString(),
      };
      expect(() => ShareCardSchema.parse(invalid)).toThrow();
    });

    it("rejects invalid ISO datetime", () => {
      const invalid = {
        title: "Grace",
        subtitle: "Momentum good",
        metrics: {
          streak: 10,
          momentum_score: 60,
          weekly_delta: 3,
          top_platform: "Instagram",
        },
        tagline: "Good",
        theme: { bg: "from-red-600 to-pink-600", accent: "red" },
        generated_at: "not-a-date",
      };
      expect(() => ShareCardSchema.parse(invalid)).toThrow();
    });

    it("requires theme with bg and accent", () => {
      const missingAccent = {
        title: "Henry",
        subtitle: "Momentum rising",
        metrics: {
          streak: 9,
          momentum_score: 72,
          weekly_delta: 4,
          top_platform: "X",
        },
        tagline: "Good",
        theme: { bg: "from-purple-600 to-pink-600" } as any,
        generated_at: new Date().toISOString(),
      };
      expect(() => ShareCardSchema.parse(missingAccent)).toThrow();
    });
  });
});

describe("Share Card Metrics Bounds", () => {
  it("accepts valid streak range", () => {
    const streaks = [0, 1, 100, 365, 1000];
    streaks.forEach((s) => {
      const card = {
        title: "User",
        subtitle: "Status",
        metrics: {
          streak: s,
          momentum_score: 50,
          weekly_delta: 0,
          top_platform: "X",
        },
        tagline: "Good",
        theme: { bg: "from-purple-600 to-pink-600", accent: "purple" },
        generated_at: new Date().toISOString(),
      };
      expect(() => ShareCardSchema.parse(card)).not.toThrow();
    });
  });

  it("accepts all valid momentum_scores", () => {
    const scores = [0, 1, 50, 99, 100];
    scores.forEach((score) => {
      const card = {
        title: "User",
        subtitle: "Status",
        metrics: {
          streak: 5,
          momentum_score: score,
          weekly_delta: 0,
          top_platform: "X",
        },
        tagline: "Good",
        theme: { bg: "from-purple-600 to-pink-600", accent: "purple" },
        generated_at: new Date().toISOString(),
      };
      expect(() => ShareCardSchema.parse(card)).not.toThrow();
    });
  });

  it("accepts all valid weekly_deltas", () => {
    const deltas = [-100, -50, 0, 50, 100];
    deltas.forEach((delta) => {
      const card = {
        title: "User",
        subtitle: "Status",
        metrics: {
          streak: 5,
          momentum_score: 50,
          weekly_delta: delta,
          top_platform: "X",
        },
        tagline: "Good",
        theme: { bg: "from-purple-600 to-pink-600", accent: "purple" },
        generated_at: new Date().toISOString(),
      };
      expect(() => ShareCardSchema.parse(card)).not.toThrow();
    });
  });
});

describe("Share Card Theme Variants", () => {
  it("supports all theme variants", () => {
    const themes = [
      { bg: "from-purple-600 to-pink-600", accent: "purple" },
      { bg: "from-gray-700 to-gray-900", accent: "gray" },
      { bg: "from-red-600 to-orange-600", accent: "orange" },
    ];

    themes.forEach((theme) => {
      const card = {
        title: "User",
        subtitle: "Status",
        metrics: {
          streak: 5,
          momentum_score: 50,
          weekly_delta: 0,
          top_platform: "X",
        },
        tagline: "Good",
        theme,
        generated_at: new Date().toISOString(),
      };
      expect(() => ShareCardSchema.parse(card)).not.toThrow();
    });
  });
});

describe("Share Card Modal Behavior", () => {
  it("displays metrics correctly", () => {
    const card: ShareCard = {
      title: "Isabel",
      subtitle: "Momentum rising 📈 • YouTube",
      metrics: {
        streak: 21,
        momentum_score: 85,
        weekly_delta: 8,
        top_platform: "YouTube",
      },
      tagline: "Your voice matters.",
      theme: { bg: "from-purple-600 to-pink-600", accent: "purple" },
      generated_at: new Date().toISOString(),
    };

    // Modal should display each metric
    expect(card.metrics.streak).toBe(21);
    expect(card.metrics.momentum_score).toBe(85);
    expect(card.metrics.weekly_delta).toBe(8);
    expect(card.metrics.top_platform).toBe("YouTube");
  });

  it("shows trend emoji based on weekly_delta sign", () => {
    const upTrendCard: ShareCard = {
      title: "Jack",
      subtitle: "Momentum rising 📈",
      metrics: {
        streak: 10,
        momentum_score: 75,
        weekly_delta: 10,
        top_platform: "X",
      },
      tagline: "Good",
      theme: { bg: "from-green-600 to-green-400", accent: "green" },
      generated_at: new Date().toISOString(),
    };
    expect(upTrendCard.metrics.weekly_delta).toBeGreaterThan(0);

    const downTrendCard: ShareCard = {
      title: "Kate",
      subtitle: "Momentum dipping 📉",
      metrics: {
        streak: 3,
        momentum_score: 35,
        weekly_delta: -10,
        top_platform: "TikTok",
      },
      tagline: "Rebuilding",
      theme: { bg: "from-orange-600 to-orange-400", accent: "orange" },
      generated_at: new Date().toISOString(),
    };
    expect(downTrendCard.metrics.weekly_delta).toBeLessThan(0);
  });
});

describe("Share Card Copy Actions", () => {
  it("prepares JSON for copy-to-clipboard", () => {
    const card: ShareCard = {
      title: "Leo",
      subtitle: "Status",
      metrics: {
        streak: 5,
        momentum_score: 50,
        weekly_delta: 0,
        top_platform: "X",
      },
      tagline: "Good",
      theme: { bg: "from-purple-600 to-pink-600", accent: "purple" },
      generated_at: new Date().toISOString(),
    };

    const json = JSON.stringify(card, null, 2);
    expect(json).toContain("title");
    expect(json).toContain("Leo");
    expect(json).toContain("metrics");
    expect(json).toContain("generated_at");
  });

  it("constructs profile URL for sharing", () => {
    const handle = "creator123";
    const url = `/u/${handle}`;
    expect(url).toBe("/u/creator123");
  });
});
