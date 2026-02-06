"use client"

import React, { useState } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { MessageSquare, Clock, Trash2, ChevronRight, Search, Calendar } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { cn } from "@/lib/utils"
import { useTheme } from '@/components/providers/theme-provider'
import { getCycleConfig } from '@/lib/cycle-config'

interface Conversation {
  id: string
  title: string
  preview: string
  messageCount: number
  createdAt: string
  updatedAt: string
}

const mockConversations: Conversation[] = [
  {
    id: 'conv-001',
    title: 'Binary Search Implementation',
    preview: 'Can you help me implement a binary search algorithm in Python?',
    messageCount: 12,
    createdAt: '2026-02-05',
    updatedAt: '2026-02-05 10:24'
  },
  {
    id: 'conv-002',
    title: 'Machine Learning Study Plan',
    preview: 'I need a 30-day study plan for machine learning fundamentals...',
    messageCount: 8,
    createdAt: '2026-02-04',
    updatedAt: '2026-02-04 15:30'
  },
  {
    id: 'conv-003',
    title: 'Neural Network Architecture',
    preview: 'Explain the architecture of a convolutional neural network...',
    messageCount: 15,
    createdAt: '2026-02-03',
    updatedAt: '2026-02-03 09:15'
  },
  {
    id: 'conv-004',
    title: 'API Design Best Practices',
    preview: 'What are the best practices for designing RESTful APIs?',
    messageCount: 6,
    createdAt: '2026-02-02',
    updatedAt: '2026-02-02 14:45'
  },
  {
    id: 'conv-005',
    title: 'Data Structures Overview',
    preview: 'Give me an overview of common data structures and their use cases...',
    messageCount: 20,
    createdAt: '2026-02-01',
    updatedAt: '2026-02-01 11:00'
  },
]

