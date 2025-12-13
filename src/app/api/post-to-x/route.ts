// src/app/api/post-to-x/route.ts
import { NextRequest } from "next/server";
import { TwitterApi } from "twitter-api-v2";
import { z } from "zod";
import { currentUser, clerkClient } from "@clerk/nextjs/server";

const schema = z.object({
  content: z.string().min(1),
});

// Simple in-memory rate limiter (per-process; replace with Redis in prod)
const rateMap = new Map<string, { count: number; windowStart: number }>();
const WINDOW_MS = 60 * 1000; // 1 minute
const MAX_POSTS_PER_WINDOW = 5;

function checkRateLimit(userId: string) {
  const now = Date.now();
  const entry = rateMap.get(userId);
  if (!entry) {
    rateMap.set(userId, { count: 1, windowStart: now });
    return true;
  }

  if (now - entry.windowStart > WINDOW_MS) {
    rateMap.set(userId, { count: 1, windowStart: now });
    return true;
  }

  if (entry.count >= MAX_POSTS_PER_WINDOW) return false;
  entry.count += 1;
  return true;
}

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    console.log("[post-to-x] currentUser:", userId);

    if (!userId) {
      return Response.json({ error: "Not authenticated" }, { status: 401 });
    }

    if (!checkRateLimit(userId)) {
      console.warn("[post-to-x] rate limit exceeded for", userId);
      return Response.json({ error: "Rate limit exceeded" }, { status: 429 });
    }

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
        lines.length === 1 ? lines[i] : `${i + 1}/${lines.length} ${lines[i]}`;

      const tweet = await client.v2.tweet(text, {
        ...(previousTweetId && { reply: { in_reply_to_tweet_id: previousTweetId } }),
      });

      previousTweetId = tweet.data.id;
    }

    const url = `https://x.com/${process.env.TWITTER_USERNAME || "i"}/status/${previousTweetId}`;
    console.log("[post-to-x] posted, url:", url, "by user:", userId);
    // Persist post to Clerk publicMetadata (mock storage)
    try {
      const user = await clerkClient.users.getUser(userId);
      const meta = (user.publicMetadata || {}) as any;
      const posts = Array.isArray(meta.posts) ? meta.posts : [];
      const postObj = {
        id: previousTweetId,
        platform: 'X',
        content: content.slice(0, 280),
        time: new Date().toISOString(),
        views: Math.floor(Math.random() * 1000),
        likes: Math.floor(Math.random() * 200),
        ringEarned: 50,
      };
      posts.unshift(postObj);
      const ring = Number(meta.ring || 0) + 50;
      const newMeta = { ...meta, posts, ring };
      await clerkClient.users.updateUser(userId, { publicMetadata: newMeta });
      console.log('[post-to-x] updated user metadata with post and ring for', userId, newMeta);
    } catch (uErr: any) {
      console.error('[post-to-x] failed to update user metadata', uErr);
    }

    return Response.json({ success: true, url });
  } catch (error: any) {
    console.error("[post-to-x] X post failed:", error);
    return Response.json({ error: error.message || "Failed to post to X" }, { status: 500 });
  }
}