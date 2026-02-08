"use client"

import React, { useState } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { Upload, FileText, Search, Trash2, Eye, FolderOpen } from 'lucide-react'
import { cn } from "@/lib/utils"
import { useTheme } from '@/components/providers/theme-provider'
import { getCycleConfig } from '@/lib/cycle-config'

interface Document {
  id: string
  name: string
  type: string
  size: string
  uploadedAt: string
  status: 'processing' | 'ready' | 'error'
}

const mockDocuments: Document[] = [
  { id: '1', name: 'Machine_Learning_Fundamentals.pdf', type: 'PDF', size: '2.4 MB', uploadedAt: '2026-02-04', status: 'ready' },
  { id: '2', name: 'Neural_Networks_Guide.pdf', type: 'PDF', size: '5.1 MB', uploadedAt: '2026-02-03', status: 'ready' },
  { id: '3', name: 'Python_Cheatsheet.md', type: 'Markdown', size: '124 KB', uploadedAt: '2026-02-02', status: 'ready' },
  { id: '4', name: 'Data_Structures_Notes.txt', type: 'Text', size: '45 KB', uploadedAt: '2026-02-01', status: 'processing' },
]

export default function KnowledgePage() {
  const { theme } = useTheme()
  const isNight = theme === 'dark'

  const [documents, setDocuments] = useState<Document[]>(mockDocuments)
  const [searchQuery, setSearchQuery] = useState('')
  const [isDragging, setIsDragging] = useState(false)

  const filteredDocs = documents.filter(doc => 
    doc.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleDelete = (id: string) => {
    setDocuments(docs => docs.filter(d => d.id !== id))
  }

  return (
    <DashboardLayout>
      <PageTransition className={cn("flex-1 flex flex-col overflow-hidden", isNight ? "bg-[#0f111a]" : "bg-[#F4F9FF]")}>
        {/* Header */}
        <header className={cn(
            "relative flex h-16 items-center justify-between border-b px-8 backdrop-blur-md flex-shrink-0",
             isNight ? "border-rose-900/40 bg-[#0d1117]/50" : "border-blue-100 bg-white/40"
        )}>
          <div className={cn(
              "absolute bottom-0 left-0 h-[1px] w-full opacity-50 bg-gradient-to-r from-transparent to-transparent",
              isNight ? "via-rose-500/50" : "via-blue-300"
          )}></div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-xl shadow-lg",
                  isNight ? "bg-gradient-to-br from-rose-500 to-rose-600 shadow-rose-500/20" : "bg-gradient-to-br from-blue-500 to-blue-600 shadow-blue-500/20"
              )}>
                <FolderOpen className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className={cn("text-lg font-black", isNight ? "text-slate-100" : "text-slate-800")}>Knowledge Base</h1>
                <p className={cn("text-[10px] font-bold tracking-wider uppercase", isNight ? "text-slate-500" : "text-slate-400")}>Document Repository</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className={cn(
                    "pl-10 pr-4 py-2 rounded-xl border text-sm outline-none transition-all w-64",
                    isNight 
                      ? "bg-[#0d1117]/60 border-rose-900/40 text-rose-100 placeholder:text-rose-900/50 focus:border-rose-700 focus:ring-2 focus:ring-rose-900/20"
                      : "bg-white/60 border-blue-100 text-slate-700 placeholder:text-slate-400 focus:border-blue-300 focus:ring-2 focus:ring-blue-100"
                )}
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
            onDrop={(e) => { e.preventDefault(); setIsDragging(false) }}
            className={cn(
                "relative mb-8 rounded-2xl border-2 border-dashed p-8 text-center transition-all",
                isDragging 
                    ? (isNight ? 'border-rose-500 bg-rose-900/20' : 'border-blue-400 bg-blue-50/50')
                    : (isNight ? 'border-rose-900/30 bg-[#0d1117]/40 hover:border-rose-700 hover:bg-[#0d1117]/60' : 'border-blue-200 bg-white/50 hover:border-blue-300 hover:bg-white/70')
            )}
          >
            <div className={cn(
                "mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl",
                isNight ? "bg-gradient-to-br from-rose-900/40 to-rose-900/10" : "bg-gradient-to-br from-blue-100 to-blue-50"
            )}>
              <Upload className={cn("h-8 w-8", isNight ? "text-rose-500" : "text-blue-500")} />
            </div>
            <h3 className={cn("text-lg font-bold mb-2", isNight ? "text-slate-100" : "text-slate-700")}>Upload Documents</h3>
            <p className="text-sm text-slate-500 mb-4">Drag and drop files here, or click to browse</p>
            <button className={cn(
                "inline-flex items-center gap-2 rounded-xl px-6 py-3 text-sm font-bold text-white shadow-lg transition-all hover:scale-[1.02] active:scale-95",
                isNight 
                    ? "bg-gradient-to-r from-rose-600 to-red-500 shadow-rose-900/20" 
                    : "bg-gradient-to-r from-blue-600 to-blue-500 shadow-blue-200"
            )}>
              <Upload className="h-4 w-4" />
              Select Files
            </button>
            <p className="mt-4 text-[10px] font-bold tracking-wider text-slate-400 uppercase">
              Supports: PDF, TXT, MD, DOCX • Max 50MB per file
            </p>
          </div>

          {/* Documents Grid */}
          <div className="mb-4 flex items-center justify-between">
            <h2 className={cn("text-[10px] font-black tracking-[0.3em] uppercase", isNight ? "text-rose-400" : "text-blue-400")}>
              Your Documents ({filteredDocs.length})
            </h2>
          </div>

          {filteredDocs.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="mx-auto h-12 w-12 text-slate-300 mb-4" />
              <p className="text-slate-500">No documents found</p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredDocs.map((doc) => (
                <div
                  key={doc.id}
                  className={cn(
                      "group relative rounded-2xl border p-5 shadow-sm backdrop-blur-sm transition-all hover:shadow-md",
                      isNight 
                          ? "bg-[#0d1117]/40 border-rose-900/20 hover:border-rose-700 hover:bg-[#0d1117]/80" 
                          : "bg-white/70 border-blue-50 hover:border-blue-200"
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
                        isNight ? "bg-rose-900/20 text-rose-500" : "bg-blue-50 text-blue-500"
                    )}>
                      <FileText className="h-6 w-6" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className={cn("font-bold truncate pr-4", isNight ? "text-slate-200" : "text-slate-700")}>{doc.name}</h3>
                      <p className="mt-1 text-[10px] font-bold tracking-wider text-slate-400 uppercase">
                        {doc.type} • {doc.size}
                      </p>
                      <p className="mt-1 font-mono text-[9px] text-slate-400">
                        Uploaded: {doc.uploadedAt}
                      </p>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button className={cn(
                        "flex-1 flex items-center justify-center gap-1.5 rounded-lg border py-2 text-[10px] font-bold tracking-wider uppercase transition-colors",
                         isNight 
                            ? "border-rose-900/50 bg-rose-900/20 text-rose-300 hover:bg-rose-900/40" 
                            : "border-blue-100 bg-blue-50 text-blue-600 hover:bg-blue-100"
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
                    <div className={cn("absolute bottom-0 left-0 h-1 w-full overflow-hidden rounded-b-2xl", isNight ? "bg-rose-900/30" : "bg-blue-100")}>
                      <div className={cn("h-full w-1/2 animate-pulse bg-gradient-to-r", isNight ? "from-rose-500 to-rose-600" : "from-blue-400 to-blue-600")}></div>
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
