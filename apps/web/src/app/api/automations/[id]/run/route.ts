/**
 * Next.js API route to trigger an automation run.
 *
 * Routes:
 *   POST /api/automations/[id]/run → POST /api/v1/automations/{id}/run
 */

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

function getAccessToken(req: Request): string | null {
    const cookieHeader = req.headers.get("cookie") ?? "";
    const match = cookieHeader.match(/(?:^|; )access-token=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : null;
}

type RouteContext = { params: Promise<{ id: string }> };

export async function POST(req: Request, ctx: RouteContext) {
    const { id } = await ctx.params;
    const token = getAccessToken(req);
    if (!token) {
        return new Response(JSON.stringify({ error: "Not authenticated" }), {
            status: 401,
            headers: { "Content-Type": "application/json" },
        });
    }

    const res = await fetch(`${BACKEND_URL}/api/v1/automations/${id}/run`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
    });

    const responseBody = await res.text();
    return new Response(responseBody, {
        status: res.status,
        headers: { "Content-Type": "application/json" },
    });
}
