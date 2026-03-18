/**
 * Next.js API route that proxies chat requests to the FastAPI backend.
 *
 * The Vercel AI SDK `useChat` hook posts to `/api/chat` by default.
 * This route forwards the request to FastAPI `/api/v1/chat` with the
 * JWT access token read from the `access-token` cookie and streams
 * the response back to the client.
 *
 * The backend emits **AI SDK v6 UIMessageStream** (Server-Sent Events):
 *   data: {"type":"text-delta","id":"...","delta":"..."}\n\n
 *   data: {"type":"finish","finishReason":"stop"}\n\n
 *   data: [DONE]\n\n
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

  // Forward to FastAPI backend
  const backendRes = await fetch(`${BACKEND_URL}/api/v1/chat`, {
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

  // Read forwarded headers from backend
  const threadId = backendRes.headers.get("X-Thread-Id");

  // Pipe the SSE streaming response through
  return new Response(backendRes.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache",
      "Connection": "keep-alive",
      ...(threadId ? { "X-Thread-Id": threadId } : {}),
    },
  });
}
