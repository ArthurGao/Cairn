import type { Schemas } from "./client";

/** An API error with the server's `{error: {code, message}}` body (design §11). */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

type Outcome<T> = { data?: T; error?: unknown; response: Response };

/** Return the data or throw an ApiError carrying the API's own message (never an empty list). */
export function unwrap<T>({ data, error, response }: Outcome<T>): T {
  if (error !== undefined || data === undefined) {
    const body = error as Partial<Schemas["ErrorResponse"]> | undefined;
    throw new ApiError(
      response.status,
      body?.error?.code ?? "http_error",
      body?.error?.message ?? `HTTP ${response.status} with no error message`,
    );
  }
  return data;
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return `The API could not be reached (${error.message})`;
  return "Unknown error";
}
