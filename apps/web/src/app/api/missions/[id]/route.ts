/**
 * Next.js API route for a single mission.
 *
 * Routes:
 *   GET    /api/missions/[id]        → GET    /api/v1/missions/{id}
 *   PATCH  /api/missions/[id]        → PATCH  /api/v1/missions/{id}
 *   DELETE /api/missions/[id]        → DELETE /api/v1/missions/{id}
 */

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

function getAccessToken(req: Request): string | null {
  const cookieHeader = req.headers.get("cookie") ?? "";
  const match = cookieHeader.match(/(?:^|; )access-token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

type RouteContext = { params: Promise<{ id: string }> };

export async function GET(req: Request, ctx: RouteContext) {
  const { id } = await ctx.params;
  const token = getAccessToken(req);
  if (!token) {
    return new Response(JSON.stringify({ error: "Not authenticated" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const res = await fetch(`${BACKEND_URL}/api/v1/missions/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const body = await res.text();
  return new Response(body, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function PATCH(req: Request, ctx: RouteContext) {
  const { id } = await ctx.params;
  const token = getAccessToken(req);
  if (!token) {
    return new Response(JSON.stringify({ error: "Not authenticated" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  // Check if this is a step toggle request
  const url = new URL(req.url);
  const pathParts = url.pathname.split("/");
  // Pattern: /api/missions/{id}/steps/{idx}/toggle — handled by catch-all or explicit
  // For simple PATCH /api/missions/{id}, forward body as-is

  const body = await req.json().catch(() => ({}));
  const res = await fetch(`${BACKEND_URL}/api/v1/missions/${id}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  const responseBody = await res.text();
  return new Response(responseBody, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function DELETE(req: Request, ctx: RouteContext) {
  const { id } = await ctx.params;
  const token = getAccessToken(req);
  if (!token) {
    return new Response(JSON.stringify({ error: "Not authenticated" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const res = await fetch(`${BACKEND_URL}/api/v1/missions/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });

  return new Response(null, { status: res.status });
}
