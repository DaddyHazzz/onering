export function stripNumbering(text: string): string {
  return text
    // 1. "1." or "1) "
    .replace(/^\s*\d+[\.\)]\s*/g, "")
    // 2. "2/6 "
    .replace(/^\s*\d+\s*\/\s*\d+\s*/g, "")
    // 3. "[3] "
    .replace(/^\s*\[\d+\]\s*/g, "")
    // 4. "(4) "
    .replace(/^\s*\(\d+\)\s*/g, "")
    // 5. bullets
    .replace(/^\s*[\-\*•]\s*/g, "")
    .trim();
}
