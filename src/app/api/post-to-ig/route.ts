// src/app/api/post-to-ig/route.ts
import { NextRequest } from "next/server";
import { z } from "zod";
import { currentUser, clerkClient } from "@clerk/nextjs/server";
import Redis from "ioredis";
import { prisma } from "@/lib/db";
import { applyLedgerEarn, getTokenIssuanceMode } from "@/lib/ring-ledger";

const schema = z.object({
  content: z.string().min(1),
});

const success = (payload: Record<string, unknown>, status = 200) =>
  Response.json({ success: true, ...payload }, { status });

const failure = (error: string, status = 500, extra: Record<string, unknown> = {}) =>
  Response.json({ success: false, error, ...extra }, { status });

let _redis: Redis | null = null;
function getRedis(): Redis {
  if (_redis) return _redis;
  const client = new Redis({
    host: process.env.REDIS_HOST || "localhost",
    port: parseInt(process.env.REDIS_PORT || "6379"),
    db: 0,
    retryStrategy: (times) => Math.min(times * 50, 2000),
    lazyConnect: true,
  });
  client.on("error", (err) => {
    console.error("[post-to-ig] Redis error:", err);
  });
  _redis = client;
  return client;
}

// Rate limiting: max 3 posts per day per user
const RATE_LIMIT_WINDOW_SECONDS = 86400; // 24 hours
const RATE_LIMIT_MAX_POSTS = 3;

async function checkRateLimit(userId: string): Promise<{ allowed: boolean; remaining: number }> {
  const key = `rate:post:ig:${userId}`;
  const now = Date.now();
  const windowStart = now - RATE_LIMIT_WINDOW_SECONDS * 1000;

  try {
    const redis = getRedis();
    await redis.zremrangebyscore(key, 0, windowStart);
    const count = await redis.zcard(key);

    if (count >= RATE_LIMIT_MAX_POSTS) {
      console.warn(`[post-to-ig] rate limit exceeded for ${userId}: ${count}/${RATE_LIMIT_MAX_POSTS}`);
      return { allowed: false, remaining: 0 };
    }

    const requestId = `${now}-${Math.random().toString(36).substring(7)}`;
    const redis2 = getRedis();
    await redis2.zadd(key, now, requestId);
    await redis2.expire(key, RATE_LIMIT_WINDOW_SECONDS);

    const remaining = RATE_LIMIT_MAX_POSTS - count - 1;
    console.log(`[post-to-ig] rate limit check passed: ${count + 1}/${RATE_LIMIT_MAX_POSTS}`);
    return { allowed: true, remaining };
  } catch (redisErr: any) {
    console.error("[post-to-ig] Redis error:", redisErr);
    return { allowed: true, remaining: -1 };
  }
}

