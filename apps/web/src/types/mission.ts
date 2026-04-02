/**
 * Mission types — shared type definitions for the mission system.
 *
 * These mirror the backend Pydantic schemas so the frontend can
 * work with strongly-typed mission objects.  Notion-style properties
 * include deadlines, time estimates, categories, and rich notes.
 */

export type MissionStatus = 'draft' | 'active' | 'completed' | 'archived'
export type MissionPriority = 'low' | 'normal' | 'critical'
export type MissionSource = 'agent' | 'user'

export interface MissionStep {
  text: string
  done: boolean
}

export interface Mission {
  id: string
  title: string
  description: string | null
  status: MissionStatus
  priority: MissionPriority
  source: MissionSource
  progress: number
  tags: string[]
  steps: MissionStep[]
  sort_order: number
  thread_id: string | null
  /* Notion-style scheduling */
  deadline: string | null
  scheduled_start: string | null
  estimated_minutes: number | null
  category: string | null
  notes: string | null
  /* Timestamps */
  created_at: string
  updated_at: string
}

export interface MissionStats {
  total: number
  active: number
  completed: number
  overdue: number
  categories: string[]
}

/** Priority badge config for UI rendering */
export const PRIORITY_CONFIG: Record<MissionPriority, { label: string; color: string; darkColor: string; accent: string }> = {
  low:      { label: 'LOW',      color: 'bg-slate-100 text-slate-500',   darkColor: 'bg-slate-800 text-slate-400',         accent: '#64748b' },
  normal:   { label: 'NORMAL',   color: 'bg-blue-100 text-blue-600',     darkColor: 'bg-blue-900/30 text-blue-400',        accent: '#3b82f6' },
  critical: { label: 'CRITICAL', color: 'bg-red-100 text-red-600',       darkColor: 'bg-red-900/30 text-red-400',          accent: '#ef4444' },
}

/** Status badge config for UI rendering */
export const STATUS_CONFIG: Record<MissionStatus, { label: string; color: string; darkColor: string; accent: string }> = {
  draft:     { label: 'DRAFT',     color: 'bg-slate-100 text-slate-500',       darkColor: 'bg-slate-800 text-slate-400',         accent: '#94a3b8' },
  active:    { label: 'ACTIVE',    color: 'bg-green-100 text-green-600',       darkColor: 'bg-green-900/30 text-green-400',      accent: '#22c55e' },
  completed: { label: 'DONE',      color: 'bg-emerald-100 text-emerald-700',   darkColor: 'bg-emerald-900/30 text-emerald-400',  accent: '#10b981' },
  archived:  { label: 'ARCHIVED',  color: 'bg-gray-100 text-gray-500',         darkColor: 'bg-gray-800 text-gray-500',           accent: '#6b7280' },
}

/* ── Helpers ──────────────────────────────────────────────────────── */

/** Parse a deadline string into a local-aware Date.
 *
 *  ISO date-only strings ("2025-03-25") are parsed by `new Date()` as UTC
 *  midnight, which in negative-UTC timezones displays as the previous day.
 *  This helper detects date-only strings and constructs the Date in local
 *  time so "March 25" always shows as "March 25" regardless of timezone. */
export function parseDeadline(deadline: string): Date {
  // Date-only: "2025-03-25" (10 chars, no 'T')
  if (/^\d{4}-\d{2}-\d{2}$/.test(deadline)) {
    const [y, m, d] = deadline.split('-').map(Number)
    return new Date(y, m - 1, d)
  }
  return new Date(deadline)
}

/** Check if a mission is overdue (deadline in the past, not completed/archived) */
export function isOverdue(m: Mission): boolean {
  if (!m.deadline) return false
  if (m.status === 'completed' || m.status === 'archived') return false
  return parseDeadline(m.deadline) < new Date()
}

/** Format a duration in minutes to human-readable */
export function formatDuration(minutes: number | null): string {
  if (!minutes) return ''
  if (minutes < 60) return `${minutes}m`
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `${h}h ${m}m` : `${h}h`
}

/** Format deadline relative to now, with the actual date always visible. */
export function formatDeadline(deadline: string | null): string {
  if (!deadline) return ''
  const d = parseDeadline(deadline)
  if (isNaN(d.getTime())) return ''
  const now = new Date()
  const diffMs = d.getTime() - now.getTime()
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24))

  const dateStr = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  if (diffDays < 0) return `${dateStr} (${Math.abs(diffDays)}d overdue)`
  if (diffDays === 0) return `${dateStr} (today)`
  if (diffDays === 1) return `${dateStr} (tomorrow)`
  if (diffDays <= 7) return `${dateStr} (${diffDays}d left)`
  return dateStr
}

/** Format deadline to local datetime-local input value (for inline editors). */
export function deadlineToInputValue(deadline: string | null): string {
  if (!deadline) return ''
  const d = parseDeadline(deadline)
  if (isNaN(d.getTime())) return ''
  // Build YYYY-MM-DDThh:mm in local time
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

/** Category color palette — cycles through a set of soft colors */
const CAT_COLORS = [
  { bg: 'bg-violet-100 dark:bg-violet-900/30', text: 'text-violet-600 dark:text-violet-400' },
  { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-600 dark:text-amber-400' },
  { bg: 'bg-cyan-100 dark:bg-cyan-900/30', text: 'text-cyan-600 dark:text-cyan-400' },
  { bg: 'bg-pink-100 dark:bg-pink-900/30', text: 'text-pink-600 dark:text-pink-400' },
  { bg: 'bg-lime-100 dark:bg-lime-900/30', text: 'text-lime-600 dark:text-lime-400' },
  { bg: 'bg-orange-100 dark:bg-orange-900/30', text: 'text-orange-600 dark:text-orange-400' },
]
export function getCategoryColor(category: string): { bg: string; text: string } {
  let hash = 0
  for (let i = 0; i < category.length; i++) hash = category.charCodeAt(i) + ((hash << 5) - hash)
  return CAT_COLORS[Math.abs(hash) % CAT_COLORS.length]
}
