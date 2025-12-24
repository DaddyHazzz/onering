// src/lib/error-handler.ts
/**
 * Safely extract error message from any error object.
 * Prevents "Unexpected token '<'" when error contains HTML.
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "string") {
    return error;
  }
  if (typeof error === "object" && error !== null && "message" in error) {
    return String((error as any).message);
  }
  return "An unknown error occurred";
}

/**
 * Safely serialize an error for JSON response.
 */
export function serializeError(error: unknown) {
  const message = getErrorMessage(error);
  const code = (error instanceof Error) ? error.name : "UnknownError";
  return { error: message, code };
}
