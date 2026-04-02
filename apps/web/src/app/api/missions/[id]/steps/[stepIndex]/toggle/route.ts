/**
 * Next.js API route for toggling a mission step.
 *
 * PATCH /api/missions/[id]/steps/[stepIndex]/toggle
 *   → PATCH /api/v1/missions/{id}/steps/{stepIndex}/toggle
 */

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

function getAccessToken(req: Request): string | null {
  const cookieHeader = req.headers.get("cookie") ?? "";
  const match = cookieHeader.match(/(?:^|; )access-token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

type RouteContext = { params: Promise<{ id: string; stepIndex: string }> };

export async function PATCH(req: Request, ctx: RouteContext) {
  const { id, stepIndex } = await ctx.params;
  const token = getAccessToken(req);
  if (!token) {
    return new Response(JSON.stringify({ error: "Not authenticated" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const res = await fetch(
    `${BACKEND_URL}/api/v1/missions/${id}/steps/${stepIndex}/toggle`,
    {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` },
    },
  );

  const body = await res.text();
  return new Response(body, {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
