/**
 * Next.js API route for a single audio resource.
 *
 * Routes:
 *   GET    /api/audio/[id]   → GET    /api/v1/audio/{id}
 *   DELETE /api/audio/[id]   → DELETE /api/v1/audio/{id}
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

    const res = await fetch(`${BACKEND_URL}/api/v1/audio/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
    });

    const body = await res.text();
    return new Response(body, {
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

    const res = await fetch(`${BACKEND_URL}/api/v1/audio/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
    });

    return new Response(null, { status: res.status });
}
