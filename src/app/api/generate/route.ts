// src/app/api/generate/route.ts
import { NextRequest } from "next/server";
import Groq from "groq-sdk";
import { z } from "zod";

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY! });

const schema = z.object({
  prompt: z.string().min(1).max(2000), // plenty for long threads
});

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { prompt } = schema.parse(body);

    const completion = await groq.chat.completions.create({
      messages: [
        {
          role: "system",
          content:
            "You are an elite viral content creator for X/Twitter. Write in first person, raw, emotional, zero fluff. Use short sentences. Add controversy when possible. End with a strong CTA. Always return exactly one long tweet or a numbered thread.",
        },
        {
          role: "user",
          content: prompt,
        },
      ],
      model: "llama-3.1-8b-instant", // Fastest free model for viral posts      temperature: 0.9,
      max_tokens: 1024,
    });

    const content = completion.choices[0]?.message?.content || "No response generated.";

    return Response.json({ content });
  } catch (error: any) {
    console.error("Groq error:", error);
    return Response.json({ error: error.message }, { status: 500 });
  }
}