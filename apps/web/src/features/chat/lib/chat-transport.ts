import { DefaultChatTransport } from 'ai'
import { useMissionStore } from '@/features/mission/store'
import { useSidebarStore } from '@/features/chat/store'

/**
 * Creates a custom transport for the AI SDK useChat hook that:
 * - Sends the body fields from the resolver to the /api/chat endpoint
 * - Captures the thread_id from the streamed response via X-Thread-Id header
 * - Intercepts mission & note SSE events and dispatches to stores
 *
 * The captured thread ID is delivered via the `onThreadId` callback instead of
 * module-level mutable state — this prevents cross-session contamination when
 * multiple MissionControl instances exist or the user switches threads rapidly.
 */
export function createSidebarTransport(
  bodyResolver: () => Record<string, unknown>,
  onThreadId: (id: string) => void,
) {
  return new DefaultChatTransport({
    api: '/api/chat',
    body: bodyResolver,
    fetch: async (input, init) => {
      const response = await fetch(input, init)

      const threadId = response.headers.get('x-thread-id')
      if (threadId) {
        onThreadId(threadId)
      }

      // Intercept SSE stream to dispatch mission events to stores.
      // We tee the body so the AI SDK still processes the full stream.
      if (response.body) {
        const [forAiSdk, forDispatch] = response.body.tee()

        // Process the dispatch branch in the background
        dispatchCustomEvents(forDispatch)

        // Return a cloned response with the AI SDK branch
        return new Response(forAiSdk, {
          status: response.status,
          statusText: response.statusText,
          headers: response.headers,
        })
      }

      return response
    },
  })
}

/**
 * Read a ReadableStream of SSE events and dispatch mission/note events
 * to the relevant Zustand stores.
 */
async function dispatchCustomEvents(stream: ReadableStream<Uint8Array>) {
  const reader = stream.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // Process complete SSE lines (terminated by \n\n)
      const parts = buffer.split('\n\n')
      // Keep the last incomplete part in the buffer
      buffer = parts.pop() ?? ''

      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data: ')) continue
        const payload = line.slice(6) // strip "data: "
        if (payload === '[DONE]') continue

        try {
          const evt = JSON.parse(payload)
          const type = evt?.type as string | undefined
          if (!type) continue

          if (type === 'data-mission-result') {
            const { missions, persisted_ids } = evt.data ?? {}
            if (Array.isArray(missions) && missions.length) {
              useMissionStore.getState().addAgentMissions(missions, persisted_ids)
            }
          } else if (type === 'data-mission-action') {
            const { action, mission, step_index } = evt.data ?? {}
            if (action && mission) {
              useMissionStore.getState().applyAgentAction(action, mission, step_index)
            }
          } else if (type === 'data-note-result') {
            const { notes } = evt.data ?? {}
            if (Array.isArray(notes)) {
              for (const n of notes) {
                if (n?.content) {
                  useSidebarStore.getState().addStickyNote({
                    content: String(n.content),
                    author: 'agent',
                  })
                }
              }
            }
          }
        } catch {
          // Ignore parse errors — non-JSON or partial frames
        }
      }
    }
  } catch {
    // Stream cancelled or errored — safe to ignore
  } finally {
    reader.releaseLock()
  }
}
