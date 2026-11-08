import { ApiError } from "./errors";

const BASE = "/api";

interface Options {
  method?: "GET" | "POST" | "DELETE";
  body?: unknown;
  query?: Record<string, string | number | boolean | undefined>;
}

function withQuery(path: string, query: Options["query"]): string {
  if (!query) return `${BASE}${path}`;
  const pairs = Object.entries(query)
    .filter(([, value]) => value !== undefined && value !== "")
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
  return pairs.length ? `${BASE}${path}?${pairs.join("&")}` : `${BASE}${path}`;
}

/** The server's own error text when it sent one, else a plain message for the status. */
async function failure(response: Response): Promise<ApiError> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return new ApiError(data.detail, response.status);
  } catch {
    /* not JSON: fall through to the generic message */
  }
  return new ApiError(`The server answered ${response.status}`, response.status);
}

export async function request<T>(path: string, options: Options = {}): Promise<T> {
  const { method = "GET", body, query } = options;
  let response: Response;
  try {
    response = await fetch(withQuery(path, query), {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Cannot reach the Tsuzuki server", 0);
  }
  if (!response.ok) throw await failure(response);
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}
