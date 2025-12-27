// src/app/api/post-to-x/route.ts
import { NextRequest } from "next/server";
import crypto from "crypto";
import { TwitterApi } from "twitter-api-v2";
import { z } from "zod";
import { currentUser, clerkClient } from "@clerk/nextjs/server";
import Redis from "ioredis";
import { prisma } from "@/lib/db";
import { embedThread } from "@/lib/embeddings";
import { getTokenIssuanceMode } from "@/lib/ring-ledger";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const enforcementSchema = z
  .object({
    request_id: z.string().min(1).optional(),
    receipt: z
      .object({
        receipt_id: z.string().min(1),
      })
      .optional(),
    qa_summary: z
      .object({
        status: z.enum(["PASS", "FAIL"]),
        violation_codes: z.array(z.string()).optional(),
        risk_score: z.number().optional(),
      })
      .optional(),
    audit_ok: z.boolean().optional(),
    required_edits: z.array(z.string()).optional(),
    mode: z.enum(["off", "advisory", "enforced"]).optional(),
  })
  .optional();

const schema = z.object({
  content: z.string().min(1),
  enforcement: enforcementSchema,
  enforcement_request_id: z.string().min(1).optional(),
  enforcement_receipt_id: z.string().min(1).optional(),
});

const success = (payload: Record<string, unknown>, status = 200) =>
  Response.json({ success: true, ...payload }, { status });

const failure = (error: string, status = 500, extra: Record<string, unknown> = {}) =>
  Response.json({ success: false, error, ...extra }, { status });

async function validateEnforcementReceipt(
  requestId?: string,
  receiptId?: string
): Promise<
  | { ok: true; receipt: { qa_status: "PASS" | "FAIL" } }
  | { ok: false; code: string; message: string }
