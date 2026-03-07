"use client"

import React, { useState, useRef, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { useSidebarStore, type WorkspaceFile, SIDEBAR_LIMITS } from '@/store/sidebar-store'
import { useUIStore, AgentMode } from '@/store/ui-store'
import { chunkFile } from '@/lib/code-chunker'
import {
  FolderOpen, FileCode2, FileText, Table2, Image, File,
  X, Plus, Search, Globe, Database, Sparkles, Download,
  ChevronDown, ChevronRight, ExternalLink, Trash2, Link2,
} from 'lucide-react'

/* ─── File type → icon mapping ───────────────────────────────────── */

const FILE_TYPE_ICONS: Record<WorkspaceFile['type'], React.ElementType> = {
  code: FileCode2,
  document: FileText,
  data: Table2,
  image: Image,
  other: File,
}

const FILE_TYPE_COLORS: Record<WorkspaceFile['type'], string> = {
  code: 'text-sky-400',
  document: 'text-amber-400',
  data: 'text-emerald-400',
  image: 'text-violet-400',
  other: 'text-slate-400',
}

/** Infer file type from extension */
function inferFileType(path: string): WorkspaceFile['type'] {
  const ext = path.split('.').pop()?.toLowerCase() ?? ''
  if (['ts', 'tsx', 'js', 'jsx', 'py', 'rs', 'go', 'java', 'c', 'cpp', 'css', 'html', 'vue', 'svelte'].includes(ext)) return 'code'
  if (['md', 'txt', 'pdf', 'doc', 'docx', 'rst'].includes(ext)) return 'document'
  if (['csv', 'json', 'sql', 'xlsx', 'parquet', 'yaml', 'yml', 'toml'].includes(ext)) return 'data'
  if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext)) return 'image'
  return 'other'
}

/** Extract filename from path */
function fileName(path: string): string {
  return path.split('/').pop() ?? path
}

/* ─── Source type config ─────────────────────────────────────────── */

const SOURCE_ICONS: Record<string, React.ElementType> = {
  rag: FileText,
  web: Globe,
  sql: Database,
  file: File,
}

const SOURCE_COLORS: Record<string, string> = {
  rag: 'text-amber-400',
  web: 'text-sky-400',
  sql: 'text-emerald-400',
  file: 'text-slate-400',
}

/* ═══════════════════════════════════════════════════════════════════ */

