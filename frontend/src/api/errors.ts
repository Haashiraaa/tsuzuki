/** A failed request, with a message fit to show on screen. */
export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong";
}
