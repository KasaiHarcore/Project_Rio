"use client"

import React, { useState } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { FileCode, FileText, Image, Download, Eye, Trash2, Clock, Sparkles } from 'lucide-react'
import { cn } from "@/lib/utils"
import { useTheme } from '@/components/providers/theme-provider'
import { getCycleConfig } from '@/lib/cycle-config'

interface Artifact {
  id: string
  name: string
  type: 'code' | 'document' | 'image' | 'data'
  language?: string
  preview: string
  createdAt: string
  conversationId: string
}

const mockArtifacts: Artifact[] = [
  { 
    id: '1', 
    name: 'binary_search.py', 
    type: 'code', 
    language: 'Python',
    preview: 'def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    while left <= right:\n        mid = (left + right) // 2\n        ...',
    createdAt: '2026-02-05 10:24',
    conversationId: 'conv-001'
  },
  { 
    id: '2', 
    name: 'study_plan.md', 
    type: 'document',
    preview: '# 30-Day ML Study Plan\n\n## Week 1: Foundations\n- Linear Algebra basics\n- Probability and Statistics\n...',
    createdAt: '2026-02-04 15:30',
    conversationId: 'conv-002'
  },
  { 
    id: '3', 
    name: 'neural_network_diagram.svg', 
    type: 'image',
    preview: 'Neural Network Architecture Diagram',
    createdAt: '2026-02-03 09:15',
    conversationId: 'conv-003'
  },
  { 
    id: '4', 
    name: 'api_response.json', 
    type: 'data',
    language: 'JSON',
    preview: '{\n  "status": "success",\n  "data": {\n    "model": "gpt-4",\n    "tokens": 1500\n  }\n}',
    createdAt: '2026-02-02 14:45',
    conversationId: 'conv-001'
  },
]

const typeIcons = {
  code: FileCode,
  document: FileText,
  image: Image,
  data: FileCode,
}

const typeColors = {
  code: 'bg-emerald-50 text-emerald-500',
  document: 'bg-blue-50 text-blue-500',
  image: 'bg-purple-50 text-purple-500',
  data: 'bg-amber-50 text-amber-500',
}

