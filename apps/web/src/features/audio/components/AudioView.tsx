"use client"

import React, { useState, useEffect, useCallback } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { Headphones, Plus, Trash2, Clock, Loader2, AlertCircle, Check, FileText } from 'lucide-react'
import { cn } from "@/shared/lib/utils"
import { toast } from "@/shared/hooks/use-toast"
import { useAudioStore } from '@/features/audio/store'
import type { AudioGenerateRequest } from '@/features/audio/api'
import { apiListNotes } from '@/features/notes/api'
import { apiListDecks, apiListCards } from '@/features/flashcards/api'

/* ── Types ── */

interface SourceItem {
  id: string
  label: string
}

/* ── Helpers ── */

function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return '--:--'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

const statusColors: Record<string, string> = {
  pending: 'bg-amber-900/30 text-amber-400',
  generating: 'bg-blue-900/30 text-blue-400',
  ready: 'bg-emerald-900/30 text-emerald-400',
  failed: 'bg-red-900/30 text-red-400',
}

/* ── Source Picker ── */

interface SourcePickerProps {
  sourceType: string
  selectedIds: string[]
  onToggle: (id: string) => void
  items: SourceItem[]
  loading: boolean
}

function SourcePicker({ sourceType, selectedIds, onToggle, items, loading }: SourcePickerProps) {
  const label = sourceType === 'notes' ? 'Notes' : 'Flashcard Decks'

  return (
    <div>
      <label className="text-[10px] font-bold tracking-wider uppercase text-page-muted mb-1 block">
        {label} {selectedIds.length > 0 && <span className="text-[var(--primary)]">({selectedIds.length} selected)</span>}
      </label>
      <div className="border border-[var(--card-border)] rounded-lg overflow-hidden">
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-6 text-sm text-page-muted">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading…
          </div>
        ) : items.length === 0 ? (
          <p className="py-6 text-center text-sm text-page-muted">
            No {label.toLowerCase()} found.
          </p>
        ) : (
          <ul className="max-h-48 overflow-y-auto divide-y divide-[var(--card-border)]">
            {items.map((item) => {
              const selected = selectedIds.includes(item.id)
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onToggle(item.id)}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2.5 text-left text-sm transition-colors hover:bg-white/5",
                      selected && "bg-violet-900/20"
                    )}
                  >
                    <span className={cn(
                      "flex h-4 w-4 flex-shrink-0 items-center justify-center rounded border transition-colors",
                      selected
                        ? "border-violet-500 bg-violet-600"
                        : "border-[var(--card-border)]"
                    )}>
                      {selected && <Check className="h-3 w-3 text-white" />}
                    </span>
                    <span className="truncate text-page-card-title">{item.label || 'Untitled'}</span>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}

/* ── Main Component ── */

export function AudioView() {
  const {
    overviews, loading, generating,
    fetchOverviews, generateAudio, deleteOverview,
  } = useAudioStore()

  // Form state
  const [showGenerate, setShowGenerate] = useState(false)
  const [formSourceType, setFormSourceType] = useState('notes')
  const [formFormat, setFormFormat] = useState('summary')
  const [formTitle, setFormTitle] = useState('')
  const [selectedIds, setSelectedIds] = useState<string[]>([])

  // Source picker data
  const [sourceItems, setSourceItems] = useState<SourceItem[]>([])
  const [loadingSources, setLoadingSources] = useState(false)

  // Misc UI
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  useEffect(() => {
    fetchOverviews()
  }, [fetchOverviews])

  // Fetch source items when source type changes or the form opens
  const fetchSources = useCallback(async (type: string) => {
    setLoadingSources(true)
    setSelectedIds([])
    try {
      if (type === 'notes') {
        const notes = await apiListNotes()
        setSourceItems(notes.map((n) => ({ id: n.id, label: n.title || 'Untitled' })))
      } else if (type === 'flashcards') {
        const decks = await apiListDecks()
        setSourceItems(decks.map((d) => ({ id: d.id, label: d.name })))
      }
    } catch {
      setSourceItems([])
    } finally {
      setLoadingSources(false)
    }
  }, [])

  useEffect(() => {
    if (showGenerate) {
      fetchSources(formSourceType)
    }
  }, [showGenerate, formSourceType, fetchSources])

  const handleSourceTypeChange = (type: string) => {
    setFormSourceType(type)
    setSelectedIds([])
    setSourceItems([])
  }

  const toggleSource = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  const resetForm = () => {
    setFormSourceType('notes')
    setFormFormat('summary')
    setFormTitle('')
    setSelectedIds([])
    setSourceItems([])
  }

  const handleGenerate = async () => {
    if (selectedIds.length === 0) {
      toast({ title: 'No source selected', description: 'Pick at least one item.', variant: 'warning' })
      return
    }

    let sourceIds = selectedIds

    // For flashcards, expand deck IDs → card IDs
    if (formSourceType === 'flashcards') {
      try {
        const cardGroups = await Promise.all(selectedIds.map((id) => apiListCards(id, 200)))
        sourceIds = cardGroups.flat().map((c) => c.id)
        if (sourceIds.length === 0) {
          toast({ title: 'Empty decks', description: 'Selected decks have no cards.', variant: 'warning' })
          return
        }
      } catch {
        toast({ title: 'Failed to load cards', variant: 'error' })
        return
      }
    }

    const data: AudioGenerateRequest = {
      source_ids: sourceIds,
      source_type: formSourceType,
      format: formFormat,
      title: formTitle.trim() || undefined,
    }

    const result = await generateAudio(data)

    if (result) {
      toast({ title: 'Audio generation started', description: `"${result.title}" is being generated.`, variant: 'success' })
      resetForm()
      setShowGenerate(false)
    } else {
      toast({ title: 'Failed to start generation', variant: 'error' })
    }
  }

  const handleDelete = async (id: string, title: string) => {
    if (deleteConfirm !== id) {
      setDeleteConfirm(id)
      return
    }

    setDeleteConfirm(null)
    const ok = await deleteOverview(id)
    if (ok) {
      toast({ title: 'Audio deleted', description: `"${title}" removed.`, variant: 'success' })
    } else {
      toast({ title: 'Failed to delete', variant: 'error' })
    }
  }

  return (
    <DashboardLayout>
      <PageTransition className="flex-1 flex flex-col overflow-hidden bg-[var(--page-bg)]">
        {/* Header */}
        <header className="relative flex h-16 items-center justify-between border-b px-8 backdrop-blur-md flex-shrink-0 border-[var(--page-header-border)] bg-[var(--page-header-bg)]">
          <div className="absolute bottom-0 left-0 h-[1px] w-full opacity-50 bg-gradient-to-r from-transparent via-[var(--page-header-line)] to-transparent" />

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-xl shadow-lg",
                  "bg-gradient-to-br from-violet-700 to-violet-900"
                )}
                style={{ boxShadow: '0 10px 15px -3px var(--page-icon-shadow)' }}
              >
                <Headphones className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-black text-page-title">Audio Overviews</h1>
                <p className="text-[10px] font-bold tracking-wider uppercase text-page-subtitle">Generated Audio</p>
              </div>
            </div>
          </div>

          <button
            onClick={() => setShowGenerate(!showGenerate)}
            className="bg-[var(--primary)] text-white rounded-lg px-4 py-2 text-sm font-medium hover:opacity-90 flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Generate
          </button>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 lg:p-8">
          {/* Generate Form */}
          {showGenerate && (
            <div className="mb-8 rounded-2xl border p-6 bg-[var(--card-bg)] border-[var(--card-border)]">
              <h2 className="text-sm font-bold text-page-card-title mb-4">Generate Audio Overview</h2>

              <div className="grid gap-4 md:grid-cols-2">
                {/* Title */}
                <div>
                  <label className="text-[10px] font-bold tracking-wider uppercase text-page-muted mb-1 block">Title (optional)</label>
                  <input
                    value={formTitle}
                    onChange={(e) => setFormTitle(e.target.value)}
                    placeholder="My audio overview…"
                    className="w-full bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                  />
                </div>

                {/* Source Type */}
                <div>
                  <label className="text-[10px] font-bold tracking-wider uppercase text-page-muted mb-1 block">Source Type</label>
                  <select
                    value={formSourceType}
                    onChange={(e) => handleSourceTypeChange(e.target.value)}
                    className="w-full bg-[#161b22] border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                  >
                    <option className="bg-[#161b22] text-[#e6edf3]" value="notes">Notes</option>
                    <option className="bg-[#161b22] text-[#e6edf3]" value="flashcards">Flashcard Decks</option>
                  </select>
                </div>

                {/* Format */}
                <div>
                  <label className="text-[10px] font-bold tracking-wider uppercase text-page-muted mb-1 block">Format</label>
                  <select
                    value={formFormat}
                    onChange={(e) => setFormFormat(e.target.value)}
                    className="w-full bg-[#161b22] border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                  >
                    <option className="bg-[#161b22] text-[#e6edf3]" value="summary">Summary</option>
                    <option className="bg-[#161b22] text-[#e6edf3]" value="dialogue">Dialogue</option>
                    <option className="bg-[#161b22] text-[#e6edf3]" value="lecture">Lecture</option>
                  </select>
                </div>
              </div>

              {/* Source Picker */}
              <div className="mt-4">
                <SourcePicker
                  sourceType={formSourceType}
                  selectedIds={selectedIds}
                  onToggle={toggleSource}
                  items={sourceItems}
                  loading={loadingSources}
                />
              </div>

              {/* Submit */}
              <div className="mt-5 flex items-center gap-3">
                <button
                  onClick={handleGenerate}
                  disabled={generating || selectedIds.length === 0}
                  className="bg-[var(--primary)] text-white rounded-lg px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
                >
                  {generating && <Loader2 className="h-4 w-4 animate-spin" />}
                  Generate Audio
                </button>
                <button
                  onClick={() => { setShowGenerate(false); resetForm() }}
                  className="text-muted-foreground hover:text-foreground hover:bg-white/5 rounded-lg px-3 py-2 text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="mb-8 grid gap-4 md:grid-cols-4">
            {[
              { label: 'Total Overviews', value: overviews.length, color: 'from-violet-500 to-violet-700' },
              { label: 'Ready', value: overviews.filter((o) => o.status === 'ready').length, color: 'from-emerald-500 to-emerald-700' },
              { label: 'Generating', value: overviews.filter((o) => o.status === 'generating' || o.status === 'pending').length, color: 'from-blue-500 to-blue-700' },
              { label: 'Failed', value: overviews.filter((o) => o.status === 'failed').length, color: 'from-red-500 to-red-700' },
            ].map((stat, i) => (
              <div key={i} className="relative overflow-hidden rounded-2xl border p-5 shadow-sm bg-[var(--card-bg)] border-[var(--card-border)]">
                <div className={`absolute top-0 left-0 h-1 w-full bg-gradient-to-r ${stat.color}`} />
                <p className="text-2xl font-black text-page-card-title">{stat.value}</p>
                <p className="text-[10px] font-bold tracking-wider text-page-muted uppercase">{stat.label}</p>
              </div>
            ))}
          </div>

          {/* List Header */}
          <div className="mb-4">
            <h2 className="text-[10px] font-black tracking-widest uppercase text-page-section-label">
              {loading ? 'Loading…' : `Audio Overviews (${overviews.length})`}
            </h2>
          </div>

          {/* Audio Cards */}
          {overviews.length === 0 && !loading ? (
            <div className="text-center py-12">
              <Headphones className="mx-auto h-12 w-12 text-page-muted mb-4 opacity-60" />
              <p className="text-page-muted">No audio overviews yet</p>
              <p className="text-sm text-page-muted mt-1">Generate audio summaries from your notes or flashcard decks.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {overviews.map((overview) => (
                <div
                  key={overview.id}
                  className="group relative rounded-2xl border p-5 shadow-sm backdrop-blur-sm transition-all hover:shadow-md bg-[var(--card-bg)] border-[var(--card-border)] hover:border-violet-700/40"
                >
                  <div className="flex items-start gap-4">
                    {/* Icon */}
                    <div className={cn(
                      "rounded-xl p-3 transition-transform group-hover:scale-110",
                      statusColors[overview.status] || 'bg-slate-800/40 text-slate-500'
                    )}>
                      {overview.status === 'generating' || overview.status === 'pending'
                        ? <Loader2 className="h-6 w-6 animate-spin" />
                        : overview.status === 'failed'
                        ? <AlertCircle className="h-6 w-6" />
                        : <Headphones className="h-6 w-6" />
                      }
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="font-bold text-page-card-title">{overview.title}</h3>
                        <span className={cn(
                          "rounded px-2 py-0.5 text-[9px] font-bold uppercase",
                          statusColors[overview.status] || 'bg-slate-800 text-slate-500'
                        )}>
                          {overview.status}
                        </span>
                        <span className="rounded px-2 py-0.5 text-[9px] font-bold uppercase bg-slate-800 text-slate-400">
                          {overview.format}
                        </span>
                        {overview.duration_seconds !== null && (
                          <span className="rounded px-2 py-0.5 text-[9px] font-bold uppercase bg-slate-800 text-slate-400">
                            {formatDuration(overview.duration_seconds)}
                          </span>
                        )}
                      </div>

                      {/* Meta */}
                      <div className="flex flex-wrap items-center gap-4 text-[10px] text-slate-400 mb-2">
                        <span className="flex items-center gap-1">
                          Source: {overview.source_type}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(overview.created_at).toLocaleString()}
                        </span>
                      </div>

                      {/* Audio Player for ready */}
                      {overview.status === 'ready' && (
                        <audio
                          controls
                          src={'/api/audio/' + overview.id + '/stream'}
                          className="w-full mt-2"
                        />
                      )}

                      {/* Transcript (expandable) */}
                      {overview.status === 'ready' && overview.transcript && (
                        <details className="mt-3">
                          <summary className="flex items-center gap-1.5 text-[10px] font-bold tracking-wider uppercase text-slate-400 cursor-pointer hover:text-slate-300 select-none">
                            <FileText className="h-3 w-3" />
                            View Transcript
                          </summary>
                          <p className="mt-2 text-xs text-slate-400 whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto border border-[var(--card-border)] rounded-lg p-3">
                            {overview.transcript}
                          </p>
                        </details>
                      )}

                      {/* Error message for failed */}
                      {overview.status === 'failed' && overview.error_message && (
                        <div className="mt-2 rounded-lg border border-red-900/30 bg-red-900/10 px-3 py-2 text-xs text-red-400">
                          <span className="font-bold">Error:</span> {overview.error_message}
                        </div>
                      )}
                    </div>

                    {/* Delete */}
                    <button
                      onClick={() => handleDelete(overview.id, overview.title)}
                      className={cn(
                        "flex items-center justify-center rounded-lg border p-2.5 transition-colors",
                        deleteConfirm === overview.id
                          ? "border-red-500 bg-red-900/40 text-red-300"
                          : "border-red-900/50 bg-red-900/20 text-red-400 hover:bg-red-900/40"
                      )}
                      title={deleteConfirm === overview.id ? 'Click again to confirm' : 'Delete'}
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </PageTransition>
    </DashboardLayout>
  )
}
