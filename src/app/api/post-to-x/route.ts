// src/app/api/post-to-x/route.ts
import { NextRequest } from "next/server";
import { TwitterApi } from "twitter-api-v2";
import { z } from "zod";

const schema = z.object({
  content: z.string().min(1),
});

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { content } = schema.parse(body);

    const client = new TwitterApi({
      appKey: process.env.TWITTER_API_KEY!,
      appSecret: process.env.TWITTER_API_SECRET!,
      accessToken: process.env.TWITTER_ACCESS_TOKEN!,
      accessSecret: process.env.TWITTER_ACCESS_TOKEN_SECRET!,
    });

    const lines = content
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    let previousTweetId: string | null = null;

    for (let i = 0; i < lines.length; i++) {
      const text =
        lines.length === 1
          ? lines[i]
          : `${i + 1}/${lines.length} ${lines[i]}`;

      const tweet = await client.v2.tweet(text, {
        ...(previousTweetId && { reply: { in_reply_to_tweet_id: previousTweetId } }),
      });

      previousTweetId = tweet.data.id;
    }

    return Response.json({ success: true, url: `https://x.com/${process.env.TWITTER_USERNAME || "i"}/status/${previousTweetId}` });
  } catch (error: any) {
    console.error("X post failed:", error);
    return Response.json(
      { error: error.message || "Failed to post to X" },
      { status: 500 }
    );
  }
}