export default function HistoryPage() {
  const router = useRouter()
  const { theme } = useTheme()
  const isNight = theme === 'dark'
  
  const [conversations, setConversations] = useState<Conversation[]>(mockConversations)
  const [searchQuery, setSearchQuery] = useState('')

  const filteredConversations = conversations.filter(conv =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    conv.preview.toLowerCase().includes(searchQuery.toLowerCase())
  )

  // Group conversations by date
  const groupedConversations = filteredConversations.reduce((groups, conv) => {
    const date = conv.createdAt
    if (!groups[date]) {
      groups[date] = []
    }
    groups[date].push(conv)
    return groups
  }, {} as Record<string, Conversation[]>)

  const handleDelete = (id: string) => {
    setConversations(convs => convs.filter(c => c.id !== id))
  }

  const handleOpen = (id: string) => {
    // Navigate to chat with conversation ID
    router.push(`/?conversation=${id}`)
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
                  isNight ? "bg-gradient-to-br from-rose-500 to-rose-600 shadow-rose-500/20" : "bg-gradient-to-br from-indigo-500 to-indigo-600 shadow-indigo-500/20"
              )}>
                <Clock className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className={cn("text-lg font-black", isNight ? "text-slate-100" : "text-slate-800")}>History</h1>
                <p className={cn("text-[10px] font-bold tracking-wider uppercase", isNight ? "text-slate-500" : "text-slate-400")}>Past Conversations</p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <input
                type="text"
                placeholder="Search conversations..."
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
          {/* Stats */}
          <div className="mb-8 grid gap-4 md:grid-cols-3">
            <div className={cn("relative overflow-hidden rounded-2xl border p-5 shadow-sm", isNight ? "bg-[#0d1117]/40 border-rose-900/30" : "bg-white/70 border-blue-100")}>
              <div className={cn("absolute top-0 left-0 h-1 w-full bg-gradient-to-r", isNight ? "from-rose-500 to-rose-700" : "from-indigo-400 to-indigo-600")}></div>
              <p className={cn("text-2xl font-black", isNight ? "text-slate-200" : "text-slate-700")}>{conversations.length}</p>
              <p className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Total Conversations</p>
            </div>
            <div className={cn("relative overflow-hidden rounded-2xl border p-5 shadow-sm", isNight ? "bg-[#0d1117]/40 border-rose-900/30" : "bg-white/70 border-blue-100")}>
              <div className={cn("absolute top-0 left-0 h-1 w-full bg-gradient-to-r", isNight ? "from-red-400 to-red-600" : "from-emerald-400 to-emerald-600")}></div>
              <p className={cn("text-2xl font-black", isNight ? "text-slate-200" : "text-slate-700")}>
                {conversations.reduce((sum, c) => sum + c.messageCount, 0)}
              </p>
              <p className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Total Messages</p>
            </div>
            <div className={cn("relative overflow-hidden rounded-2xl border p-5 shadow-sm", isNight ? "bg-[#0d1117]/40 border-rose-900/30" : "bg-white/70 border-blue-100")}>
              <div className={cn("absolute top-0 left-0 h-1 w-full bg-gradient-to-r", isNight ? "from-pink-400 to-pink-600" : "from-amber-400 to-amber-600")}></div>
              <p className={cn("text-2xl font-black", isNight ? "text-slate-200" : "text-slate-700")}>
                {Object.keys(groupedConversations).length}
              </p>
              <p className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Active Days</p>
            </div>
          </div>

          {/* Conversations List */}
          {Object.keys(groupedConversations).length === 0 ? (
            <div className="text-center py-12">
              <MessageSquare className="mx-auto h-12 w-12 text-slate-300 mb-4" />
              <p className="text-slate-500">No conversations found</p>
            </div>
          ) : (
            <div className="space-y-8">
              {Object.entries(groupedConversations).map(([date, convs]) => (
                <div key={date}>
                  {/* Date Header */}
                  <div className="mb-4 flex items-center gap-2">
                    <Calendar className={cn("h-4 w-4", isNight ? "text-rose-400" : "text-blue-400")} />
                    <h2 className={cn("text-[10px] font-black tracking-[0.3em] uppercase", isNight ? "text-rose-400" : "text-blue-400")}>
                      {new Date(date).toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
                    </h2>
                    <div className={cn("flex-1 h-[1px] bg-gradient-to-r to-transparent", isNight ? "from-rose-900/50" : "from-blue-200")}></div>
                  </div>

                  {/* Conversation Cards */}
                  <div className="space-y-3">
                    {convs.map((conv) => (
                      <div
                        key={conv.id}
                        className={cn(
                            "group relative rounded-2xl border p-5 shadow-sm backdrop-blur-sm transition-all hover:shadow-md cursor-pointer",
                            isNight 
                                ? "bg-[#0d1117]/40 border-rose-900/20 hover:border-rose-700 hover:bg-[#0d1117]/80" 
                                : "bg-white/70 border-blue-50 hover:border-blue-200"
                        )}
                        onClick={() => handleOpen(conv.id)}
                      >
                        <div className="flex items-center gap-4">
                          {/* Icon */}
                          <div className={cn(
                              "rounded-xl p-3 transition-transform group-hover:scale-110",
                              isNight ? "bg-rose-900/20 text-rose-400" : "bg-indigo-50 text-indigo-500"
                          )}>
                            <MessageSquare className="h-6 w-6" />
                          </div>

                          {/* Info */}
                          <div className="flex-1 min-w-0">
                            <h3 className={cn("font-bold mb-1", isNight ? "text-slate-200" : "text-slate-700")}>{conv.title}</h3>
                            <p className={cn("text-sm truncate", isNight ? "text-slate-500" : "text-slate-500")}>{conv.preview}</p>
                            <div className="mt-2 flex items-center gap-4 text-[10px] text-slate-400">
                              <span className="flex items-center gap-1">
                                <MessageSquare className="h-3 w-3" />
                                {conv.messageCount} messages
                              </span>
                              <span className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {conv.updatedAt}
                              </span>
                            </div>
                          </div>

                          {/* Actions */}
                          <div className="flex items-center gap-2">
                            <button 
                              onClick={(e) => { e.stopPropagation(); handleDelete(conv.id) }}
                              className="flex items-center justify-center rounded-lg border border-red-100 bg-red-50 p-2.5 text-red-500 transition-colors hover:bg-red-100 opacity-0 group-hover:opacity-100"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                            <ChevronRight className="h-5 w-5 text-slate-300 group-hover:text-blue-500 transition-colors" />
                          </div>
                        </div>
                      </div>
                    ))}
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
