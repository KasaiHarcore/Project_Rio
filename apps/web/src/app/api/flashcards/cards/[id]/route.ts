/**
 * Proxy: single flashcard card.
 *   PATCH  /api/flashcards/cards/[id] → PATCH  /api/v1/flashcards/cards/{id}
 *   DELETE /api/flashcards/cards/[id] → DELETE /api/v1/flashcards/cards/{id}
 */

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

function getAccessToken(req: Request): string | null {
  const cookieHeader = req.headers.get("cookie") ?? "";
  const match = cookieHeader.match(/(?:^|; )access-token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

type RouteContext = { params: Promise<{ id: string }> };

export async function PATCH(req: Request, ctx: RouteContext) {
  const { id } = await ctx.params;
  const token = getAccessToken(req);
  if (!token) {
    return new Response(JSON.stringify({ error: "Not authenticated" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const body = await req.json();
  const res = await fetch(`${BACKEND_URL}/api/v1/flashcards/cards/${id}`, {
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

  const res = await fetch(`${BACKEND_URL}/api/v1/flashcards/cards/${id}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${token}` },
  });

  return new Response(null, { status: res.status });
}
