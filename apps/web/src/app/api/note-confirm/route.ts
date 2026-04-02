/**
 * Next.js API route that proxies note confirmation resume requests
 * to the FastAPI backend at POST /api/v1/note-confirmation/resume.
 *
 * Returns a streaming response using the AI SDK data-stream protocol
 * so the frontend can pipe tokens and events back into the chat.
 */

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function POST(req: Request) {
  const body = await req.json();
  const cookieHeader = req.headers.get("cookie") ?? "";

  // Extract the access-token from cookies
  const tokenMatch = cookieHeader.match(/(?:^|; )access-token=([^;]*)/);
  const accessToken = tokenMatch ? decodeURIComponent(tokenMatch[1]) : null;

  if (!accessToken) {
    return new Response(JSON.stringify({ error: "Not authenticated" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }

  const backendRes = await fetch(`${BACKEND_URL}/api/v1/note-confirmation/resume`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(body),
  });

  if (!backendRes.ok) {
    const errText = await backendRes.text().catch(() => "Backend error");
    return new Response(errText, {
      status: backendRes.status,
      headers: { "Content-Type": "text/plain; charset=utf-8" },
    });
  }

  const threadId = backendRes.headers.get("X-Thread-Id");
  const dataStreamHeader = backendRes.headers.get("X-Vercel-AI-Data-Stream");

  return new Response(backendRes.body, {
    status: 200,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "no-cache",
      "Transfer-Encoding": "chunked",
      ...(threadId ? { "X-Thread-Id": threadId } : {}),
      ...(dataStreamHeader ? { "X-Vercel-AI-Data-Stream": dataStreamHeader } : {}),
    },
  });
}
