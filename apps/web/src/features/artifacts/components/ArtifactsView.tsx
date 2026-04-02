"use client"

import React, { Suspense, useState, useEffect } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { FileCode, FileText, Image, Download, Eye, Trash2, Clock, Sparkles, X, Link2 } from 'lucide-react'
import { cn } from "@/shared/lib/utils"
import { useArtifactStore, type ArtifactRecord } from '@/features/artifacts/store'
import { useSearchParams } from 'next/navigation'

const typeIcons: Record<string, React.ComponentType<Record<string, unknown>>> = {
  code: FileCode,
  document: FileText,
  image: Image,
  data: FileCode,
}

const typeColors: Record<string, string> = {
  code: 'bg-emerald-900/20 text-emerald-400',
  document: 'bg-blue-900/20 text-blue-400',
  image: 'bg-purple-900/20 text-purple-400',
  data: 'bg-amber-900/20 text-amber-400',
}

export function ArtifactsView() {
  return (
    <Suspense>
      <ArtifactsContent />
    </Suspense>
  )
}

function ArtifactsContent() {
  const searchParams = useSearchParams()
  const focusId = searchParams.get('id')

  const { artifacts, loading, fetchArtifacts, deleteArtifact } = useArtifactStore()
  const [filter, setFilter] = useState<'all' | 'code' | 'document' | 'image' | 'data'>('all')
  const [selectedArtifact, setSelectedArtifact] = useState<ArtifactRecord | null>(null)

  useEffect(() => {
    fetchArtifacts()
  }, [fetchArtifacts])

  useEffect(() => {
    if (focusId && artifacts.length > 0) {
      const found = artifacts.find((a) => a.id === focusId)
      if (found) setSelectedArtifact(found)
    }
  }, [focusId, artifacts])

  const filteredArtifacts = filter === 'all'
    ? artifacts
    : artifacts.filter(a => a.artifact_type === filter)

  const handleDelete = async (id: string) => {
    await deleteArtifact(id)
    if (selectedArtifact?.id === id) setSelectedArtifact(null)
  }

  const handleDownload = async (artifact: ArtifactRecord) => {
    try {
      const res = await fetch(`/api/artifacts/${artifact.id}/download`)
      if (!res.ok) return
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = artifact.name
      a.click()
      URL.revokeObjectURL(url)
    } catch { /* ignore */ }
  }

  return (
    <DashboardLayout>
      <PageTransition className="flex-1 flex flex-col overflow-hidden bg-[var(--page-bg)]">
        {/* Header */}
        <header className="relative flex h-16 items-center justify-between border-b px-8 backdrop-blur-md flex-shrink-0 border-[var(--page-header-border)] bg-[var(--page-header-bg)]">
          <div className="absolute bottom-0 left-0 h-[1px] w-full opacity-50 bg-gradient-to-r from-transparent via-[var(--page-header-line)] to-transparent"></div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-xl shadow-lg",
                  "bg-gradient-to-br from-purple-800 to-purple-900"
              )} style={{ boxShadow: `0 10px 15px -3px var(--page-icon-shadow)` }}>
                <Sparkles className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-black text-page-title">Artifacts</h1>
                <p className="text-[10px] font-bold tracking-wider uppercase text-page-subtitle">Generated Content</p>
              </div>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center gap-2">
            {(['all', 'code', 'document', 'image', 'data'] as const).map((type) => (
              <button
                key={type}
                onClick={() => setFilter(type)}
                className={cn(
                    "px-4 py-2 rounded-xl text-[10px] font-bold tracking-wider uppercase transition-all",
                    filter === type
                        ? "bg-gradient-to-r from-rose-600 to-red-500 text-white shadow-lg shadow-rose-900/20"
                        : "border border-rose-900/30 bg-[#0d1117]/60 text-slate-500 hover:bg-[#0d1117] hover:text-rose-400"
                )}
              >
                {type}
              </button>
            ))}
          </div>
        </header>

        {/* Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Artifact List */}
          <div className={cn("flex-1 overflow-y-auto p-6 lg:p-8", selectedArtifact && "lg:w-1/2")}>
            {/* Stats */}
            <div className="mb-8 grid gap-4 md:grid-cols-4">
              {[
                { label: 'Total Artifacts', value: artifacts.length, color: 'from-blue-500 to-blue-700' },
                { label: 'Code Files', value: artifacts.filter(a => a.artifact_type === 'code').length, color: 'from-emerald-500 to-emerald-700' },
                { label: 'Documents', value: artifacts.filter(a => a.artifact_type === 'document').length, color: 'from-purple-500 to-purple-700' },
                { label: 'Data Files', value: artifacts.filter(a => a.artifact_type === 'data').length, color: 'from-amber-500 to-amber-700' },
              ].map((stat, i) => (
                <div key={i} className={cn("relative overflow-hidden rounded-2xl border p-5 shadow-sm", "bg-[#0d1117]/40 border-rose-900/30")}>
                  <div className={`absolute top-0 left-0 h-1 w-full bg-gradient-to-r ${stat.color}`}></div>
                  <p className="text-2xl font-black text-page-card-title">{stat.value}</p>
                  <p className="text-[10px] font-bold tracking-wider text-page-muted uppercase">{stat.label}</p>
                </div>
              ))}
            </div>

            {/* List Header */}
            <div className="mb-4">
              <h2 className="text-[10px] font-black tracking-widest uppercase text-page-section-label">
                {loading ? 'Loading...' : `Recent Artifacts (${filteredArtifacts.length})`}
              </h2>
            </div>

            {filteredArtifacts.length === 0 && !loading ? (
              <div className="text-center py-12">
                <Sparkles className="mx-auto h-12 w-12 text-page-muted mb-4 opacity-60" />
                <p className="text-page-muted">No artifacts found</p>
                <p className="text-sm text-page-muted mt-1">Artifacts will appear here when the AI generates code, documents, or data files during conversations.</p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredArtifacts.map((artifact) => {
                  const Icon: React.ComponentType<Record<string, unknown>> = typeIcons[artifact.artifact_type] ?? FileCode
                  const isSelected = selectedArtifact?.id === artifact.id

                  return (
                    <div
                      key={artifact.id}
                      className={cn(
                          "group relative rounded-2xl border p-5 shadow-sm backdrop-blur-sm transition-all hover:shadow-md cursor-pointer",
                          "bg-[#0d1117]/40 border-rose-900/20 hover:border-rose-700 hover:bg-[#0d1117]/80",
                          isSelected && "border-rose-500 bg-[#0d1117]/80",
                      )}
                      onClick={() => setSelectedArtifact(isSelected ? null : artifact)}
                    >
                      <div className="flex items-start gap-4">
                        {/* Icon */}
                        <div className={cn("rounded-xl p-3 transition-transform group-hover:scale-110", typeColors[artifact.artifact_type])}>
                          <Icon className="h-6 w-6" />
                        </div>

                        {/* Info */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-3 mb-1">
                            <h3 className="font-bold text-page-card-title">{artifact.name}</h3>
                            {artifact.language && (
                              <span className={cn("rounded px-2 py-0.5 text-[9px] font-bold uppercase", "bg-slate-800 text-slate-400")}>
                                {artifact.language}
                              </span>
                            )}
                            {artifact.version > 1 && (
                              <span className={cn("rounded px-2 py-0.5 text-[9px] font-bold", "bg-blue-900/30 text-blue-400")}>
                                v{artifact.version}
                              </span>
                            )}
                          </div>

                          {/* Preview */}
                          <pre className={cn("mt-2 rounded-xl p-3 text-xs font-mono overflow-hidden max-h-20", "bg-[#010409] text-slate-400 border border-slate-800")}>
                            {artifact.content.slice(0, 200)}
                          </pre>

                          {/* Meta */}
                          <div className="mt-3 flex items-center gap-4 text-[10px] text-slate-400">
                            <span className="flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {new Date(artifact.created_at).toLocaleString()}
                            </span>
                            {artifact.thread_id && (
                              <a
                                href={`/operation/${artifact.thread_id}`}
                                onClick={(e) => e.stopPropagation()}
                                className="flex items-center gap-1 hover:text-blue-400 transition-colors"
                              >
                                <Link2 className="h-3 w-3" />
                                Source Thread
                              </a>
                            )}
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={() => setSelectedArtifact(artifact)}
                            className={cn("flex items-center justify-center rounded-lg border p-2.5 transition-colors", "border-blue-900/50 bg-blue-900/20 text-blue-400 hover:bg-blue-900/40")}
                          >
                            <Eye className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDownload(artifact)}
                            className={cn("flex items-center justify-center rounded-lg border p-2.5 transition-colors", "border-emerald-900/50 bg-emerald-900/20 text-emerald-400 hover:bg-emerald-900/40")}
                          >
                            <Download className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(artifact.id)}
                            className={cn("flex items-center justify-center rounded-lg border p-2.5 transition-colors", "border-red-900/50 bg-red-900/20 text-red-400 hover:bg-red-900/40")}
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Detail Panel */}
          {selectedArtifact && (
            <div className={cn(
              "hidden lg:flex lg:w-1/2 flex-col border-l overflow-hidden",
              "border-rose-900/30 bg-[#0a0d14]"
            )}>
              {/* Detail Header */}
              <div className={cn("flex items-center justify-between px-6 py-4 border-b", "border-rose-900/30")}>
                <div>
                  <h3 className="font-bold text-lg text-page-title">{selectedArtifact.name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    {selectedArtifact.language && (
                      <span className={cn("rounded px-2 py-0.5 text-[9px] font-bold uppercase", "bg-slate-800 text-slate-400")}>
                        {selectedArtifact.language}
                      </span>
                    )}
                    <span className="text-[10px] text-page-muted">v{selectedArtifact.version}</span>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedArtifact(null)}
                  className={cn("rounded-lg p-2 transition-colors", "hover:bg-slate-800 text-slate-400")}
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Detail Content */}
              <div className="flex-1 overflow-y-auto p-6">
                <pre className={cn(
                  "rounded-xl p-4 text-xs font-mono overflow-x-auto whitespace-pre-wrap",
                  "bg-[#010409] text-slate-300 border border-slate-800"
                )}>
                  {selectedArtifact.content}
                </pre>
              </div>

              {/* Detail Footer */}
              <div className={cn("flex items-center gap-3 px-6 py-3 border-t", "border-rose-900/30")}>
                <button
                  onClick={() => handleDownload(selectedArtifact)}
                  className={cn("flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold transition-colors", "bg-emerald-900/30 text-emerald-400 hover:bg-emerald-900/50")}
                >
                  <Download className="h-3.5 w-3.5" />
                  Download
                </button>
                {selectedArtifact.thread_id && (
                  <a
                    href={`/operation/${selectedArtifact.thread_id}`}
                    className={cn("flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-bold transition-colors", "bg-blue-900/30 text-blue-400 hover:bg-blue-900/50")}
                  >
                    <Link2 className="h-3.5 w-3.5" />
                    Source Thread
                  </a>
                )}
              </div>
            </div>
          )}
        </div>
      </PageTransition>
    </DashboardLayout>
  )
}
