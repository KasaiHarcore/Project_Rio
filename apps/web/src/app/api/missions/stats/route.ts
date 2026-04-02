/**
 * Next.js API route that proxies mission stats to the FastAPI backend.
 *
 * Route:
 *   GET /api/missions/stats → GET /api/v1/missions/stats
 */

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

function getAccessToken(req: Request): string | null {
  const cookieHeader = req.headers.get("cookie") ?? "";
  const match = cookieHeader.match(/(?:^|; )access-token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export async function GET(req: Request) {
  const token = getAccessToken(req);
  if (!token) {
    return new Response(JSON.stringify({ error: "Not authenticated" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const res = await fetch(`${BACKEND_URL}/api/v1/missions/stats`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const body = await res.text();
  return new Response(body, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
