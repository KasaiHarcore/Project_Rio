"use client"

import React, { useState } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { FileCode, FileText, Image, Download, Eye, Trash2, Clock, Sparkles } from 'lucide-react'

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
      <PageTransition className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="relative flex h-16 items-center justify-between border-b border-blue-100 bg-white/40 px-8 backdrop-blur-md flex-shrink-0">
          <div className="absolute bottom-0 left-0 h-[1px] w-full bg-gradient-to-r from-transparent via-blue-300 to-transparent opacity-50"></div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-purple-500 to-purple-600 shadow-lg shadow-purple-500/20">
                <Sparkles className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-black text-slate-800">Artifacts</h1>
                <p className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Generated Content</p>
              </div>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex items-center gap-2">
            {(['all', 'code', 'document', 'image', 'data'] as const).map((type) => (
              <button
                key={type}
                onClick={() => setFilter(type)}
                className={`px-4 py-2 rounded-xl text-[10px] font-bold tracking-wider uppercase transition-all ${
                  filter === type
                    ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-lg shadow-blue-200'
                    : 'border border-blue-100 bg-white/60 text-slate-500 hover:bg-white hover:text-blue-600'
                }`}
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
              { label: 'Total Artifacts', value: artifacts.length, color: 'from-blue-400 to-blue-600' },
              { label: 'Code Files', value: artifacts.filter(a => a.type === 'code').length, color: 'from-emerald-400 to-emerald-600' },
              { label: 'Documents', value: artifacts.filter(a => a.type === 'document').length, color: 'from-purple-400 to-purple-600' },
              { label: 'This Week', value: artifacts.length, color: 'from-amber-400 to-amber-600' },
            ].map((stat, i) => (
              <div key={i} className="relative overflow-hidden rounded-2xl border border-blue-100 bg-white/70 p-5 shadow-sm">
                <div className={`absolute top-0 left-0 h-1 w-full bg-gradient-to-r ${stat.color}`}></div>
                <p className="text-2xl font-black text-slate-700">{stat.value}</p>
                <p className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">{stat.label}</p>
              </div>
            ))}
          </div>

          {/* Artifacts List */}
          <div className="mb-4">
            <h2 className="text-[10px] font-black tracking-[0.3em] text-blue-400 uppercase">
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
                return (
                  <div
                    key={artifact.id}
                    className="group relative rounded-2xl border border-blue-50 bg-white/70 p-5 shadow-sm backdrop-blur-sm transition-all hover:border-blue-200 hover:shadow-md"
                  >
                    <div className="flex items-start gap-4">
                      {/* Icon */}
                      <div className={`rounded-xl p-3 transition-transform group-hover:scale-110 ${typeColors[artifact.type]}`}>
                        <Icon className="h-6 w-6" />
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                          <h3 className="font-bold text-slate-700">{artifact.name}</h3>
                          {artifact.language && (
                            <span className="rounded bg-slate-100 px-2 py-0.5 text-[9px] font-bold text-slate-500 uppercase">
                              {artifact.language}
                            </span>
                          )}
                        </div>
                        
                        {/* Preview */}
                        <pre className="mt-2 rounded-xl bg-slate-50 p-3 text-xs text-slate-600 font-mono overflow-hidden max-h-20">
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
                        <button className="flex items-center justify-center rounded-lg border border-blue-100 bg-blue-50 p-2.5 text-blue-500 transition-colors hover:bg-blue-100">
                          <Eye className="h-4 w-4" />
                        </button>
                        <button className="flex items-center justify-center rounded-lg border border-emerald-100 bg-emerald-50 p-2.5 text-emerald-500 transition-colors hover:bg-emerald-100">
                          <Download className="h-4 w-4" />
                        </button>
                        <button 
                          onClick={() => handleDelete(artifact.id)}
                          className="flex items-center justify-center rounded-lg border border-red-100 bg-red-50 p-2.5 text-red-500 transition-colors hover:bg-red-100"
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