async function postToInstagram(
  content: string,
  userId: string
): Promise<{ success: boolean; id?: string; error?: string }> {
  try {
    const igAccessToken = process.env.INSTAGRAM_ACCESS_TOKEN;
    const igBusinessAccountId = process.env.INSTAGRAM_BUSINESS_ACCOUNT_ID;

    if (!igAccessToken || !igBusinessAccountId) {
      console.warn("[post-to-ig] Instagram credentials not configured, using mock");
      return {
        success: true,
        id: `ig_${Date.now()}`,
      };
    }

    // Use Meta Graph API to post to Instagram
    // POST /ig-user-id/media with caption
    const lines = content
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    const caption = lines.join("\n");

    // Create media container (carousel or single)
    const createRes = await fetch(
      `https://graph.instagram.com/v18.0/${igBusinessAccountId}/media`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          caption,
          media_type: "CAROUSEL",
          access_token: igAccessToken,
        }),
      }
    );

    const createData = (await createRes.json()) as any;
    if (!createRes.ok) {
      console.error("[post-to-ig] media creation failed:", createData);
      return {
        success: false,
        error: createData.error?.message || "Failed to create media",
      };
    }

    const mediaId = createData.id;

    // Publish media
    const publishRes = await fetch(
      `https://graph.instagram.com/v18.0/${igBusinessAccountId}/media_publish`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          media_id: mediaId,
          access_token: igAccessToken,
        }),
      }
    );

    const publishData = (await publishRes.json()) as any;
    if (!publishRes.ok) {
      console.error("[post-to-ig] publish failed:", publishData);
      return {
        success: false,
        error: publishData.error?.message || "Failed to publish",
      };
    }

    console.log("[post-to-ig] posted successfully, media_id:", publishData.id);
    return {
      success: true,
      id: publishData.id,
    };
  } catch (error: any) {
    console.error("[post-to-ig] posting error:", error);
    return {
      success: false,
      error: error.message || "Failed to post to Instagram",
    };
  }
}

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    console.log("[post-to-ig] currentUser:", userId);

    if (!userId) {
      return failure("Not authenticated", 401);
    }

    const rateLimitCheck = await checkRateLimit(userId);
    if (!rateLimitCheck.allowed) {
      return failure("Rate limit exceeded. Maximum 3 posts per day.", 429, {
        retryAfter: RATE_LIMIT_WINDOW_SECONDS,
      });
    }

    const body = await req.json();
    const { content } = schema.parse(body);

    // Post to Instagram
    const result = await postToInstagram(content, userId);

    if (!result.success) {
      return failure(result.error || "Failed to post to Instagram", 500);
    }

    const tokenMode = getTokenIssuanceMode();
    const ringAward = 50;

    // Award RING on success
    try {
      let dbUser = await prisma.user.findUnique({
        where: { clerkId: userId },
      });

      if (!dbUser) {
        dbUser = await prisma.user.create({
          data: {
            clerkId: userId,
            ringBalance: tokenMode === "off" ? ringAward : 0,
          },
        });
      } else if (tokenMode === "off") {
        dbUser = await prisma.user.update({
          where: { id: dbUser.id },
          data: {
            ringBalance: { increment: ringAward },
          },
        });
      }

      if (tokenMode !== "off") {
        const earned = await applyLedgerEarn({
          userId,
          amount: ringAward,
          reasonCode: "social_post:ig",
          metadata: { externalId: result.id },
        });
        if (!earned.ok) {
          console.warn("[post-to-ig] ledger earn blocked:", earned.error);
        }
      }

      // Create post record
      await prisma.post.create({
        data: {
          userId: dbUser.id,
          platform: "IG",
          content: content.slice(0, 280),
          externalId: result.id,
          ringEarned: tokenMode === "off" ? ringAward : ringAward,
          status: "published",
        },
      });

      console.log("[post-to-ig] recorded post in DB for user:", dbUser.id);

      // Sync to Clerk metadata (legacy only; ledger mode uses async sync)
      if (tokenMode === "off") {
        try {
          const user = await clerkClient.users.getUser(userId);
          const meta = (user.publicMetadata || {}) as any;
          const posts = Array.isArray(meta.posts) ? meta.posts : [];
          const postObj = {
            id: result.id,
            platform: "IG",
            content: content.slice(0, 280),
            time: new Date().toISOString(),
            ringEarned: ringAward,
          };
          posts.unshift(postObj);
          const newMeta = { ...meta, posts, ring: dbUser.ringBalance };
          await clerkClient.users.updateUser(userId, { publicMetadata: newMeta });
          console.log("[post-to-ig] synced Clerk metadata");
        } catch (clerkErr: any) {
          console.warn("[post-to-ig] failed to sync Clerk metadata:", clerkErr.message);
        }
      }
    } catch (dbErr: any) {
      console.error("[post-to-ig] database error:", dbErr);
    }

    return success({ id: result.id, remaining: rateLimitCheck.remaining });
  } catch (error: any) {
    console.error("[post-to-ig] error:", error);
    return failure(error.message || "Failed to post to Instagram", 500);
  }
}
