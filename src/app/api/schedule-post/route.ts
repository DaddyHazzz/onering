// src/app/api/schedule-post/route.ts
import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";
import { z } from "zod";

const schema = z.object({
  content: z.string().min(1),
  delayMinutes: z.number().optional().default(1),
});

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    console.log("[schedule-post] currentUser:", userId);

    if (!userId) {
      return Response.json({ error: "Not authenticated" }, { status: 401 });
    }

    const body = await req.json();
    const { content, delayMinutes } = schema.parse(body);
    const delaySeconds = delayMinutes * 60;

    console.log("[schedule-post] scheduling post for user:", userId, { delayMinutes });

    // Get or create user in DB
    let dbUser = await prisma.user.findUnique({
      where: { clerkId: userId },
    });

    if (!dbUser) {
      dbUser = await prisma.user.create({
        data: { clerkId: userId },
      });
      console.log("[schedule-post] created user:", dbUser.id);
    }

    // Create post record with "scheduled" status
    const post = await prisma.post.create({
      data: {
        userId: dbUser.id,
        platform: "X",
        content: content.slice(0, 280),
        status: "scheduled",
        scheduledFor: new Date(Date.now() + delaySeconds * 1000),
      },
    });

    console.log("[schedule-post] created scheduled post record:", post.id);

    // Enqueue job to RQ via backend endpoint
    const backendRes = await fetch(`${BACKEND_URL}/v1/jobs/schedule-post`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        content,
        user_id: userId,
        delay_seconds: delaySeconds,
        post_id: post.id,
      }),
    });

    const backendData = await backendRes.json();

    if (!backendRes.ok) {
      console.error("[schedule-post] backend error:", backendData);
      return Response.json(
        { error: `Backend error: ${backendData.error || "Unknown error"}` },
        { status: 500 }
      );
    }

    console.log("[schedule-post] enqueued job via backend:", backendData.job_id);

    return Response.json({
      scheduled: true,
      inMinutes: delayMinutes,
      postId: post.id,
      jobId: backendData.job_id,
      message: `Post scheduled for ${delayMinutes} minute(s) from now`,
    });
  } catch (error: any) {
    console.error("[schedule-post] error:", error);
    if (error.name === "ZodError") {
      return Response.json({ error: "Invalid request" }, { status: 400 });
    }
    return Response.json({ error: error?.message || String(error) }, { status: 500 });
  }
}
