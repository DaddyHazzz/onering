// src/app/api/generate/route.ts
import { NextRequest } from "next/server";
import { z } from "zod";
import { currentUser } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";
import { embedUserProfile } from "@/lib/embeddings";
import { getErrorMessage } from "@/lib/error-handler";

export const schema = z.object({
  prompt: z.string().min(1).max(2000),
  type: z.enum(["simple", "viral_thread"]).default("simple"),
  platform: z.string().min(1).default("x"),
  user_id: z.string().min(1),
  stream: z.boolean().optional().default(true),
});

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const callerClerkId = caller?.id;

    const body = await req.json();
    const { prompt, type, platform, user_id, stream } = schema.parse(body);

    console.log("[generate] forwarding prompt to backend:", prompt.slice(0, 50) + "...", { type, platform, user_id, stream });

    // Auto-embed user profile on first generation if userId provided
    // NOTE: Disabled for now - profileEmbedding is Unsupported("vector") type
    // if (userId && mode === "viral_thread") {
    //   try {
    //     const dbUser = await prisma.user.findUnique({
    //       where: { clerkId: userId },
    //       include: {
    //         postHistory: {
    //           where: { status: "published" },
    //           orderBy: { createdAt: "desc" },
    //           take: 5,
    //         },
    //       },
    //     });

    //     if (dbUser && !dbUser.profileEmbedding) {
    //       const recentPostContents = dbUser.postHistory.map((p) => p.content);
    //       const userEmbedding = await embedUserProfile(caller?.username || "User", recentPostContents);

    //       // Store profile embedding for future use
    //       await prisma.user.update({
    //         where: { id: dbUser.id },
    //         data: {
    //           profileEmbedding: userEmbedding,
    //         },
    //       });
    //       console.log("[generate] embedded user profile for", userId);
    //     }
    //   } catch (embedErr: any) {
    //     console.warn("[generate] profile embedding skipped:", embedErr.message);
    //   }
    // }

    // Fetch streaming response from FastAPI backend
    const backendUrl = `${BACKEND_URL}/v1/generate/content`;
    console.log("[generate] calling backend:", backendUrl);
    
    const backendRes = await fetch(backendUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        type,
        platform,
        user_id,
        stream,
      }),
    });

    if (!backendRes.ok) {
      const errorText = await backendRes.text();
      console.error("[generate] backend error:", backendRes.status, errorText);
      
      // Check if error response is HTML (404, 500, etc.)
      if (errorText.toLowerCase().includes('<!doctype') || errorText.toLowerCase().includes('<html')) {
        return Response.json(
          { error: `Backend error ${backendRes.status}: ${backendRes.statusText}. Check backend is running on ${BACKEND_URL}` },
          { status: 502 }
        );
      }
      
      return Response.json(
        { error: `Backend error: ${backendRes.statusText}` },
        { status: backendRes.status }
      );
    }

    // Pipe the backend's streaming response directly to the client
    // The backend returns text/event-stream with tokens as "data: token\n\n"
    const reader = backendRes.body?.getReader();
    if (!reader) {
      return Response.json({ error: "No response body from backend" }, { status: 500 });
    }

    const customReadable = new ReadableStream({
      async start(controller) {
        try {
          const decoder = new TextDecoder();
          while (true) {
            const { done, value } = await reader.read();
            if (done) {
              controller.close();
              break;
            }
            const chunk = decoder.decode(value, { stream: true });
            controller.enqueue(new TextEncoder().encode(chunk));
          }
        } catch (error: any) {
          console.error("[generate] stream error:", error);
          controller.error(error);
        }
      },
    });

    return new Response(customReadable, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error: any) {
    console.error("[generate] error:", error);
    return Response.json({ error: getErrorMessage(error) }, { status: 500 });
  }
}