import type { LogicEntry } from '@/features/chat/store'
import type { MessageSource } from '@/features/chat/store'

/**
 * Mock / bridge-mode source synthesis.
 *
 * Until the backend emits a structured `source` SSE event, the tree view's
 * DetailPanel derives best-effort source cards from the `tool-call` logic
 * entries that fell inside the turn's time window. Web workers produce
 * link-preview placeholders; RAG / KB workers produce doc-attachment
 * placeholders. The goal is to preview the VISUAL, not represent real
 * citations — real unfurl data (og:image, filename, etc.) arrives once
 * the backend side of C4 lands.
 *
 * Drop this whole module once `messageSources[messageId]` is populated
 * from real backend events.
 */

const URL_PATTERN = /https?:\/\/[^\s)]+/i

const WEB_WORKERS = new Set(['web', 'search'])
const DOC_WORKERS = new Set(['rag', 'knowledge', 'kb', 'retrieval'])

function extractWorker(title: string): string | null {
  const match = title.match(/^([A-Za-z][\w-]*)\s+(completed|failed|started|running)?/)
  return match ? match[1].toLowerCase() : null
}

function firstUrl(text: string | undefined): string | null {
  if (!text) return null
  const match = text.match(URL_PATTERN)
  return match ? match[0] : null
}

function domainFrom(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, '') } catch { return url }
}

/**
 * Build placeholder WebSource / DocSource cards from tool-call entries.
 * Returns an empty array when none of the entries look like retrieval
 * events — the DetailPanel then omits the Sources section entirely.
 */
export function deriveMockSources(entries: readonly LogicEntry[]): MessageSource[] {
  const sources: MessageSource[] = []

  for (const entry of entries) {
    if (entry.kind !== 'tool-call') continue
    const worker = extractWorker(entry.title)
    if (!worker) continue

    if (WEB_WORKERS.has(worker)) {
      const url = firstUrl(entry.detail) ?? 'https://example.com'
      const snippet = entry.detail
        ? entry.detail.replace(URL_PATTERN, '').replace(/\s+/g, ' ').trim().slice(0, 180)
        : undefined
      sources.push({
        kind: 'web',
        url,
        title: entry.title.replace(/\s+(completed|failed|started|running)$/i, '').trim() || domainFrom(url),
        snippet: snippet || undefined,
        siteName: domainFrom(url),
        timestamp: entry.timestamp,
      })
      continue
    }

    if (DOC_WORKERS.has(worker)) {
      const excerpt = entry.detail?.trim()
      sources.push({
        kind: 'doc',
        filename: inferDocFilename(entry.title, worker),
        title: inferDocTitle(entry.title),
        excerpt: excerpt && excerpt.length > 0 ? excerpt : undefined,
        source: worker.toUpperCase(),
        timestamp: entry.timestamp,
      })
      continue
    }
  }

  return sources
}

function inferDocTitle(rawTitle: string): string {
  return rawTitle.replace(/\s+(completed|failed|started|running)$/i, '').trim() || 'Retrieved document'
}

function inferDocFilename(rawTitle: string, worker: string): string {
  const cleaned = inferDocTitle(rawTitle)
    .replace(/[^\w\s.-]+/g, '')
    .trim()
    .replace(/\s+/g, '_')
  return cleaned ? `${cleaned}.pdf` : `${worker}_result.pdf`
}