export default function ArtifactsPage() {
  const { theme } = useTheme()
  const isNight = theme === 'dark'
  
  const [artifacts, setArtifacts] = useState<Artifact[]>(mockArtifacts)
  const [filter, setFilter] = useState<'all' | 'code' | 'document' | 'image' | 'data'>('all')

  const filteredArtifacts = filter === 'all' 
    ? artifacts 
    : artifacts.filter(a => a.type === filter)

  const handleDelete = (id: string) => {
    setArtifacts(arts => arts.filter(a => a.id !== id))
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
                  isNight ? "bg-gradient-to-br from-purple-800 to-purple-900 shadow-purple-900/20" : "bg-gradient-to-br from-purple-500 to-purple-600 shadow-purple-500/20"
              )}>
                <Sparkles className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className={cn("text-lg font-black", isNight ? "text-slate-100" : "text-slate-800")}>Artifacts</h1>
                <p className={cn("text-[10px] font-bold tracking-wider uppercase", isNight ? "text-slate-500" : "text-slate-400")}>Generated Content</p>
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
                        ? (isNight ? "bg-gradient-to-r from-rose-600 to-red-500 text-white shadow-lg shadow-rose-900/20" : 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-200')
                        : (isNight ? "border border-rose-900/30 bg-[#0d1117]/60 text-slate-500 hover:bg-[#0d1117] hover:text-rose-400" : 'border border-blue-100 bg-white/60 text-slate-500 hover:bg-white hover:text-blue-600')
                )}
              >
                {type}
              </button>
            ))}
          </div>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 lg:p-8">
          {/* Stats */}
          <div className="mb-8 grid gap-4 md:grid-cols-4">
            {[
              { label: 'Total Artifacts', value: artifacts.length, color: isNight ? 'from-blue-500 to-blue-700' : 'from-blue-400 to-blue-600' },
              { label: 'Code Files', value: artifacts.filter(a => a.type === 'code').length, color: isNight ? 'from-emerald-500 to-emerald-700' : 'from-emerald-400 to-emerald-600' },
              { label: 'Documents', value: artifacts.filter(a => a.type === 'document').length, color: isNight ? 'from-purple-500 to-purple-700' : 'from-purple-400 to-purple-600' },
              { label: 'This Week', value: artifacts.length, color: isNight ? 'from-amber-500 to-amber-700' : 'from-amber-400 to-amber-600' },
            ].map((stat, i) => (
              <div key={i} className={cn("relative overflow-hidden rounded-2xl border p-5 shadow-sm", isNight ? "bg-[#0d1117]/40 border-rose-900/30" : "bg-white/70 border-blue-100")}>
                <div className={`absolute top-0 left-0 h-1 w-full bg-gradient-to-r ${stat.color}`}></div>
                <p className={cn("text-2xl font-black", isNight ? "text-slate-200" : "text-slate-700")}>{stat.value}</p>
                <p className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">{stat.label}</p>
              </div>
            ))}
          </div>

          {/* Artifacts List */}
          <div className="mb-4">
            <h2 className={cn("text-[10px] font-black tracking-[0.3em] uppercase", isNight ? "text-rose-400" : "text-blue-400")}>
              Recent Artifacts ({filteredArtifacts.length})
            </h2>
          </div>

          {filteredArtifacts.length === 0 ? (
            <div className="text-center py-12">
              <Sparkles className="mx-auto h-12 w-12 text-slate-300 mb-4" />
              <p className="text-slate-500">No artifacts found</p>
            </div>
          ) : (
            <div className="space-y-4">
              {filteredArtifacts.map((artifact) => {
                const Icon = typeIcons[artifact.type]
                const nightColors = {
                    code: 'bg-emerald-900/20 text-emerald-400',
                    document: 'bg-blue-900/20 text-blue-400',
                    image: 'bg-purple-900/20 text-purple-400',
                    data: 'bg-amber-900/20 text-amber-400',
                }
                
                return (
                  <div
                    key={artifact.id}
                    className={cn(
                        "group relative rounded-2xl border p-5 shadow-sm backdrop-blur-sm transition-all hover:shadow-md",
                        isNight 
                            ? "bg-[#0d1117]/40 border-rose-900/20 hover:border-rose-700 hover:bg-[#0d1117]/80" 
                            : "bg-white/70 border-blue-50 hover:border-blue-200"
                    )}
                  >
                    <div className="flex items-start gap-4">
                      {/* Icon */}
                      <div className={cn("rounded-xl p-3 transition-transform group-hover:scale-110", isNight ? nightColors[artifact.type] : typeColors[artifact.type])}>
                        <Icon className="h-6 w-6" />
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                          <h3 className={cn("font-bold", isNight ? "text-slate-200" : "text-slate-700")}>{artifact.name}</h3>
                          {artifact.language && (
                            <span className={cn("rounded px-2 py-0.5 text-[9px] font-bold uppercase", isNight ? "bg-slate-800 text-slate-400" : "bg-slate-100 text-slate-500")}>
                              {artifact.language}
                            </span>
                          )}
                        </div>
                        
                        {/* Preview */}
                        <pre className={cn("mt-2 rounded-xl p-3 text-xs font-mono overflow-hidden max-h-20", isNight ? "bg-[#010409] text-slate-400 border border-slate-800" : "bg-slate-50 text-slate-600")}>
                          {artifact.preview}
                        </pre>

                        {/* Meta */}
                        <div className="mt-3 flex items-center gap-4 text-[10px] text-slate-400">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {artifact.createdAt}
                          </span>
                          <span className="font-mono">ID: {artifact.conversationId}</span>
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button className={cn("flex items-center justify-center rounded-lg border p-2.5 transition-colors", isNight ? "border-blue-900/50 bg-blue-900/20 text-blue-400 hover:bg-blue-900/40" : "border-blue-100 bg-blue-50 text-blue-500 hover:bg-blue-100")}>
                          <Eye className="h-4 w-4" />
                        </button>
                        <button className={cn("flex items-center justify-center rounded-lg border p-2.5 transition-colors", isNight ? "border-emerald-900/50 bg-emerald-900/20 text-emerald-400 hover:bg-emerald-900/40" : "border-emerald-100 bg-emerald-50 text-emerald-500 hover:bg-emerald-100")}>
                          <Download className="h-4 w-4" />
                        </button>
                        <button 
                          onClick={() => handleDelete(artifact.id)}
                          className={cn("flex items-center justify-center rounded-lg border p-2.5 transition-colors", isNight ? "border-red-900/50 bg-red-900/20 text-red-400 hover:bg-red-900/40" : "border-red-100 bg-red-50 text-red-500 hover:bg-red-100")}
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
      </PageTransition>
    </DashboardLayout>
  )
}
