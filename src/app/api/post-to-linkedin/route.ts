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
    lazyConnect: true,
  });
  _redis = client;
  return client;
}

const RATE_LIMIT_WINDOW_SECONDS = 86400;
const RATE_LIMIT_MAX_POSTS = 3;

async function checkRateLimit(userId: string) {
  const key = `rate:post:li:${userId}`;
  const now = Date.now();
  const windowStart = now - RATE_LIMIT_WINDOW_SECONDS * 1000;
  const redis = getRedis();
  await redis.zremrangebyscore(key, 0, windowStart);
  const count = await redis.zcard(key);
  if (count >= RATE_LIMIT_MAX_POSTS) return { allowed: false, remaining: 0 };
  const requestId = `${now}-${Math.random().toString(36).slice(2)}`;
  await redis.zadd(key, now, requestId);
  await redis.expire(key, RATE_LIMIT_WINDOW_SECONDS);
  return { allowed: true, remaining: RATE_LIMIT_MAX_POSTS - count - 1 };
}

async function postToLinkedIn(content: string) {
  const token = process.env.LINKEDIN_ACCESS_TOKEN;
  const authorUrn = process.env.LINKEDIN_AUTHOR_URN; // e.g., urn:li:person:xxxx or urn:li:organization:xxxx

  if (!token || !authorUrn) {
    console.warn("[post-to-linkedin] Missing credentials, using mock");
    return { success: true, id: `li_${Date.now()}` };
  }

  const body = {
    author: authorUrn,
    lifecycleState: "PUBLISHED",
    specificContent: {
      "com.linkedin.ugc.ShareContent": {
        shareCommentary: { text: content.slice(0, 1300) },
        shareMediaCategory: "NONE",
      },
    },
    visibility: { "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC" },
  };

  const res = await fetch("https://api.linkedin.com/v2/ugcPosts", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      "X-Restli-Protocol-Version": "2.0.0",
    },
    body: JSON.stringify(body),
  });

  const data = (await res.json()) as any;
  if (!res.ok) {
    console.error("[post-to-linkedin] error:", data);
    return { success: false, error: data.message || "LinkedIn post failed" };
  }
  return { success: true, id: data.id || data.entity };
}

export async function POST(req: NextRequest) {
  try {
    const user = await currentUser();
    const userId = user?.id;
    if (!userId) return failure("Not authenticated", 401);

    const rate = await checkRateLimit(userId);
    if (!rate.allowed) return failure("Rate limit exceeded", 429, { retryAfter: RATE_LIMIT_WINDOW_SECONDS });

    const body = await req.json();
    const { content } = schema.parse(body);

    const result = await postToLinkedIn(content);
    if (!result.success) return failure(result.error || "Failed to post", 500);

    const tokenMode = getTokenIssuanceMode();
    const ringAward = 50;

    // Award RING and record post
    let dbUser = await prisma.user.findUnique({ where: { clerkId: userId } });
    if (!dbUser) {
      dbUser = await prisma.user.create({ data: { clerkId: userId, ringBalance: tokenMode === "off" ? ringAward : 0 } });
    } else if (tokenMode === "off") {
      dbUser = await prisma.user.update({ where: { id: dbUser.id }, data: { ringBalance: { increment: ringAward } } });
    }

    if (tokenMode !== "off") {
      const earned = await applyLedgerEarn({
        userId,
        amount: ringAward,
        reasonCode: "social_post:li",
        metadata: { externalId: result.id },
      });
      if (!earned.ok) {
        console.warn("[post-to-linkedin] ledger earn blocked:", earned.error);
      }
    }
    await prisma.post.create({
      data: {
        userId: dbUser.id,
        platform: "LI",
        content: content.slice(0, 280),
        externalId: result.id,
        ringEarned: ringAward,
        status: "published",
      },
    });

    if (tokenMode === "off") {
      try {
        const clerkUser = await clerkClient.users.getUser(userId);
        const meta = (clerkUser.publicMetadata || {}) as any;
        const posts = Array.isArray(meta.posts) ? meta.posts : [];
        posts.unshift({ id: result.id, platform: "LI", content: content.slice(0, 280), time: new Date().toISOString(), ringEarned: ringAward });
        await clerkClient.users.updateUser(userId, { publicMetadata: { ...meta, posts, ring: dbUser.ringBalance } });
      } catch (e: any) {
        console.warn("[post-to-linkedin] clerk metadata sync failed:", e.message);
      }
    }

    return success({ id: result.id, remaining: rate.remaining });
  } catch (e: any) {
    console.error("[post-to-linkedin] error:", e);
    return failure(e.message || "Failed to post", 500);
  }
}
