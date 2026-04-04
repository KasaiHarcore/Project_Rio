/**
 * Mission types and UI helpers.
 *
 * These mirror the backend Pydantic schemas so the frontend can
 * work with strongly-typed mission objects.
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
  deadline: string | null
  scheduled_start: string | null
  estimated_minutes: number | null
  category: string | null
  notes: string | null
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

/* ── UI Config ───────────────────────────────────────────────────── */

export const PRIORITY_CONFIG: Record<MissionPriority, { label: string; color: string; darkColor: string; accent: string }> = {
  low:      { label: 'LOW',      color: 'bg-slate-100 text-slate-500',   darkColor: 'bg-slate-800 text-slate-400',         accent: '#64748b' },
  normal:   { label: 'NORMAL',   color: 'bg-blue-100 text-blue-600',     darkColor: 'bg-blue-900/30 text-blue-400',        accent: '#3b82f6' },
  critical: { label: 'CRITICAL', color: 'bg-red-100 text-red-600',       darkColor: 'bg-red-900/30 text-red-400',          accent: '#ef4444' },
}

export const STATUS_CONFIG: Record<MissionStatus, { label: string; color: string; darkColor: string; accent: string }> = {
  draft:     { label: 'DRAFT',     color: 'bg-slate-100 text-slate-500',       darkColor: 'bg-slate-800 text-slate-400',         accent: '#94a3b8' },
  active:    { label: 'ACTIVE',    color: 'bg-green-100 text-green-600',       darkColor: 'bg-green-900/30 text-green-400',      accent: '#22c55e' },
  completed: { label: 'DONE',      color: 'bg-emerald-100 text-emerald-700',   darkColor: 'bg-emerald-900/30 text-emerald-400',  accent: '#10b981' },
  archived:  { label: 'ARCHIVED',  color: 'bg-gray-100 text-gray-500',         darkColor: 'bg-gray-800 text-gray-500',           accent: '#6b7280' },
}

/* ── Helpers ──────────────────────────────────────────────────────── */

export function parseDeadline(deadline: string): Date {
  if (/^\d{4}-\d{2}-\d{2}$/.test(deadline)) {
    const [y, m, d] = deadline.split('-').map(Number)
    return new Date(y, m - 1, d)
  }
  return new Date(deadline)
}

export function isOverdue(m: Mission): boolean {
  if (!m.deadline) return false
  if (m.status === 'completed' || m.status === 'archived') return false
  return parseDeadline(m.deadline) < new Date()
}

export function formatDuration(minutes: number | null): string {
  if (!minutes) return ''
  if (minutes < 60) return `${minutes}m`
  const h = Math.floor(minutes / 60)
  const rem = minutes % 60
  return rem ? `${h}h ${rem}m` : `${h}h`
}

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

export function deadlineToInputValue(deadline: string | null): string {
  if (!deadline) return ''
  const d = parseDeadline(deadline)
  if (isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

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
