"use client"

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { Upload, FileText, Search, Trash2, Eye, FolderOpen, Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import { cn } from "@/shared/lib/utils"
import {
  apiListDocuments,
  apiUploadDocument,
  apiDeleteDocument,
  DocumentRecord,
} from '@/features/knowledge/api'
import { useAffinityTracker } from '@/features/emotional/hooks/use-affinity-tracker'

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function KnowledgeView() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [isDragging, setIsDragging] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const { recordUpload } = useAffinityTracker()

  const fileInputRef = useRef<HTMLInputElement>(null)

  // ── Fetch documents ────────────────────────────────────────────────────
  const fetchDocuments = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiListDocuments(100)
      setDocuments(data.documents)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to load documents'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchDocuments() }, [fetchDocuments])

  // ── Upload handler ─────────────────────────────────────────────────────
  const handleFiles = async (files: FileList | File[]) => {
    const fileArr = Array.from(files)
    if (fileArr.length === 0) return

    setUploading(true)
    try {
      for (const file of fileArr) {
        await apiUploadDocument(file)
        recordUpload() // Award affinity for each document uploaded
      }
      await fetchDocuments()
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Upload failed'
      setError(msg)
    } finally {
      setUploading(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files.length) {
      handleFiles(e.dataTransfer.files)
    }
  }

  // ── Delete handler ─────────────────────────────────────────────────────
  const handleDelete = async (id: string) => {
    try {
      await apiDeleteDocument(id)
      setDocuments(prev => prev.filter(d => d.id !== id))
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Delete failed'
      setError(msg)
    }
  }

  const filteredDocs = documents.filter(doc =>
    doc.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

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
                  "bg-gradient-to-br from-rose-500 to-rose-600"
              )} style={{ boxShadow: `0 10px 15px -3px var(--page-icon-shadow)` }}>
                <FolderOpen className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-black text-page-title">Knowledge Base</h1>
                <p className="text-[10px] font-bold tracking-wider uppercase text-page-subtitle">Document Repository</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-page-muted" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-4 py-2 rounded-xl border text-sm outline-none transition-all w-64 bg-[var(--page-search-bg)] border-[var(--page-search-border)] text-[var(--page-search-text)] placeholder:text-[var(--page-search-placeholder)] focus:border-[var(--page-search-focus-border)] focus:ring-2 focus:ring-[var(--page-search-focus-ring)]"
              />
            </div>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 lg:p-8">
          {/* Upload Zone */}
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            className={cn(
                "relative mb-8 rounded-2xl border-2 border-dashed p-8 text-center transition-all",
                isDragging
                    ? 'border-rose-500 bg-rose-900/20'
                    : 'border-rose-900/30 bg-[#0d1117]/40 hover:border-rose-700 hover:bg-[#0d1117]/60'
            )}
          >
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".txt,.md,.pdf,.json,.csv,.html,.htm,.docx"
              className="hidden"
              onChange={(e) => e.target.files && handleFiles(e.target.files)}
            />
            <div className={cn(
                "mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl",
                "bg-gradient-to-br from-rose-900/40 to-rose-900/10"
            )}>
              {uploading ? (
                <Loader2 className="h-8 w-8 animate-spin text-page-loader" />
              ) : (
                <Upload className="h-8 w-8 text-page-accent" />
              )}
            </div>
            <h3 className="text-lg font-bold mb-2 text-page-card-title">
              {uploading ? 'Uploading & Processing…' : 'Upload Documents'}
            </h3>
            <p className="text-sm text-page-muted mb-4">Drag and drop files here, or click to browse</p>
            <button
              disabled={uploading}
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                "inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-bold text-white shadow-lg transition-all hover:scale-[1.02] active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed",
                "bg-gradient-to-r from-rose-600 to-red-500 shadow-rose-900/20"
            )}>
              <Upload className="h-4 w-4" />
              Select Files
            </button>
            <p className="mt-4 text-[10px] font-bold tracking-wider text-page-muted uppercase">
              Supports: PDF, TXT, MD, JSON, CSV, HTML, DOCX • Max 25MB per file
            </p>
          </div>

          {/* Error banner */}
          {error && (
            <div className="mb-4 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span className="flex-1">{error}</span>
              <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600 text-xs font-bold">Dismiss</button>
            </div>
          )}

          {/* Documents Grid */}
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-[10px] font-black tracking-widest uppercase text-page-section-label">
              Your Documents ({filteredDocs.length})
            </h2>
            <button onClick={fetchDocuments} className="text-page-muted hover:text-page-card-title transition-colors">
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            </button>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Loader2 className="h-8 w-8 animate-spin text-page-loader" />
            </div>
          ) : filteredDocs.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="mx-auto h-12 w-12 text-page-muted mb-4 opacity-60" />
              <p className="text-page-muted">No documents found</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredDocs.map((doc) => (
                <div
                  key={doc.id}
                  className={cn(
                      "group relative rounded-2xl border p-5 shadow-sm backdrop-blur-sm transition-all hover:shadow-md",
                      "bg-[#0d1117]/40 border-rose-900/20 hover:border-rose-700 hover:bg-[#0d1117]/80"
                  )}
                >
                  {/* Status indicator */}
                  <div className="absolute top-4 right-4">
                    {doc.status === 'ready' && (
                      <span className="flex h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span>
                    )}
                    {doc.status === 'processing' && (
                      <span className="flex h-2 w-2 rounded-full bg-amber-500 animate-pulse"></span>
                    )}
                    {doc.status === 'error' && (
                      <span className="flex h-2 w-2 rounded-full bg-red-500"></span>
                    )}
                  </div>

                  <div className="flex items-start gap-4">
                    <div className={cn(
                        "rounded-xl p-3 transition-transform group-hover:scale-110",
                        "bg-rose-900/20 text-rose-500"
                    )}>
                      <FileText className="h-6 w-6" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold truncate pr-4 text-page-card-title">{doc.name}</h3>
                      <p className="mt-1 text-[10px] font-bold tracking-wider text-page-muted uppercase">
                        {doc.file_type.toUpperCase()} • {formatFileSize(doc.size_bytes)}
                        {doc.status === 'ready' && ` • ${doc.chunk_count} chunks`}
                      </p>
                      <p className="mt-1 font-mono text-[9px] text-page-muted">
                        Uploaded: {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : '—'}
                      </p>
                      {doc.status === 'error' && doc.error_message && (
                        <p className="mt-1 text-[9px] text-red-400 truncate" title={doc.error_message}>
                          {doc.error_message}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className={cn(
                        "flex-1 flex items-center justify-center gap-1.5 rounded-lg border py-2 text-[10px] font-bold tracking-wider uppercase transition-colors",
                        "border-rose-900/50 bg-rose-900/20 text-rose-300 hover:bg-rose-900/40"
                    )}>
                      <Eye className="h-3 w-3" />
                      View
                    </button>
                    <button
                      onClick={() => handleDelete(doc.id)}
                      className="flex items-center justify-center rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-red-500 transition-colors hover:bg-red-100"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>

                  {/* Progress bar for processing */}
                  {doc.status === 'processing' && (
                    <div className={cn("absolute bottom-0 left-0 h-1 w-full overflow-hidden rounded-b-2xl", "bg-rose-900/30")}>
                      <div className={cn("h-full w-1/2 animate-pulse bg-gradient-to-r", "from-rose-500 to-rose-600")}></div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </PageTransition>
    </DashboardLayout>
  )
}
