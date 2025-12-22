/**
 * src/features/momentum/graph.ts
 * Pure, deterministic SVG path generator for momentum graph.
 * Input: array of daily momentum scores
 * Output: SVG path + metadata (min, max, points with labels)
 */

export interface MomentumDataPoint {
  date: string; // YYYY-MM-DD
  score: number; // 0-100
}

export interface GraphOutput {
  pathD: string; // SVG path d attribute
  points: Array<{ x: number; y: number; label: string; score: number }>;
  min: number;
  max: number;
  trend: "up" | "flat" | "down";
  trendBanner: string; // "Momentum rising" / "Momentum stable" / "Momentum dipping"
  trendHint: string; // Supportive action hint
}

/**
 * Generate deterministic SVG path for momentum data.
 * No randomness; same input always produces same output (except with fresh data).
 */
export function generateMomentumPath(data: MomentumDataPoint[]): GraphOutput {
  // Gracefully handle empty input
  if (!data || data.length === 0) {
    return {
      pathD: "",
      points: [],
      min: 0,
      max: 100,
      trend: "flat",
      trendBanner: "Momentum building",
      trendHint: "Start tracking daily actions to build momentum.",
    };
  }

  // Sort by date ascending (ensures determinism)
  const sorted = [...data].sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  // Clamp scores to [0, 100]
  const clamped = sorted.map((d) => ({
    ...d,
    score: Math.max(0, Math.min(100, d.score)),
  }));

  // Find min/max for scaling
  const scores = clamped.map((d) => d.score);
  const min = Math.min(...scores);
  const max = Math.max(...scores);

  // SVG dimensions
  const width = 400;
  const height = 150;
  const padding = 30;
  const graphWidth = width - 2 * padding;
  const graphHeight = height - 2 * padding;

  // X spacing: evenly distribute points
  const xStep = graphWidth / Math.max(clamped.length - 1, 1);

  // Y scaling: invert because SVG y-axis goes down
  const yScale = graphHeight / Math.max(max - min, 1) || 1;

  // Generate points
  const points: GraphOutput["points"] = [];
  let pathCommands: string[] = [];

  clamped.forEach((d, i) => {
    const x = padding + i * xStep;
    const y = padding + graphHeight - (d.score - min) * yScale;

    points.push({
      x,
      y,
      label: formatDate(d.date),
      score: d.score,
    });

    if (i === 0) {
      pathCommands.push(`M ${x} ${y}`);
    } else {
      pathCommands.push(`L ${x} ${y}`);
    }
  });

  const pathD = pathCommands.join(" ");

  // Determine trend: compare first and last score
  const firstScore = clamped[0].score;
  const lastScore = clamped[clamped.length - 1].score;
  const delta = lastScore - firstScore;

  let trend: "up" | "flat" | "down" = "flat";
  let trendBanner = "Momentum stable";
  let trendHint = "Keep showing up daily to maintain your rhythm.";

  if (delta > 5) {
    trend = "up";
    trendBanner = "Momentum rising 📈";
    trendHint = "You're building pace. Keep this energy going.";
  } else if (delta < -5) {
    trend = "down";
    trendBanner = "Momentum dipping 📉";
    trendHint = "Small actions today reset your trajectory. One post is enough.";
  }

  return {
    pathD,
    points,
    min,
    max,
    trend,
    trendBanner,
    trendHint,
  };
}

/**
 * Format date for label: compact "Mon 21" or just "12/21" depending on length.
 */
function formatDate(isoDate: string): string {
  try {
    const date = new Date(isoDate + "T00:00:00Z");
    const month = date.getMonth() + 1;
    const day = date.getDate();
    return `${month}/${day}`;
  } catch {
    return "?";
  }
}

/**
 * Generate last 7 days of dummy data for preview/demo.
 * Deterministic based on current date.
 */
export function generateDemoMomentumData(): MomentumDataPoint[] {
  const data: MomentumDataPoint[] = [];
  const today = new Date();

  for (let i = 6; i >= 0; i--) {
    const date = new Date(today);
    date.setDate(date.getDate() - i);
    const dateStr = date.toISOString().split("T")[0];

    // Deterministic "random" score based on date
    const dayOfWeek = date.getDay();
    const score = 50 + ((dayOfWeek * 13) % 40); // Range 50-89

    data.push({ date: dateStr, score });
  }

  return data;
}
