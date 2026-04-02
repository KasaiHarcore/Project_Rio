/**
 * Next.js API route that streams audio from the backend.
 *
 * Routes:
 *   GET /api/audio/[id]/stream → GET /api/v1/audio/{id}/stream
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

    const backendRes = await fetch(`${BACKEND_URL}/api/v1/audio/${id}/stream`, {
        headers: { Authorization: `Bearer ${token}` },
    });

    return new Response(backendRes.body, {
        status: backendRes.status,
        headers: {
            "Content-Type": backendRes.headers.get("Content-Type") ?? "application/octet-stream",
            "Content-Disposition": backendRes.headers.get("Content-Disposition") ?? "",
        },
    });
}
