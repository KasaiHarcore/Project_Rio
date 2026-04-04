import { DefaultChatTransport } from 'ai'
import { useMissionStore } from '@/features/mission/store'
import { useSidebarStore } from '@/features/chat/store'
import { useSQLApprovalStore } from '@/features/chat/stores/sql-approval-store'
import { useNoteConfirmationStore } from '@/features/chat/stores/note-confirmation-store'
import { useEmotionalStore } from '@/features/emotional/store'
import { useNoteStore } from '@/features/notes/store'

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
        dispatchCustomEvents(forDispatch, threadId)

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
async function dispatchCustomEvents(stream: ReadableStream<Uint8Array>, threadId: string | null) {
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
            const { action: noteAction, notes, persisted_ids } = evt.data ?? {}
            const ids = Array.isArray(persisted_ids) ? persisted_ids : []
            const resolvedAction = noteAction ?? 'create'

            if (resolvedAction === 'delete') {
              // Remove deleted notes from sidebar and global store
              for (const nid of ids) {
                if (nid) {
                  useSidebarStore.getState().removeStickyNoteByDbId(String(nid))
                  useNoteStore.getState().removeNote(String(nid))
                }
              }
            } else if (resolvedAction === 'update') {
              // Refresh updated notes in sidebar feed
              if (Array.isArray(notes)) {
                for (let i = 0; i < notes.length; i++) {
                  const n = notes[i]
                  const dbId = ids[i] ?? n?.note_id ?? ''
                  if (!dbId) continue

                  // Update sticky note content if it exists in sidebar
                  if (n?.content) {
                    useSidebarStore.getState().updateStickyNoteByDbId(String(dbId), {
                      content: String(n.content),
                    })
                  }

                  // Update in global note store
                  const updatePatch: Partial<{ content: string; title: string }> = {}
                  if (n?.content) updatePatch.content = String(n.content)
                  if (n?.title) updatePatch.title = String(n.title)
                  if (Object.keys(updatePatch).length > 0) {
                    useNoteStore.getState().updateNote(String(dbId), updatePatch)
                  }

                  // If not already in sidebar, add it as a new sticky note
                  const existing = useSidebarStore.getState().stickyNotes.find(
                    (s) => s.dbId === String(dbId)
                  )
                  if (!existing) {
                    useSidebarStore.getState().addStickyNote({
                      content: n?.content ? String(n.content) : `Note updated (${dbId})`,
                      author: 'agent',
                      dbId: String(dbId),
                    })
                  }
                }
              }
            } else {
              // Create — add new sticky notes to sidebar feed
              if (Array.isArray(notes)) {
                for (let i = 0; i < notes.length; i++) {
                  const n = notes[i]
                  if (!n?.content) continue
                  const dbId = ids[i] ?? ''

                  useSidebarStore.getState().addStickyNote({
                    content: String(n.content),
                    author: 'agent',
                    dbId: dbId || undefined,
                  })

                  if (dbId) {
                    const now = new Date().toISOString()
                    const noteTitle = n.title ? String(n.title) : String(n.content).slice(0, 80)
                    useNoteStore.getState().addNote({
                      id: dbId,
                      title: noteTitle,
                      content: String(n.content),
                      blocks: [],
                      collectionIds: [],
                      isPinned: false,
                      isImportant: false,
                      author: 'agent',
                      createdAt: now,
                      updatedAt: now,
                      todos: Array.isArray(n.todos) ? n.todos : [],
                    })
                  }
                }
              }
            }
          } else if (type === 'data-run-started') {
            const d = evt.data ?? {}
            useSidebarStore.getState().addLogicEntry({
              title: 'Workflow started',
              detail: d.character ? `Agent: ${d.character}` : undefined,
              kind: 'info',
            })
          } else if (type === 'data-supervisor-decision') {
            const d = evt.data ?? {}
            const action = d.action ?? 'delegate'
            const worker = d.worker ?? ''
            const reasoning = d.reasoning ?? ''
            const confidence = typeof d.confidence === 'number' ? d.confidence : null
            const confStr = confidence !== null ? ` (${Math.round(confidence * 100)}%)` : ''

            useSidebarStore.getState().addLogicEntry({
              title: action === 'respond'
                ? 'Responding directly'
                : action === 'clarify'
                  ? 'Asking for clarification'
                  : `Routing → ${worker}`,
              detail: reasoning ? `${reasoning}${confStr}` : undefined,
              kind: 'decision',
            })
          } else if (type === 'data-worker-result') {
            const d = evt.data ?? {}
            const worker = d.worker ?? 'unknown'
            const success = d.success !== false
            useSidebarStore.getState().addLogicEntry({
              title: success ? `${worker} completed` : `${worker} failed`,
              detail: d.content_preview ? String(d.content_preview).slice(0, 200) : undefined,
              kind: 'tool-call',
            })
          } else if (type === 'data-planning') {
            const d = evt.data ?? {}
            const content = typeof d.content === 'string' ? d.content : ''
            if (content) {
              useSidebarStore.getState().addLogicEntry({
                title: 'Execution plan',
                detail: content.slice(0, 200),
                kind: 'thinking',
              })
            }
          } else if (type === 'data-artifact-result') {
            const d = evt.data ?? {}
            const artifacts = Array.isArray(d.artifacts) ? d.artifacts : []
            const ids = Array.isArray(d.persisted_ids) ? d.persisted_ids : []
            for (const art of artifacts) {
              if (art?.name) {
                useSidebarStore.getState().addWorkspaceFileFromArtifact({
                  id: art.id ?? ids[artifacts.indexOf(art)] ?? '',
                  name: art.name,
                  type: art.type ?? 'code',
                  version: art.version ?? 1,
                  content: art.content ?? '',
                })
              }
            }
            if (artifacts.length > 0) {
              useSidebarStore.getState().addLogicEntry({
                title: `${artifacts.length} artifact(s) created`,
                detail: artifacts.map((a: any) => a?.name).filter(Boolean).join(', '),
                kind: 'info',
              })
            }
          } else if (type === 'data-note-confirmation-request') {
            const d = evt.data ?? {}
            if (d.note_id && threadId) {
              useNoteConfirmationStore.getState().setPending(
                {
                  confirmation_type: d.confirmation_type ?? '',
                  note_id: d.note_id ?? '',
                  note_title: d.note_title ?? '',
                  action: d.action ?? 'delete',
                  update_type: d.update_type ?? null,
                  message: d.message ?? '',
                  options: Array.isArray(d.options) ? d.options : ['approve', 'reject'],
                },
                threadId,
              )
              useSidebarStore.getState().addLogicEntry({
                title: `Note ${d.action ?? 'action'} confirmation required`,
                detail: d.message || `"${d.note_title}"`,
                kind: 'decision',
              })
            }
          } else if (type === 'data-sql-approval-request') {
            const d = evt.data ?? {}
            if (d.request_id && threadId) {
              useSQLApprovalStore.getState().setPending(
                {
                  request_id: d.request_id,
                  sql: d.sql ?? '',
                  natural_query: d.natural_query ?? '',
                  operation_type: d.operation_type ?? '',
                  danger_level: d.danger_level ?? '',
                  affected_tables: Array.isArray(d.affected_tables) ? d.affected_tables : [],
                  estimated_rows_affected: d.estimated_rows_affected ?? null,
                  warnings: Array.isArray(d.warnings) ? d.warnings : [],
                  explanation: d.explanation ?? '',
                  message: d.message ?? '',
                },
                threadId,
              )
              useSidebarStore.getState().addLogicEntry({
                title: `SQL approval required (${d.danger_level ?? 'unknown'})`,
                detail: d.explanation || d.sql?.slice(0, 100) || undefined,
                kind: 'decision',
              })
            }
          } else if (type === 'data-stage-assessment') {
            const d = evt.data ?? {}
            useSidebarStore.getState().setSupportAssessment({
              currentStage: d.current_stage ?? null,
              primaryGoal: d.primary_goal ?? null,
              currentFriction: d.current_friction ?? null,
            })
            useSidebarStore.getState().addLogicEntry({
              title: d.current_stage
                ? `Stage: ${d.current_stage}`
                : 'Assessing situation',
              detail: d.primary_goal ?? undefined,
              kind: 'thinking',
            })
          } else if (type === 'data-intervention-decision') {
            const d = evt.data ?? {}
            useSidebarStore.getState().setSupportIntervention({
              intervention: d.intervention ?? null,
              reasoning: d.reasoning ?? null,
            })
            if (d.intervention) {
              useSidebarStore.getState().addLogicEntry({
                title: `Intervention: ${d.intervention.replace(/_/g, ' ')}`,
                detail: d.reasoning ?? undefined,
                kind: 'decision',
              })
            }
          } else if (type === 'data-next-step') {
            const d = evt.data ?? {}
            useSidebarStore.getState().setSupportNextStep(
              d.recommended_next_step ?? null
            )
          } else if (type === 'data-emotional-update') {
            const d = evt.data ?? {}
            if (d.mood) {
              useEmotionalStore.getState().applyUpdate({
                mood: d.mood,
                energy: d.energy ?? 1.0,
                affinity: d.affinity ?? 0,
                relationship_tier: d.relationship_tier ?? 'stranger',
                mood_changed: d.mood_changed ?? false,
                streak_days: d.streak_days,
                interaction_count: d.interaction_count,
              })
            }
          } else if (type === 'data-contextual-notes') {
            const { notes } = evt.data ?? {}
            if (Array.isArray(notes) && notes.length > 0) {
              useSidebarStore.getState().setContextualNotes(notes)
            }
          } else if (type === 'data-final') {
            const d = evt.data ?? {}
            const timing = d.timing ?? {}
            const iterations = d.iterations ?? 0
            const parts: string[] = []
            if (iterations > 0) parts.push(`${iterations} iteration(s)`)
            const totalMs = timing.total_ms
            if (typeof totalMs === 'number') parts.push(`${(totalMs / 1000).toFixed(1)}s`)

            useSidebarStore.getState().addLogicEntry({
              title: 'Workflow complete',
              detail: parts.length > 0 ? parts.join(' · ') : undefined,
              kind: 'info',
            })
          } else if (type === 'error') {
            useSidebarStore.getState().addLogicEntry({
              title: 'Error',
              detail: typeof evt.errorText === 'string' ? evt.errorText : 'Unknown error',
              kind: 'info',
            })
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
