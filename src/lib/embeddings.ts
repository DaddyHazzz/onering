// src/lib/embeddings.ts
import { Groq } from "groq-sdk";
import seedrandom from "seedrandom";

let groqClient: Groq | null = null;

/**
 * Lazily initialize Groq client.
 * This prevents crashes during tests when GROQ_API_KEY is missing.
 */
function getGroq(): Groq {
  if (!groqClient) {
    const apiKey = process.env.GROQ_API_KEY;
    if (!apiKey) {
      throw new Error(
        "GROQ_API_KEY is missing. Groq client cannot be initialized."
      );
    }
    groqClient = new Groq({ apiKey });
  }
  return groqClient;
}

/**
 * Embed thread content using deterministic seeded randomization for pgvector storage.
 * Returns a 1536-dimensional vector (compatible with pgvector).
 */
export async function embedThread(content: string): Promise<number[]> {
  try {
    // ⚠️ NOTE:
    // This is a deterministic fake embedding.
    // getGroq() is intentionally NOT called here yet.
    // When you switch to real embeddings, call getGroq() inside this function.

    const hash = content
      .split("")
      .reduce((acc, char) => {
        return ((acc << 5) - acc + char.charCodeAt(0)) | 0;
      }, 0);

    const seed = Math.abs(hash) % 1_000_000;
    const random = seedrandom(seed.toString());

    const vector: number[] = [];
    for (let i = 0; i < 1536; i++) {
      vector.push(random() * 2 - 1);
    }

    const magnitude = Math.sqrt(
      vector.reduce((sum, val) => sum + val * val, 0)
    );

    return vector.map((val) => val / magnitude);
  } catch (error) {
    console.error("[embeddings] error embedding content:", error);
    return new Array(1536).fill(0);
  }
}

/**
 * Embed user profile (bio + recent posts).
 */
export async function embedUserProfile(
  userName: string,
  recentPosts: string[] = []
): Promise<number[]> {
  try {
    const profileContent = `
User: ${userName}
Recent posts:
${recentPosts.slice(0, 5).join("\n---\n")}
    `.trim();

    const hash = profileContent
      .split("")
      .reduce((acc, char) => {
        return ((acc << 5) - acc + char.charCodeAt(0)) | 0;
      }, 0);

    const seed = Math.abs(hash) % 1_000_000;
    const random = seedrandom(seed.toString());

    const vector: number[] = [];
    for (let i = 0; i < 1536; i++) {
      vector.push(random() * 2 - 1);
    }

    const magnitude = Math.sqrt(
      vector.reduce((sum, val) => sum + val * val, 0)
    );

    return vector.map((val) => val / magnitude);
  } catch (error) {
    console.error("[embeddings] error embedding profile:", error);
    return new Array(1536).fill(0);
  }
}

/**
 * Calculate cosine similarity between two vectors.
 */
export function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) {
    throw new Error("Vectors must have same dimension");
  }

  let dot = 0;
  let magA = 0;
  let magB = 0;

  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    magA += a[i] * a[i];
    magB += b[i] * b[i];
  }

  if (magA === 0 || magB === 0) return 0;

  return dot / (Math.sqrt(magA) * Math.sqrt(magB));
}
