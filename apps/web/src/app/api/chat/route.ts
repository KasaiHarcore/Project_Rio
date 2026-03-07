/**
 * Next.js API route that proxies chat requests to the FastAPI backend.
 *
 * The Vercel AI SDK `useChat` hook posts to `/api/chat` by default.
 * This route forwards the request to FastAPI `/api/v1/chat` with the
 * JWT access token read from the `access-token` cookie and streams
 * the response back to the client.
 *
 * The backend now emits the **AI SDK data-stream protocol** (v1):
 *   0:"text"  – text deltas
 *   2:[{…}]   – data annotations (sidebar events)
 *   d:{…}     – finish signal
 *
 * We forward the `X-Vercel-AI-Data-Stream: v1` header so that
 * `useChat({ streamProtocol: 'data' })` on the client can parse
 * both text and structured metadata from a single response.
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
  const dataStreamHeader = backendRes.headers.get("X-Vercel-AI-Data-Stream");

  // Pipe the streaming response through
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
