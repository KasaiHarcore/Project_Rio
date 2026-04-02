/**
 * Next.js API route that proxies automation requests to the FastAPI backend.
 *
 * Routes:
 *   GET  /api/automations       → GET  /api/v1/automations
 *   POST /api/automations       → POST /api/v1/automations
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

    const { searchParams } = new URL(req.url);
    const qs = searchParams.toString();
    const url = `${BACKEND_URL}/api/v1/automations${qs ? `?${qs}` : ""}`;

    const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
    });

    const body = await res.text();
    return new Response(body, {
        status: res.status,
        headers: { "Content-Type": "application/json" },
    });
}

export async function POST(req: Request) {
    const token = getAccessToken(req);
    if (!token) {
        return new Response(JSON.stringify({ error: "Not authenticated" }), {
            status: 401,
            headers: { "Content-Type": "application/json" },
        });
    }

    const body = await req.json();
    const res = await fetch(`${BACKEND_URL}/api/v1/automations`, {
        method: "POST",
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
