/**
 * Next.js API route for downloading artifact content.
 *
 * Routes:
 *   GET /api/artifacts/:id/download → GET /api/v1/artifacts/:id/download
 */

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

function getAccessToken(req: Request): string | null {
  const cookieHeader = req.headers.get("cookie") ?? "";
  const match = cookieHeader.match(/(?:^|; )access-token=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const token = getAccessToken(req);
  if (!token) {
    return new Response(JSON.stringify({ error: "Not authenticated" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const res = await fetch(`${BACKEND_URL}/api/v1/artifacts/${id}/download`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  const body = await res.arrayBuffer();
  return new Response(body, {
    status: res.status,
    headers: {
      "Content-Type": res.headers.get("Content-Type") ?? "application/octet-stream",
      "Content-Disposition": res.headers.get("Content-Disposition") ?? `attachment; filename="artifact"`,
    },
  });
}
