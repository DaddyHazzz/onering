import { describe, it, expect } from "vitest";
import { schema as generateSchema } from "../app/api/generate/route";

// Note: We avoid importing posting routes to prevent accidental SDK init.
// Instead, validate the generate route schema which mirrors backend contracts.

describe("Frontend contract schemas", () => {
  it("accepts valid generate payload", () => {
    const parsed = generateSchema.parse({
      prompt: "hello",
      type: "simple",
      platform: "x",
      user_id: "u",
      stream: true,
    });
    expect(parsed.prompt).toBe("hello");
  });

  it("rejects invalid type", () => {
    expect(() => generateSchema.parse({
      prompt: "hello",
      type: "unknown",
      platform: "x",
      user_id: "u",
    })).toThrow();
  });

  it("requires user_id and platform", () => {
    expect(() => generateSchema.parse({ prompt: "hi" })).toThrow();
  });
});
