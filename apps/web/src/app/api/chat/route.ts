export const runtime = 'edge';

export async function POST(req: Request) {
  const { messages } = await req.json();
  const lastMessage = messages[messages.length - 1].content;

  const encoder = new TextEncoder();
  
  const stream = new ReadableStream({
    async start(controller) {
      const responseText = `**[SYSTEM SIMULATION]**\n\nI received your directive: _"${lastMessage}"_\n\nSince the neural link (backend) is offline, I am operating in **simulation mode**. Here is a projected outcome:\n\n1.  **Analysis**: Directive recognized.\n2.  **Action**: Retrieval of relevant artifacts.\n3.  **Result**: 3 items found.\n\n\`\`\`python\n# Projected Operation\ndef execute_directive():\n    return "Mission Accomplished"\n\`\`\``;
      
      const chunks = responseText.split(""); // Split by char for smooth typerwriter

      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
        await new Promise((resolve) => setTimeout(resolve, 15)); // Fast Typing effect
      }
      
      controller.close();
    },
  });

  return new Response(stream, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
