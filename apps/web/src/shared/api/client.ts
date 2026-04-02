/**
 * Shared API client — core fetch wrapper and token management.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Token helpers ──────────────────────────────────────────────────────────

/** True when the page is served over HTTPS (or via a secure context). */
const _isSecure =
  typeof window !== "undefined" && window.location.protocol === "https:";

/** Cookie flag string: adds Secure on HTTPS, always SameSite=Lax. */
const _cookieFlags = _isSecure
  ? "path=/; SameSite=Lax; Secure"
  : "path=/; SameSite=Lax";

export function setTokens(access: string, refresh: string) {
  const maxAge = 60 * 30; // 30 min for access
  const refreshMaxAge = 60 * 60 * 24 * 7; // 7 days for refresh

  document.cookie = `access-token=${access}; max-age=${maxAge}; ${_cookieFlags}`;
  document.cookie = `refresh-token=${refresh}; max-age=${refreshMaxAge}; ${_cookieFlags}`;
  // Keep the auth-token cookie that the SSR middleware checks
  document.cookie = `auth-token=${access}; max-age=${maxAge}; ${_cookieFlags}`;
}

export function getAccessToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(/(?:^|; )access-token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function clearTokens() {
  const expired = "Thu, 01 Jan 1970 00:00:01 GMT";
  const flags = _isSecure ? "path=/; Secure" : "path=/";
  document.cookie = `access-token=; ${flags}; expires=${expired}`;
  document.cookie = `refresh-token=; ${flags}; expires=${expired}`;
  document.cookie = `auth-token=; ${flags}; expires=${expired}`;
}

// ── Generic fetch wrapper ──────────────────────────────────────────────────

interface ApiOptions extends RequestInit {
  /** If true, skip automatic Authorization header */
  noAuth?: boolean;
}

/**
 * In-flight GET request deduplication.
 * Concurrent identical GETs share a single fetch promise.
 */
const _inflight = new Map<string, Promise<unknown>>();

export async function apiFetch<T = unknown>(
  path: string,
  options: ApiOptions = {},
): Promise<T> {
  const { noAuth, headers: extraHeaders, ...rest } = options;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(extraHeaders as Record<string, string>),
  };

  if (!noAuth) {
    const token = getAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  const method = (rest.method ?? "GET").toUpperCase();
  const url = `${API_BASE}/api/v1${path}`;

  // Deduplicate concurrent GET requests to the same URL
  if (method === "GET") {
    const existing = _inflight.get(url);
    if (existing) return existing as Promise<T>;
  }

  const promise = (async () => {
    const res = await fetch(url, { headers, ...rest });

    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(res.status, body.detail ?? res.statusText, body);
    }

    // 204 No Content (and other bodyless responses) — return undefined
    if (res.status === 204 || res.headers.get("content-length") === "0") {
      return undefined as T;
    }

    return res.json() as Promise<T>;
  })();

  if (method === "GET") {
    _inflight.set(url, promise);
    promise.finally(() => _inflight.delete(url));
  }

  return promise;
}

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, message: string, body?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export { API_BASE };
