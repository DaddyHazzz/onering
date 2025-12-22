import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { z } from "zod";

const leaderboardSchema = z.object({
  success: z.boolean(),
  data: z.object({
    metric_type: z.enum(["collaboration", "momentum", "consistency"]),
    entries: z.array(
      z.object({
        position: z.number(),
        user_id: z.string(),
        display_name: z.string(),
        avatar_url: z.string().nullable(),
        metric_value: z.number(),
        metric_label: z.string(),
        insight: z.string(),
      })
    ),
    computed_at: z.string().datetime(),
    message: z.string(),
  }),
});

export type Leaderboard = z.infer<typeof leaderboardSchema>;

export async function GET(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    if (!userId) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Parse and validate query parameters
    const searchParams = req.nextUrl.searchParams;
    const metric = searchParams.get("metric") || "collaboration";
    const now = searchParams.get("now");

    // Validate metric type
    const validMetrics = ["collaboration", "momentum", "consistency"];
    if (!validMetrics.includes(metric)) {
      return Response.json(
        { error: "Invalid metric type", validOptions: validMetrics },
        { status: 400 }
      );
    }

    // Proxy to backend
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const leaderboardUrl = new URL(
      "/api/analytics/v1/analytics/leaderboard",
      backendUrl
    );
    leaderboardUrl.searchParams.set("metric", metric);
    if (now) {
      leaderboardUrl.searchParams.set("now", now);
    }

    const response = await fetch(leaderboardUrl.toString(), {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      return Response.json(
        { error: `Backend error: ${response.statusText}` },
        { status: response.status }
      );
    }

    const data = await response.json();

    // Validate response shape
    const validated = leaderboardSchema.parse(data);

    // Safety: Check for forbidden phrases in insights and message
    const forbiddenPhrases = [
      "behind",
      "catch up",
      "falling",
      "ahead of",
      "better than",
      "worse than",
      "last place",
      "you lost",
      "rank shame",
    ];

    const message = validated.data.message.toLowerCase();
    for (const phrase of forbiddenPhrases) {
      if (message.includes(phrase)) {
        return Response.json(
          { error: "Response contains forbidden comparative language" },
          { status: 500 }
        );
      }
    }

    for (const entry of validated.data.entries) {
      const insight = entry.insight.toLowerCase();
      for (const phrase of forbiddenPhrases) {
        if (insight.includes(phrase)) {
          return Response.json(
            { error: "Response contains forbidden comparative language" },
            { status: 500 }
          );
        }
      }
    }

    return Response.json(validated);
  } catch (error: any) {
    console.error("[analytics/leaderboard] error:", error);
    return Response.json(
      { error: error.message || "Failed to fetch leaderboard" },
      { status: 500 }
    );
  }
}