> {
  try {
    const res = await fetch(`${BACKEND_URL}/v1/enforcement/receipts/validate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_id: requestId,
        receipt_id: receiptId,
      }),
    });
    const payload = await res.json();
    if (!payload?.ok) {
      return { ok: false, code: payload?.code || "RECEIPT_INVALID", message: payload?.message || "Invalid receipt" };
    }
    return { ok: true, receipt: payload.receipt };
  } catch (error: any) {
    return { ok: false, code: "RECEIPT_LOOKUP_FAILED", message: error?.message || "Receipt lookup failed" };
  }
}

async function emitPublishEvent(params: {
  userId: string;
  platform: string;
  content: string;
  platformPostId: string;
  enforcementRequestId?: string;
  enforcementReceiptId?: string;
  metadata?: Record<string, unknown>;
}): Promise<{ ok: boolean; token_result?: Record<string, unknown> }> {
  const hex = crypto
    .createHash("sha256")
    .update(`${params.userId}:${params.platform}:${params.platformPostId}`)
    .digest("hex");
  const eventId = `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20, 32)}`;
  const contentHash = crypto.createHash("sha256").update(params.content).digest("hex");
  try {
    const res = await fetch(`${BACKEND_URL}/v1/tokens/publish`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_id: eventId,
        user_id: params.userId,
        platform: params.platform,
        content_hash: contentHash,
        published_at: new Date().toISOString(),
        platform_post_id: params.platformPostId,
        enforcement_request_id: params.enforcementRequestId,
        enforcement_receipt_id: params.enforcementReceiptId,
        metadata: params.metadata || {},
      }),
    });
    const payload = await res.json();
    if (!payload?.ok) {
      return { ok: false };
    }
    return { ok: true, token_result: payload.token_result };
  } catch (error) {
    return { ok: false };
  }
}

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
    console.error("[post-to-x] Redis error:", err);
  });
  _redis = client;
  return client;
}

// Rate limiting constants: max 5 posts per hour per user
const RATE_LIMIT_WINDOW_SECONDS = 3600; // 1 hour
const RATE_LIMIT_MAX_POSTS = 5;

async function checkRateLimit(userId: string): Promise<{ allowed: boolean; remaining: number; retryAfter: number }> {
  const key = `rate:post:x:${userId}`;
  const now = Date.now();
  const windowStart = now - RATE_LIMIT_WINDOW_SECONDS * 1000;

  try {
    const redis = getRedis();
    // Use Redis ZSET for sliding window: score = timestamp, member = request ID
    // Remove expired entries
    await redis.zremrangebyscore(key, 0, windowStart);

    // Count current requests in window
    const count = await redis.zcard(key);

    if (count >= RATE_LIMIT_MAX_POSTS) {
      // Get oldest entry's timestamp to calculate retry_after
      const oldest = await redis.zrange(key, 0, 0, "WITHSCORES");
      const retryAfter = oldest.length > 1
        ? Math.ceil((parseInt(oldest[1]) + RATE_LIMIT_WINDOW_SECONDS * 1000 - now) / 1000)
        : RATE_LIMIT_WINDOW_SECONDS;

      console.warn(`[post-to-x] rate limit exceeded for ${userId}: ${count}/${RATE_LIMIT_MAX_POSTS}`);
      return { allowed: false, remaining: 0, retryAfter };
    }

    // Add current request to the window
    const requestId = `${now}-${Math.random().toString(36).substring(7)}`;
    await redis.zadd(key, now, requestId);
    // Set expiration on the key
    await redis.expire(key, RATE_LIMIT_WINDOW_SECONDS);

    const remaining = RATE_LIMIT_MAX_POSTS - count - 1;
    console.log(`[post-to-x] rate limit check passed for ${userId}: ${count + 1}/${RATE_LIMIT_MAX_POSTS}`);
    return { allowed: true, remaining, retryAfter: 0 };
  } catch (redisErr: any) {
    console.error("[post-to-x] Redis rate limit check error:", redisErr);
    // Fall through on Redis error (allow request)
    return { allowed: true, remaining: -1, retryAfter: 0 };
  }
}

export async function POST(req: NextRequest) {
  try {
    const enforcementMode = process.env.ONERING_ENFORCEMENT_MODE || "off";
    const caller = await currentUser();
    const userId = caller?.id;
    console.log("[post-to-x] currentUser:", userId);

    if (!userId) {
      return failure("Not authenticated", 401);
    }

    const body = await req.json();
    const { content, enforcement, enforcement_request_id, enforcement_receipt_id } = schema.parse(body);
    const enforcementWarnings: string[] = [];
    let enforcementRequestId: string | undefined = enforcement_request_id || enforcement?.request_id;
    let enforcementReceiptId: string | undefined = enforcement_receipt_id || enforcement?.receipt?.receipt_id;

    if (enforcementMode !== "off") {
      const receiptId = enforcementReceiptId;
      const requestId = enforcementRequestId;

      if (!receiptId && !requestId) {
        if (enforcementMode === "enforced") {
          return failure("Enforcement receipt required", 400, {
            code: "ENFORCEMENT_RECEIPT_REQUIRED",
            suggestedFix: "Regenerate content with enforcement enabled and pass enforcement_request_id to posting.",
            details: { enforcement_request_id: null, enforcement_receipt_id: null },
          });
        }
        enforcementWarnings.push("ENFORCEMENT_RECEIPT_MISSING");
      } else {
        const receiptCheck = await validateEnforcementReceipt(requestId, receiptId);
        if (!receiptCheck.ok) {
          if (enforcementMode === "enforced") {
            const suggestedFix =
              receiptCheck.code === "AUDIT_WRITE_FAILED"
                ? "Ensure audit tables are created before enabling enforced mode."
                : receiptCheck.code === "ENFORCEMENT_RECEIPT_EXPIRED"
                ? "Receipt expired. Regenerate content and try posting again."
                : "Regenerate content with enforcement enabled and pass a valid enforcement_request_id.";
            return failure("Enforcement receipt invalid", 403, {
              code: receiptCheck.code,
              suggestedFix,
              details: { reason: receiptCheck.code, message: receiptCheck.message },
            });
          }
          enforcementWarnings.push("ENFORCEMENT_RECEIPT_INVALID");
        } else if (receiptCheck.receipt.qa_status !== "PASS") {
          if (enforcementMode === "enforced") {
            return failure("QA blocked publishing", 403, {
              code: "QA_BLOCKED",
              suggestedFix: "Resolve required edits and regenerate content through the enforcement pipeline.",
              details: {
                qa_status: receiptCheck.receipt.qa_status,
              },
            });
          }
          enforcementWarnings.push("QA_FAILED");
        }
      }
    }

    const rateLimitCheck = await checkRateLimit(userId);
    if (!rateLimitCheck.allowed) {
      return failure("Rate limit exceeded. Maximum 5 posts per hour.", 429, {
        retryAfter: rateLimitCheck.retryAfter,
        ...(enforcementWarnings.length ? { warnings: enforcementWarnings } : {}),
      });
    }

    if (enforcementMode === "advisory" && enforcementWarnings.length) {
      console.warn("[post-to-x] enforcement warnings:", enforcementWarnings);
    }

    // Verify credentials exist
    if (!process.env.TWITTER_API_KEY || !process.env.TWITTER_API_SECRET || !process.env.TWITTER_ACCESS_TOKEN || !process.env.TWITTER_ACCESS_TOKEN_SECRET) {
      console.error("[post-to-x] missing Twitter credentials in environment");
      return failure(
        "Twitter credentials not configured. Add TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET to .env.local",
        500,
        enforcementWarnings.length ? { warnings: enforcementWarnings } : {}
      );
    }

    const client = new TwitterApi({
      appKey: process.env.TWITTER_API_KEY,
      appSecret: process.env.TWITTER_API_SECRET,
      accessToken: process.env.TWITTER_ACCESS_TOKEN,
      accessSecret: process.env.TWITTER_ACCESS_TOKEN_SECRET,
    });

    // Validate credentials by testing a read-only API call
    try {
      console.log("[post-to-x] validating Twitter credentials...");
      await client.v2.me();
      console.log("[post-to-x] credentials validated");
    } catch (authErr: any) {
      console.error("[post-to-x] credential validation failed:", {
        status: authErr.status,
        code: authErr.code,
        message: authErr.message,
        detail: authErr.data?.detail || authErr.data?.error
      });
      
      const errorDetail = authErr.data?.detail || authErr.data?.error || authErr.message;
      if (authErr.status === 403) {
        return failure(
          "Twitter API 403: Not Permitted. Your app may lack 'Read+Write' permissions or tokens are invalid.",
          403,
          {
            detail: errorDetail,
            suggestedFix:
              "1. Check Twitter Developer Portal for app permissions (needs Read+Write+DM)\n2. Regenerate API keys if expired\n3. Update .env.local with fresh credentials\n4. Ensure app is linked to your account",
          }
        );
      } else if (authErr.status === 401) {
        return failure(
          "Twitter API 401: Unauthorized. Your credentials are invalid or expired.",
          401,
          { detail: errorDetail, suggestedFix: "Regenerate API keys from Twitter Developer Portal and update .env.local" }
        );
      }
      throw authErr;
    }

    const lines = content
      .split("\n")
      .map((l) => l.trim())
      .filter((l) => l.length > 0);

    let previousTweetId: string | null = null;
    const postedTweets: string[] = [];

    for (let i = 0; i < lines.length; i++) {
      // Don't add numbering - tweets should be posted as-is
      // If they need numbering, the content generation should handle it
      const text = lines[i];

      try {
        console.log(`[post-to-x] posting tweet ${i + 1}/${lines.length}...`);
        const tweet = await client.v2.tweet(text, {
          ...(previousTweetId && { reply: { in_reply_to_tweet_id: previousTweetId } }),
        });

        previousTweetId = tweet.data.id;
        postedTweets.push(tweet.data.id);
        console.log(`[post-to-x] tweet ${i + 1} posted: ${tweet.data.id}`);
      } catch (tweetErr: any) {
        console.error(`[post-to-x] failed to post tweet ${i + 1}:`, {
          text: text.slice(0, 100),
          status: tweetErr.status,
          message: tweetErr.message,
          code: tweetErr.code,
          twitterDetail: tweetErr.data?.detail || tweetErr.data?.error,
          fullData: tweetErr.data
        });
        
        // If it's a 403, provide detailed help
        if (tweetErr.status === 403) {
          return failure(
            `Tweet ${i + 1} failed with 403 Forbidden: You are not permitted to perform this action.`,
            403,
            {
              detail: tweetErr.data?.detail || "Likely due to insufficient permissions or write-only token restriction",
              suggestedFix: "Check Twitter app permissions require 'Read + Write'. Regenerate tokens in Developer Portal.",
              failedTweetIndex: i + 1,
              failedTweetText: text.slice(0, 200),
            }
          );
        }
        
        throw new Error(`Tweet ${i + 1} failed: ${tweetErr.message || tweetErr.code} (HTTP ${tweetErr.status})`);
      }
    }

    const url = `https://x.com/${process.env.TWITTER_USERNAME || "i"}/status/${previousTweetId}`;
    console.log("[post-to-x] posted, url:", url, "by user:", userId);

    // Notify backend streak service (idempotent, best-effort)
    try {
      await fetch(`${BACKEND_URL}/v1/streaks/events/post`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          post_id: previousTweetId,
          posted_at: new Date().toISOString(),
          platform: "x",
        }),
      });
    } catch (notifyErr: any) {
      console.warn("[post-to-x] streak notify failed (non-blocking):", notifyErr?.message || notifyErr);
    }

    let tokenResult: Record<string, unknown> | null = null;

    // Write to database and update Clerk metadata
    try {
      const tokenIssuanceMode = getTokenIssuanceMode();
      // Ensure user exists in Postgres
      let dbUser = await prisma.user.findUnique({
        where: { clerkId: userId },
      });
      const createdUser = !dbUser;

      if (!dbUser) {
        // Create user if doesn't exist
        dbUser = await prisma.user.create({
          data: {
            clerkId: userId,
            ringBalance: tokenIssuanceMode === "off" ? 50 : 0,
          },
        });
        console.log("[post-to-x] created new user in DB:", dbUser.id);
      }

      const publishResult = await emitPublishEvent({
        userId,
        platform: "x",
        content,
        platformPostId: previousTweetId,
        enforcementRequestId,
        enforcementReceiptId,
        metadata: {
          rate_limit_remaining: rateLimitCheck.remaining,
          rate_limit_retry_after: rateLimitCheck.retryAfter,
          thread_size: lines.length,
        },
      });
      if (publishResult.ok && publishResult.token_result) {
        tokenResult = publishResult.token_result;
      } else {
        tokenResult = {
          mode: tokenIssuanceMode,
          issued_amount: 0,
          pending_amount: 0,
          reason_code: "TOKEN_ISSUANCE_FAILED",
          guardrails_applied: [],
        };
      }

      const tokenMode = typeof tokenResult?.mode === "string" ? tokenResult.mode : tokenIssuanceMode;
      const issuedAmount = typeof tokenResult?.issued_amount === "number" ? tokenResult.issued_amount : 0;
      const pendingAmount = typeof tokenResult?.pending_amount === "number" ? tokenResult.pending_amount : 0;
      const ringEarned = tokenMode === "off"
        ? 50
        : tokenMode === "shadow"
        ? pendingAmount
        : issuedAmount;

      if (tokenMode === "off" && !createdUser) {
        // Increment ring balance only when token issuance is off (legacy behavior).
        dbUser = await prisma.user.update({
          where: { id: dbUser.id },
          data: {
            ringBalance: { increment: 50 },
          },
        });
      } else if (tokenMode === "live") {
        const refreshed = await prisma.user.findUnique({ where: { id: dbUser.id } });
        if (refreshed) {
          dbUser = refreshed;
        }
      }

      // Create post record in database
      await prisma.post.create({
        data: {
          userId: dbUser.id,
          platform: "X",
          content: content.slice(0, 280),
          externalId: previousTweetId,
          ringEarned,
          status: "published",
        },
      });

      // Embed thread content for pgvector storage
      try {
        const threadEmbedding = await embedThread(content);
        console.log("[post-to-x] embedded thread (1536 dims) for pgvector storage");

        // In production, store embedding in User.pastThreads vector column
        // await prisma.user.update({
        //   where: { id: dbUser.id },
        //   data: {
        //     pastThreads: { push: threadEmbedding }
        //   }
        // });
      } catch (embedErr: any) {
        console.warn("[post-to-x] thread embedding skipped:", embedErr.message);
      }

      console.log("[post-to-x] recorded post in DB for user:", dbUser.id, { ringBalance: dbUser.ringBalance, ringEarned });

      // Also sync to Clerk metadata for fallback (legacy only)
      if (tokenMode === "off") {
        try {
          const clerk = await clerkClient();
          const user = await clerk.users.getUser(userId);
          const meta = (user.publicMetadata || {}) as any;
          const posts = Array.isArray(meta.posts) ? meta.posts : [];
          const postObj = {
            id: previousTweetId,
            platform: "X",
            content: content.slice(0, 280),
            time: new Date().toISOString(),
            views: Math.floor(Math.random() * 1000),
            likes: Math.floor(Math.random() * 200),
            ringEarned,
          };
          posts.unshift(postObj);
          const newMeta = { ...meta, posts, ring: dbUser.ringBalance };
          await clerk.users.updateUser(userId, { publicMetadata: newMeta });
          console.log("[post-to-x] synced Clerk metadata for", userId);
        } catch (clerkErr: any) {
          console.warn("[post-to-x] failed to sync Clerk metadata:", clerkErr.message);
        }
      }
    } catch (dbErr: any) {
      console.error("[post-to-x] failed to write to database:", dbErr);
    }

    return success({
      url,
      remaining: rateLimitCheck.remaining,
      ...(tokenResult ? { token_result: tokenResult } : {}),
      ...(enforcementWarnings.length ? { warnings: enforcementWarnings } : {}),
    });
  } catch (error: any) {
    console.error("[post-to-x] X post failed:", error);
    return failure(error.message || "Failed to post to X", 500);
  }
}
