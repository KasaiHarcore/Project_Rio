"use client"

import React, { useState, useEffect, useCallback, Suspense } from "react"
import dynamic from "next/dynamic"
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { Share2, Loader2, AlertCircle, RefreshCw, Filter } from "lucide-react"
import { cn } from "@/shared/lib/utils"
import { apiGetNoteGraph, NoteGraphNode, NoteGraphEdge, NoteGraphStats } from "@/features/notes/api"

// Lazy-load Three.js-based graph — 42 MB dep, requires browser canvas
const NoteGraph = dynamic(
  () => import("@/features/notes/components/NoteGraph").then(m => m.NoteGraph),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="relative w-20 h-20 mx-auto mb-4">
            <div className="absolute inset-0 rounded-full border-2 border-rose-500/20 animate-ping" />
            <div className="absolute inset-2 rounded-full border-2 border-rose-500/30 animate-pulse" />
            <div className="absolute inset-4 rounded-full bg-rose-500/10 flex items-center justify-center">
              <Share2 className="h-6 w-6 text-rose-500/60" />
            </div>
          </div>
          <p className="text-sm text-page-muted">Loading 3D graph…</p>
        </div>
      </div>
    ),
  }
)

function GraphPageContent() {
  const [nodes, setNodes] = useState<NoteGraphNode[]>([])
  const [edges, setEdges] = useState<NoteGraphEdge[]>([])
  const [stats, setStats] = useState<NoteGraphStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterType, setFilterType] = useState<string | null>(null)

  const fetchGraph = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await apiGetNoteGraph()
      setNodes(data.nodes)
      setEdges(data.edges)
      setStats(data.stats)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load graph"
      setError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchGraph()
  }, [fetchGraph])

  // Filter nodes/edges by type
  const filteredNodes = filterType
    ? nodes.filter((n) => n.type === filterType || edges.some(
        (e) => (e.source_id === n.id || e.target_id === n.id) &&
          (nodes.find((nn) => nn.id === e.source_id)?.type === filterType ||
           nodes.find((nn) => nn.id === e.target_id)?.type === filterType)
      ))
    : nodes

  const filteredEdges = filterType
    ? edges.filter((e) => {
        const src = nodes.find((n) => n.id === e.source_id)
        const tgt = nodes.find((n) => n.id === e.target_id)
        return src?.type === filterType || tgt?.type === filterType
      })
    : edges

  const nodeTypes = Array.from(new Set(nodes.map((n) => n.type)))

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
                  "bg-gradient-to-br from-rose-500 to-rose-600"
                )}
                style={{ boxShadow: "0 10px 15px -3px var(--page-icon-shadow)" }}
              >
                <Share2 className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-black text-page-title">Note Graph</h1>
                <p className="text-[10px] font-bold tracking-wider uppercase text-page-subtitle">
                  {stats?.truncated
                    ? `Showing ${stats.returned_nodes} of ${stats.total_nodes} nodes`
                    : "Knowledge Visualization"}
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Type filter */}
            {nodeTypes.length > 1 && (
              <div className="flex items-center gap-1.5">
                <Filter className="h-3.5 w-3.5 text-page-muted" />
                <select
                  value={filterType ?? ""}
                  onChange={(e) => setFilterType(e.target.value || null)}
                  className="text-xs rounded-lg border px-2 py-1.5 outline-none bg-[var(--page-search-bg)] border-[var(--page-search-border)] text-[var(--page-search-text)]"
                >
                  <option className="bg-[#0d1117] text-[#e6edf3]" value="">All types</option>
                  {nodeTypes.map((t) => (
                    <option className="bg-[#0d1117] text-[#e6edf3]" key={t} value={t}>
                      {t.charAt(0).toUpperCase() + t.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button
              onClick={fetchGraph}
              className="text-page-muted hover:text-page-card-title transition-colors"
            >
              <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            </button>
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 relative">
          {error && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 shadow-lg">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
              <button
                onClick={() => setError(null)}
                className="text-red-400 hover:text-red-600 text-xs font-bold"
              >
                Dismiss
              </button>
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <Loader2 className="h-8 w-8 animate-spin text-page-loader mx-auto mb-3" />
                <p className="text-sm text-page-muted">Loading graph data...</p>
              </div>
            </div>
          ) : (
            <NoteGraph nodes={filteredNodes} edges={filteredEdges} />
          )}
        </div>
      </PageTransition>
    </DashboardLayout>
  )
}

export default function GraphPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center h-screen">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      }
    >
      <GraphPageContent />
    </Suspense>
  )
}