export function WorkspaceTab() {
  const workspaceFiles = useSidebarStore((s) => s.workspaceFiles)
  const addWorkspaceFile = useSidebarStore((s) => s.addWorkspaceFile)
  const removeWorkspaceFile = useSidebarStore((s) => s.removeWorkspaceFile)
  const clearWorkspaceFiles = useSidebarStore((s) => s.clearWorkspaceFiles)

  const searchReferences = useSidebarStore((s) => s.searchReferences)
  const removeSearchReference = useSidebarStore((s) => s.removeSearchReference)
  const clearSearchReferences = useSidebarStore((s) => s.clearSearchReferences)

  const agentMode = useUIStore((s) => s.agentMode)

  const setFileChunks = useSidebarStore((s) => s.setFileChunks)

  const [filesExpanded, setFilesExpanded] = useState(true)
  const [searchExpanded, setSearchExpanded] = useState(true)
  const [addFileOpen, setAddFileOpen] = useState(false)
  const [newFilePath, setNewFilePath] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-chunk artifact-backed files that have content but no chunks yet
  useEffect(() => {
    for (const file of workspaceFiles) {
      if (file.content && !file.chunks && file.artifactId) {
        const result = chunkFile(file.name, file.content)
        setFileChunks(file.id, result.chunks, result.fileTree, file.content)
      }
    }
  }, [workspaceFiles, setFileChunks])

  /* ── Add file handler ── */
  function handleAddFile() {
    if (!newFilePath.trim()) return
    const path = newFilePath.trim()
    addWorkspaceFile({
      name: fileName(path),
      path,
      type: inferFileType(path),
    })
    setNewFilePath('')
    setAddFileOpen(false)
  }

  return (
    <div className="space-y-0">
      {/* ───── Project Files ───── */}
      <div className="border-b border-[var(--chat-sidebar-section-border)]">
        <div
          onClick={() => setFilesExpanded(!filesExpanded)}
          className="flex w-full items-center justify-between p-4 pb-2 text-left cursor-pointer select-none"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setFilesExpanded(!filesExpanded) } }}
        >
          <div className="flex items-center gap-2">
            {filesExpanded ? <ChevronDown className="h-3 w-3 text-[var(--chat-sidebar-stat-label)]" /> : <ChevronRight className="h-3 w-3 text-[var(--chat-sidebar-stat-label)]" />}
            <h3 className="text-[10px] font-black tracking-[0.25em] uppercase text-[var(--chat-sidebar-heading)]">
              Files
            </h3>
            {workspaceFiles.length > 0 && (
              <span className="ml-1 rounded-full px-1.5 py-0.5 text-[8px] font-bold bg-sky-500/20 text-sky-400">
                {workspaceFiles.length}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            {workspaceFiles.length > 0 && (
              <button
                onClick={(e) => { e.stopPropagation(); clearWorkspaceFiles() }}
                className="rounded-md p-1 text-[var(--chat-sidebar-stat-label)] hover:text-red-400 transition-colors"
                title="Clear all files"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            )}
            <button
              onClick={(e) => {
                e.stopPropagation()
                if (workspaceFiles.length < SIDEBAR_LIMITS.WORKSPACE_FILES) {
                  setAddFileOpen(!addFileOpen)
                  setTimeout(() => inputRef.current?.focus(), 100)
                }
              }}
              className={cn(
                "rounded-md p-1 transition-colors hover:bg-[var(--chat-sidebar-artifact-bg)]",
                workspaceFiles.length >= SIDEBAR_LIMITS.WORKSPACE_FILES
                  ? "text-[var(--chat-sidebar-stat-label)]/30 cursor-not-allowed"
                  : "text-[var(--chat-sidebar-stat-label)] hover:text-[var(--chat-sidebar-stat-text)]"
              )}
              title={workspaceFiles.length >= SIDEBAR_LIMITS.WORKSPACE_FILES ? `Max ${SIDEBAR_LIMITS.WORKSPACE_FILES} files` : 'Add file'}
            >
              <Plus className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {filesExpanded && (
          <div className="px-4 pb-4 space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar">
            {/* Quick add file */}
            {addFileOpen && (
              <div className="flex items-center gap-1.5 rounded-lg border p-1.5 bg-[var(--chat-sidebar-card-bg)] border-[var(--chat-sidebar-card-border)]">
                <input
                  ref={inputRef}
                  value={newFilePath}
                  onChange={(e) => setNewFilePath(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') handleAddFile(); if (e.key === 'Escape') setAddFileOpen(false) }}
                  placeholder="path/to/file.ts"
                  maxLength={200}
                  className="flex-1 min-w-0 bg-transparent text-[10px] text-[var(--chat-sidebar-value)] placeholder:text-[var(--chat-sidebar-stat-label)]/50 focus:outline-none px-1"
                />
                <button
                  onClick={handleAddFile}
                  disabled={!newFilePath.trim()}
                  className="rounded px-2 py-0.5 text-[8px] font-bold bg-[var(--chat-sidebar-stat-text)]/20 text-[var(--chat-sidebar-stat-text)] hover:bg-[var(--chat-sidebar-stat-text)]/30 disabled:opacity-30 transition-colors"
                >
                  Add
                </button>
              </div>
            )}

            {workspaceFiles.length === 0 && !addFileOpen ? (
              <div className="rounded-xl border border-dashed p-4 text-center border-[var(--chat-sidebar-artifact-border)]">
                <FolderOpen className="h-5 w-5 mx-auto mb-1.5 text-[var(--chat-sidebar-stat-label)]" />
                <p className="text-[9px] font-bold text-[var(--chat-sidebar-stat-label)]">
                  No files in context
                </p>
                <p className="text-[8px] text-[var(--chat-sidebar-stat-label)]/70 mt-0.5">
                  Add files the agent should work with
                </p>
              </div>
            ) : (
              workspaceFiles.map((file) => {
                const Icon = FILE_TYPE_ICONS[file.type]
                const color = FILE_TYPE_COLORS[file.type]
                const isArtifact = !!file.artifactId
                return (
                  <div
                    key={file.id}
                    className="group flex items-center gap-2 rounded-lg px-2.5 py-2 transition-all bg-[var(--chat-sidebar-artifact-bg)] border border-[var(--chat-sidebar-artifact-border)] hover:border-[var(--chat-sidebar-artifact-hover-border)]"
                  >
                    <div className="relative flex-shrink-0">
                      <Icon className={cn('h-3.5 w-3.5', color)} />
                      {isArtifact && (
                        <Link2 className="absolute -top-1 -right-1 h-2 w-2 text-sky-400" />
                      )}
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-[10px] font-bold text-[var(--chat-sidebar-value)] truncate">{file.name}</p>
                      <div className="flex items-center gap-1.5">
                        {!isArtifact && <p className="text-[8px] font-mono text-[var(--chat-sidebar-stat-label)] truncate">{file.path}</p>}
                        {isArtifact && file.artifactVersion && (
                          <span className="text-[7px] font-bold text-sky-400/80">v{file.artifactVersion}</span>
                        )}
                        {file.chunks && (
                          <span className="text-[7px] text-[var(--chat-sidebar-stat-label)]">{file.chunks.length} chunks</span>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-all">
                      {isArtifact && (
                        <a
                          href={`/artifacts?id=${file.artifactId}`}
                          className="rounded p-0.5 text-[var(--chat-sidebar-stat-label)] hover:text-sky-400 transition-colors"
                          title="Open in Artifacts"
                        >
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      )}
                      {isArtifact && (
                        <button
                          onClick={() => {
                            const a = document.createElement('a')
                            a.href = `/api/artifacts/${file.artifactId}/download`
                            a.download = file.name
                            a.click()
                          }}
                          className="rounded p-0.5 text-[var(--chat-sidebar-stat-label)] hover:text-emerald-400 transition-colors"
                          title="Download"
                        >
                          <Download className="h-3 w-3" />
                        </button>
                      )}
                      <button
                        onClick={() => removeWorkspaceFile(file.id)}
                        className="rounded p-0.5 text-[var(--chat-sidebar-stat-label)] hover:text-red-400 transition-colors"
                        title="Remove from context"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        )}
      </div>

      {/* ───── Search & References ───── */}
      <div>
        <div
          onClick={() => setSearchExpanded(!searchExpanded)}
          className="flex w-full items-center justify-between p-4 pb-2 text-left cursor-pointer select-none"
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSearchExpanded(!searchExpanded) } }}
        >
          <div className="flex items-center gap-2">
            {searchExpanded ? <ChevronDown className="h-3 w-3 text-[var(--chat-sidebar-stat-label)]" /> : <ChevronRight className="h-3 w-3 text-[var(--chat-sidebar-stat-label)]" />}
            <h3 className="text-[10px] font-black tracking-[0.25em] uppercase text-[var(--chat-sidebar-heading)]">
              References
            </h3>
            {searchReferences.length > 0 && (
              <span className="ml-1 rounded-full px-1.5 py-0.5 text-[8px] font-bold bg-emerald-500/20 text-emerald-400">
                {searchReferences.length}
              </span>
            )}
          </div>
          {searchReferences.length > 0 && (
            <button
              onClick={(e) => { e.stopPropagation(); clearSearchReferences() }}
              className="text-[8px] font-bold uppercase tracking-wider text-[var(--chat-sidebar-stat-label)] hover:text-[var(--chat-sidebar-stat-text)] transition-colors"
            >
              Clear
            </button>
          )}
        </div>

        {searchExpanded && (
          <div className="px-4 pb-4 space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar">
            {searchReferences.length === 0 ? (
              <div className="rounded-xl border border-dashed p-4 text-center border-[var(--chat-sidebar-artifact-border)]">
                <ModeEmptyIcon mode={agentMode} />
                <p className="text-[9px] font-bold text-[var(--chat-sidebar-stat-label)] mt-1.5">
                  {agentMode === 'rag' ? 'Retrieved documents appear here' :
                   agentMode === 'web' ? 'Web search results appear here' :
                   agentMode === 'sql' ? 'Query results appear here' :
                   'Search references collected during the session'}
                </p>
              </div>
            ) : (
              searchReferences.map((ref) => {
                const Icon = SOURCE_ICONS[ref.source] ?? File
                const color = SOURCE_COLORS[ref.source] ?? 'text-slate-400'
                return (
                  <div
                    key={ref.id}
                    className="group relative rounded-xl border p-2.5 transition-all bg-[var(--chat-sidebar-artifact-bg)] border-[var(--chat-sidebar-artifact-border)] hover:border-[var(--chat-sidebar-artifact-hover-border)]"
                  >
                    <div className="flex items-start gap-2">
                      <div className={cn("rounded-md p-1.5 bg-[var(--chat-sidebar-artifact-icon-bg)]", color)}>
                        <Icon className="h-3 w-3" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-[10px] font-bold text-[var(--chat-sidebar-value)] truncate">{ref.title}</p>
                        <p className="text-[8px] text-[var(--chat-sidebar-stat-label)] mt-0.5 line-clamp-2 leading-snug">{ref.snippet}</p>
                        {ref.url && (
                          <a href={ref.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 mt-1 text-[7px] text-[var(--chat-sidebar-stat-text)] hover:underline">
                            <ExternalLink className="h-2 w-2" /> Source
                          </a>
                        )}
                      </div>
                      <button
                        onClick={() => removeSearchReference(ref.id)}
                        className="rounded p-0.5 opacity-0 group-hover:opacity-100 text-[var(--chat-sidebar-stat-label)] hover:text-red-400 transition-all flex-shrink-0"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/* ─── Sub-component ──────────────────────────────────────────────── */

function ModeEmptyIcon({ mode }: { mode: AgentMode }) {
  const icons: Record<AgentMode, React.ElementType> = {
    chat: Search, rag: FileText, web: Globe, sql: Database,
  }
  const Icon = icons[mode] ?? Search
  return <Icon className="h-5 w-5 mx-auto text-[var(--chat-sidebar-stat-label)]" />
}
