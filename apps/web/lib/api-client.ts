export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export class CsrfError extends ApiError {
  constructor() {
    super("CSRF token missing or invalid", 403);
    this.name = "CsrfError";
  }
}

/**
 * Returns the API base URL.
 * - Server components: use the internal Docker network address (NEXT_PUBLIC_API_URL or http://api:8000)
 * - Client components: use "" so the Next.js rewrites at /api/v1 are used
 */
function getBaseUrl(): string {
  if (typeof window === "undefined") {
    return process.env.INTERNAL_API_URL ?? "http://api:8000";
  }
  return "";
}

/**
 * Core fetch wrapper.
 * - Always sends credentials (session cookie)
 * - Reads CSRF token from window.__CSRF_TOKEN__ for mutating requests
 * - Handles 401 → redirect to login (client only)
 * - Handles 403 → throws CsrfError
 */
async function fetchWithAuth<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${getBaseUrl()}/api/v1${path}`;

  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  const method = options.method ?? "GET";
  if (
    typeof window !== "undefined" &&
    ["POST", "PUT", "PATCH", "DELETE"].includes(method)
  ) {
    const token = (window as Window & { __CSRF_TOKEN__?: string }).__CSRF_TOKEN__;
    if (token) {
      headers.set("X-CSRF-Token", token);
    }
  }

  const credentialsOption = options.credentials ?? "include";

  if (typeof window === "undefined") {
    // We are on the server
    try {
      const { cookies } = await import("next/headers");
      const cookieStore = await cookies();
      const cookieHeader = cookieStore.toString();
      if (cookieHeader) {
        headers.set("cookie", cookieHeader);
      }
    } catch {
      // Ignore if next/headers is not available
    }
  }

  const res = await fetch(url, {
    ...options,
    headers,
    credentials: credentialsOption,
  });

  if (res.status === 401 && typeof window !== "undefined") {
    if (window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
    throw new ApiError("Unauthorized", 401);
  }

  if (res.status === 403) {
    throw new CsrfError();
  }

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const data = (await res.json()) as { detail?: string; error?: string };
      message = data.detail ?? data.error ?? message;
    } catch {
      // ignore parse errors
    }
    throw new ApiError(message, res.status);
  }

  const text = await res.text();
  return (text ? JSON.parse(text) : {}) as T;
}

export function apiGet<T>(path: string, options?: RequestInit): Promise<T> {
  return fetchWithAuth<T>(path, { ...options, method: "GET" });
}

export function apiPost<T>(
  path: string,
  body?: unknown,
  options?: RequestInit
): Promise<T> {
  return fetchWithAuth<T>(path, {
    ...options,
    method: "POST",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function apiPatch<T>(
  path: string,
  body?: unknown,
  options?: RequestInit
): Promise<T> {
  return fetchWithAuth<T>(path, {
    ...options,
    method: "PATCH",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function apiPut<T>(
  path: string,
  body?: unknown,
  options?: RequestInit
): Promise<T> {
  return fetchWithAuth<T>(path, {
    ...options,
    method: "PUT",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function apiDelete<T>(path: string, options?: RequestInit): Promise<T> {
  return fetchWithAuth<T>(path, { ...options, method: "DELETE" });
}
