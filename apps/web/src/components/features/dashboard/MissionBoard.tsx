"use client"

import React from 'react'
import { motion } from 'framer-motion'
import { MessageCircle, ArrowRight, Target, Timer, Loader2, Sparkles, Plus, CheckCircle2, TrendingUp, MessageSquare, Zap, Code, Globe, Music } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useRouter } from 'next/navigation'
import Image from 'next/image'

import { SystemOperationPlayer } from './SystemOperationPlayer'
import { apiGetBriefing, apiGetDashboardStats, DashboardBriefing, DashboardStats, ThreadStat } from '@/lib/api'
import { useMissionStore, Mission } from '@/store/mission-store'
import { useEmotionalStore } from '@/store/emotional-store'
import { useActivityMonitor } from '@/hooks/use-activity-monitor'

// ── Mood Sticker Mapping ─────────────────────────────────────────────────

const MOOD_STICKERS: Record<string, string> = {
  happy: 'Smile',
  excited: 'Excited',
  neutral: 'Smirk',
  sad: 'Sulk',
  frustrated: 'Angry',
  tired: 'Sleepy',
}

// ─── Main Component ───────────────────────────────────────────────────────

export function MissionBoard() {
  const router = useRouter()

  const [stats, setStats] = React.useState<DashboardStats | null>(null)
  const [briefing, setBriefing] = React.useState<DashboardBriefing | null>(null)
  const [loading, setLoading] = React.useState(true)
  const { mood, affinity, relationshipTier, streakDays, fetchState } = useEmotionalStore()
  const activityData = useActivityMonitor()

  const fetchData = React.useCallback(async () => {
    try {
      setLoading(true)
      const [statsData, briefingData] = await Promise.all([
        apiGetDashboardStats(),
        apiGetBriefing(),
      ])
      setStats(statsData)
      setBriefing(briefingData)
    } catch {
      // fallback - show empty state
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    fetchData()
    fetchState('rio')
  }, [fetchData, fetchState])

  const recentThreads = stats?.recent_threads ?? []
  const moodSticker = MOOD_STICKERS[briefing?.emotional_state.mood ?? 'neutral'] || 'Smirk'

  // Handle suggested actions
  const handleAction = (action: string, target?: string | null) => {
    switch (action) {
      case 'open_mission':
        router.push('/mission')
        break
      case 'resume_chat':
        router.push(`/operation?thread=${target}`)
        break
      case 'new_chat':
        router.push('/operation?new=true')
        break
      case 'new_mission':
        router.push('/mission?new=true')
        break
      case 'upload_doc':
        router.push('/knowledge')
        break
    }
  }

  return (
    <div className="flex h-full w-full relative overflow-hidden bg-transparent">
      {/* ─── CENTER MAIN: Workspace ─── */}
      <div className="flex-1 flex flex-col relative overflow-hidden">
        <div className="flex-1 overflow-y-auto custom-scrollbar pb-32">
          <div className="max-w-7xl mx-auto px-6 lg:px-10 py-8 lg:py-12">

            {/* 1. Top Bar: Greeting + Quick Actions */}
            <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-12">
              <div>
                <h1 className="text-3xl font-black text-foreground tracking-tight">
                  {getTimeGreeting()}, Sensei.
                </h1>
                <p className="text-sm text-muted-foreground mt-1 text-emerald-500/80 font-medium">
                  {stats?.active_threads ?? 0} active threads • Level {stats?.level ?? 1} Analyst
                </p>
              </div>
              <div className="flex items-center gap-3 mt-4 md:mt-0">
                <button
                  onClick={() => router.push('/operation?new=true')}
                  className="px-4 py-2 rounded-xl bg-rose-500 hover:bg-rose-600 text-white text-sm font-bold transition-colors shadow-lg shadow-rose-500/30"
                >
                  Start New Operation
                </button>
                <button
                  onClick={() => router.push('/knowledge')}
                  className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 border border-white/20 text-white text-sm font-bold transition-colors"
                >
                  Upload Document
                </button>
              </div>
            </div>

            {/* 2. Today's Summary Card */}
            {loading ? (
              <div className="flex justify-center py-12 mb-12">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : (
              <div className="mb-12 p-6 rounded-2xl border border-white/10 bg-gradient-to-br from-white/5 to-white/[0.02]">
                <h3 className="text-sm font-black text-white/70 uppercase tracking-widest mb-4">Today's Summary</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="flex flex-col">
                    <span className="text-2xl font-black text-white">{stats?.messages_today ?? 0}</span>
                    <span className="text-xs text-white/50 font-medium">Messages Sent</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-2xl font-black text-emerald-400">
                      {briefing?.session_stats?.missions_completed_today ?? 0}
                    </span>
                    <span className="text-xs text-white/50 font-medium">Missions Completed</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-2xl font-black text-indigo-400">
                      {formatTime(activityData?.sessionDuration || 0)}
                    </span>
                    <span className="text-xs text-white/50 font-medium">Time Spent</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-2xl font-black text-amber-400">{streakDays ?? 0} 🔥</span>
                    <span className="text-xs text-white/50 font-medium">Day Streak</span>
                  </div>
                </div>
              </div>
            )}

            {/* 3. Main Grid - Traditional 3-Column Productivity Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-14">
              {/* Column 1: Progress & Stats */}
              <div className="space-y-6">
                {/* Level Progress */}
                <div className="p-6 rounded-2xl border border-indigo-500/30 bg-gradient-to-br from-indigo-500/10 to-purple-500/10">
                  <h3 className="text-xs font-black text-muted-foreground tracking-widest uppercase mb-4">
                    Level Progress
                  </h3>
                  <div className="flex items-center justify-center mb-4">
                    <div className="relative w-32 h-32">
                      <svg className="w-full h-full -rotate-90">
                        <circle
                          cx="64"
                          cy="64"
                          r="56"
                          stroke="currentColor"
                          strokeWidth="8"
                          fill="none"
                          className="text-white/10"
                        />
                        <circle
                          cx="64"
                          cy="64"
                          r="56"
                          stroke="currentColor"
                          strokeWidth="8"
                          fill="none"
                          className="text-indigo-400"
                          strokeDasharray={`${2 * Math.PI * 56}`}
                          strokeDashoffset={`${2 * Math.PI * 56 * (1 - ((stats?.xp_in_level ?? 0) / (stats?.xp_for_next ?? 100)))}`}
                          strokeLinecap="round"
                        />
                      </svg>
                      <div className="absolute inset-0 flex flex-col items-center justify-center">
                        <span className="text-3xl font-black text-white">{stats?.level ?? 1}</span>
                        <span className="text-xs text-white/50 font-medium">Analyst</span>
                      </div>
                    </div>
                  </div>
                  <div className="text-center">
                    <p className="text-sm font-medium text-white/70">
                      {stats?.xp_in_level ?? 0} / {stats?.xp_for_next ?? 100} XP
                    </p>
                    <p className="text-xs text-white/50 mt-1">
                      {((stats?.xp_for_next ?? 100) - (stats?.xp_in_level ?? 0))} XP to Level {(stats?.level ?? 1) + 1}
                    </p>
                  </div>
                </div>

                {/* This Week's Activity */}
                {stats?.messages_by_day && stats.messages_by_day.length > 0 && (
                  <div className="p-6 rounded-2xl border border-white/10 bg-white/5">
                    <h3 className="text-xs font-black text-muted-foreground tracking-widest uppercase mb-4">
                      This Week's Activity
                    </h3>
                    <div className="flex items-end justify-between gap-2 h-24">
                      {stats.messages_by_day.map((count, i) => {
                        const maxCount = Math.max(...stats.messages_by_day, 1)
                        const height = (count / maxCount) * 100
                        const days = ['S', 'M', 'T', 'W', 'T', 'F', 'S']
                        const today = new Date().getDay()
                        const dayIndex = (today - 6 + i + 7) % 7

                        return (
                          <div key={i} className="flex-1 flex flex-col items-center gap-2">
                            <div className="w-full relative group">
                              <div
                                className="w-full bg-gradient-to-t from-indigo-500 to-indigo-400 rounded-t-lg transition-all hover:from-indigo-400 hover:to-indigo-300"
                                style={{ height: `${Math.max(height, 8)}%` }}
                              />
                            </div>
                            <span className="text-[10px] font-bold text-white/50">{days[dayIndex]}</span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {/* Streak Tracker */}
                <div className="p-6 rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-emerald-500/5">
                  <h3 className="text-xs font-black text-muted-foreground tracking-widest uppercase mb-4">
                    Streak Tracker
                  </h3>
                  <div className="text-center mb-4">
                    <span className="text-5xl font-black text-emerald-400">{streakDays ?? 0}</span>
                    <p className="text-sm text-white/70 mt-2">Day Streak 🔥</p>
                  </div>
                  {/* Mini calendar heatmap placeholder */}
                  <div className="grid grid-cols-7 gap-1">
                    {Array.from({ length: 28 }).map((_, i) => (
                      <div
                        key={i}
                        className={cn(
                          'aspect-square rounded-sm',
                          i < (streakDays ?? 0) ? 'bg-emerald-400/50' : 'bg-white/10'
                        )}
                      />
                    ))}
                  </div>
                </div>
              </div>

              {/* Column 2: Tasks & Missions */}
              <div className="space-y-6">
                {/* Upcoming Deadlines */}
                <div className="flex flex-col">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center">
                    <Target size={18} className="text-amber-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-black text-foreground tracking-tight">Upcoming Deadlines</h3>
                    <p className="text-[10px] text-amber-400/60 font-bold uppercase tracking-widest">Priority Missions</p>
                  </div>
                </div>

                <UpcomingDeadlines />

                <motion.button
                  onClick={() => router.push('/mission')}
                  className="w-full flex items-center justify-center gap-2 py-3 mt-4 text-xs font-bold text-white/50 hover:text-white transition-colors rounded-xl border border-dashed border-white/10 hover:border-white/30"
                >
                  View All Missions <ArrowRight size={14} />
                </motion.button>
              </div>

              {/* Recent Conversations */}
              <div className="flex flex-col">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                    <MessageCircle size={18} className="text-indigo-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-black text-foreground tracking-tight">Recent Chats</h3>
                    <p className="text-[10px] text-indigo-400/60 font-bold uppercase tracking-widest">Active Conversations</p>
                  </div>
                </div>

                <div className="space-y-3 flex-1 overflow-y-auto pr-2 custom-scrollbar max-h-[300px]">
                  {loading ? (
                    <div className="flex justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
                    </div>
                  ) : recentThreads.length === 0 ? (
                    <motion.div
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="text-center py-10 rounded-2xl border border-white/10 bg-white/5"
                    >
                      <Sparkles className="w-8 h-8 text-white/20 mx-auto mb-3" />
                      <p className="text-sm font-bold text-white/50">No chats yet</p>
                      <button
                        onClick={() => router.push('/operation?new=true')}
                        className="mt-4 inline-flex items-center gap-2 text-xs font-bold px-4 py-2 rounded-xl bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
                      >
                        <Plus size={14} /> New Chat
                      </button>
                    </motion.div>
                  ) : (
                    recentThreads.slice(0, 6).map((thread, index) => (
                      <ConversationRow key={thread.id} thread={thread} index={index} />
                    ))
                  )}
                </div>

                <motion.button
                  onClick={() => router.push('/operation')}
                  className="w-full flex items-center justify-center gap-2 py-3 mt-4 text-xs font-bold text-white/50 hover:text-white transition-colors rounded-xl border border-dashed border-white/10 hover:border-white/30"
                >
                  View All Chats <ArrowRight size={14} />
                </motion.button>
              </div>

              {/* Quick Stats */}
              <div className="p-6 rounded-2xl border border-white/10 bg-white/5">
                <h3 className="text-xs font-black text-muted-foreground tracking-widest uppercase mb-4">
                  Quick Stats
                </h3>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-white/70">Total Chats</span>
                    <span className="text-lg font-black text-indigo-400">{stats?.total_threads ?? 0}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-white/70">Messages Today</span>
                    <span className="text-lg font-black text-emerald-400">{stats?.messages_today ?? 0}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-white/70">Active Threads</span>
                    <span className="text-lg font-black text-white">{stats?.active_threads ?? 0}</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Column 3: Calendar & Knowledge */}
            <div className="space-y-6">
              {/* Today's Schedule */}
              <div className="p-6 rounded-2xl border border-white/10 bg-white/5">
                <h3 className="text-xs font-black text-muted-foreground tracking-widest uppercase mb-4">
                  Today's Schedule
                </h3>
                <div className="space-y-3">
                  <div className="text-center py-6">
                    <Timer className="w-8 h-8 text-white/20 mx-auto mb-2" />
                    <p className="text-sm font-medium text-white/50">No scheduled missions</p>
                    <p className="text-xs text-white/30 mt-1">Missions with scheduled_start will appear here</p>
                  </div>
                </div>
              </div>

              {/* Knowledge Base */}
              <div className="p-6 rounded-2xl border border-purple-500/30 bg-gradient-to-br from-purple-500/10 to-purple-500/5">
                <h3 className="text-xs font-black text-muted-foreground tracking-widest uppercase mb-4">
                  Knowledge Base
                </h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-white/70">Documents Ready</span>
                    <span className="text-2xl font-black text-emerald-400">{stats?.ready_documents ?? 0}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-white/70">Processing</span>
                    <span className="text-lg font-black text-amber-400">
                      {(stats?.total_documents ?? 0) - (stats?.ready_documents ?? 0)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-white/70">Total Docs</span>
                    <span className="text-lg font-black text-white">{stats?.total_documents ?? 0}</span>
                  </div>
                  <button
                    onClick={() => router.push('/knowledge')}
                    className="w-full mt-4 px-4 py-2 rounded-xl bg-purple-500/20 hover:bg-purple-500/30 border border-purple-500/50 text-sm font-bold text-purple-300 transition-colors"
                  >
                    Manage Knowledge
                  </button>
                </div>
              </div>

              {/* Connected Contexts */}
              <div className="p-6 rounded-2xl border border-white/10 bg-white/5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xs font-black text-muted-foreground tracking-widest uppercase">
                    Connected Contexts
                  </h3>
                  <span className="text-[10px] text-white/30 font-bold uppercase tracking-widest">
                    Coming Soon
                  </span>
                </div>
                <div className="space-y-3">
                  {[
                    { name: 'VS Code', icon: Code, active: false },
                    { name: 'Browser', icon: Globe, active: false },
                    { name: 'Spotify', icon: Music, active: false },
                  ].map((app, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/5 opacity-50"
                    >
                      <app.icon size={16} className="text-muted-foreground" />
                      <span className="text-sm font-medium text-muted-foreground">{app.name}</span>
                      <span className="ml-auto text-xs text-white/40">Not connected</span>
                    </div>
                  ))}
                </div>
                <p className="text-[10px] text-white/30 mt-4">
                  💡 Future: Real-time app detection
                </p>
              </div>
            </div>
          </div>

          </div>
        </div>

        {/* ─── Floating System Player ─── */}
        <div className="absolute bottom-6 left-0 right-0 z-[100] pointer-events-none flex justify-center">
          <div className="w-full max-w-6xl px-4 lg:px-8">
            <SystemOperationPlayer />
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Helper Components ────────────────────────────────────────────────────

function StatMini({ label, value, icon, highlight = false }: {
  label: string
  value: number
  icon: React.ReactNode
  highlight?: boolean
}) {
  return (
    <div className={cn(
      "flex items-center gap-2 px-3 py-2 rounded-lg transition-colors",
      highlight ? "bg-emerald-500/10 border border-emerald-500/30" : "bg-white/5"
    )}>
      <div className={cn(
        "text-muted-foreground",
        highlight && "text-emerald-400"
      )}>
        {icon}
      </div>
      <div>
        <div className={cn(
          "text-lg font-black",
          highlight ? "text-emerald-400" : "text-white"
        )}>
          {value}
        </div>
        <div className="text-[9px] font-bold text-white/40 uppercase tracking-widest">
          {label}
        </div>
      </div>
    </div>
  )
}

function ConversationRow({ thread, index }: { thread: ThreadStat; index: number }) {
  const router = useRouter()
  const isActive = thread.status === 'active'
  const date = new Date(thread.updated_at)
  const timeAgo = getTimeAgo(date)

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      whileHover={{ x: 4 }}
      onClick={() => router.push(`/operation?thread=${thread.id}`)}
      className={cn(
        "group flex items-center gap-4 px-5 py-4 rounded-xl border cursor-pointer transition-all hover:shadow-md",
        isActive
          ? "bg-indigo-500/10 border-indigo-500/30"
          : "bg-white/5 border-white/10 hover:border-white/30"
      )}
    >
      {/* Status dot */}
      <div className={cn(
        "w-2.5 h-2.5 rounded-full shrink-0 shadow-[0_0_8px_currentColor]",
        isActive ? "bg-emerald-400 animate-pulse text-emerald-400" : "bg-white/30 text-white/30"
      )} />

      {/* Title + meta */}
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-bold truncate text-white group-hover:text-primary transition-colors">
          {thread.title ?? 'Untitled Conversation'}
        </h3>
        <div className="flex items-center gap-3 mt-1">
          <span className="text-[10px] text-white/50 font-bold uppercase tracking-wider">
            {thread.message_count} message{thread.message_count !== 1 ? 's' : ''}
          </span>
          <span className="text-[10px] text-white/30">•</span>
          <span className="text-[10px] text-white/60 font-medium tracking-wide">{timeAgo}</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="hidden sm:flex items-center gap-3 shrink-0">
        <div className="w-16 h-1.5 rounded-full overflow-hidden bg-black/40">
          <div
            className={cn(
              "h-full rounded-full transition-all",
              isActive ? "bg-indigo-400" : "bg-white/40"
            )}
            style={{ width: `${thread.progress}%` }}
          />
        </div>
        <span className="text-[10px] font-black tracking-widest text-white/50 w-8 text-right">{thread.progress}%</span>
      </div>

      {/* Arrow */}
      <ArrowRight size={16} className={cn(
        "transition-colors shrink-0",
        isActive ? "text-indigo-400 group-hover:text-indigo-300" : "text-white/30 group-hover:text-white/70"
      )} />
    </motion.div>
  )
}

// ── Upcoming Deadlines widget (real mission data) ────────────────────────

function formatTimeRemaining(deadline: Date): string {
  const now = new Date()
  const diffMs = deadline.getTime() - now.getTime()
  if (diffMs <= 0) return 'Expired'
  const hours = Math.floor(diffMs / (1000 * 60 * 60))
  const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))
  if (hours >= 24) {
    const days = Math.floor(hours / 24)
    return `${days}d ${hours % 24}h`
  }
  return `${hours}h ${minutes}m`
}

function getUrgencyColor(deadline: Date): string {
  const diffMs = deadline.getTime() - new Date().getTime()
  const hours = diffMs / (1000 * 60 * 60)
  if (hours <= 3) return 'text-red-500'
  if (hours <= 12) return 'text-amber-500'
  return 'text-emerald-500'
}

const PRIORITY_COLORS: Record<string, string> = {
  critical: 'bg-red-500/10 text-red-600 dark:text-red-400',
  normal: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
  low: 'bg-slate-500/10 text-slate-600 dark:text-slate-400',
}

function UpcomingDeadlines() {
  const router = useRouter()
  const { missions, loading: missionsLoading, fetchMissions } = useMissionStore()

  React.useEffect(() => { fetchMissions() }, [fetchMissions])

  // Filter to active missions with deadlines, sorted soonest-first, limit 6
  const deadlineMissions = React.useMemo(() => {
    return missions
      .filter((m) => m.status === 'active' && m.deadline)
      .sort((a, b) => new Date(a.deadline!).getTime() - new Date(b.deadline!).getTime())
      .slice(0, 6)
  }, [missions])

  if (missionsLoading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
      </div>
    )
  }

  if (deadlineMissions.length === 0) {
    return (
      <div className="flex flex-col flex-1">
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center py-10 rounded-2xl border border-white/10 bg-white/5 flex-1 flex flex-col items-center justify-center"
        >
          <CheckCircle2 className="w-8 h-8 text-emerald-500/40 mx-auto mb-3" />
          <p className="text-sm font-bold text-white/90">All caught up!</p>
          <p className="text-xs text-white/50 mt-1">No upcoming deadlines</p>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1">
      <div className="space-y-3 flex-1 overflow-y-auto pr-2 custom-scrollbar max-h-[400px]">
        {deadlineMissions.map((mission, index) => {
          const deadline = new Date(mission.deadline!)
          return (
            <motion.div
              key={mission.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
              whileHover={{ x: 4 }}
              onClick={() => router.push('/mission')}
              className={cn(
                "group flex items-center gap-4 px-5 py-4 rounded-xl border cursor-pointer transition-all hover:shadow-md",
                "bg-white/5 border-white/10 hover:border-amber-500/50"
              )}
            >
              {/* Priority badge */}
              <div className={cn(
                "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 border border-white/5",
                mission.priority === 'critical' ? "bg-red-500/20 text-red-400" : mission.priority === 'low' ? "bg-white/10 text-white/60" : "bg-amber-500/20 text-amber-400"
              )}>
                <Target size={18} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-bold truncate text-white group-hover:text-amber-400 transition-colors">
                  {mission.title}
                </h3>
                <div className="flex items-center gap-2 mt-1">
                  <span className={cn(
                    "text-[9px] font-black uppercase px-2 py-0.5 rounded-sm tracking-widest bg-black/40",
                    PRIORITY_COLORS[mission.priority] ?? PRIORITY_COLORS.normal
                  )}>
                    {mission.priority}
                  </span>
                  {mission.category && (
                    <span className="text-[10px] text-white/50 font-bold uppercase tracking-wider">{mission.category}</span>
                  )}
                  {mission.progress > 0 && (
                    <>
                      <span className="text-[10px] text-white/30">•</span>
                      <span className="text-[10px] text-white/60 font-bold">{mission.progress}%</span>
                    </>
                  )}
                </div>
              </div>

              {/* Time remaining */}
              <div className="flex flex-col items-end shrink-0 pl-2">
                <div className="flex items-center gap-1.5 opacity-80 mb-1">
                  <Timer size={12} className={getUrgencyColor(deadline)} />
                  <span className={cn("text-xs font-black tracking-wide", getUrgencyColor(deadline))}>
                    {formatTimeRemaining(deadline)}
                  </span>
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}

// ── Helper Components ──────────────────────────────────────────────────────

function StatsCard({ label, value, trend, color }: {
  label: string
  value: number | string
  trend: string
  color: 'indigo' | 'emerald' | 'purple' | 'amber'
}) {
  const colorClasses = {
    indigo: 'from-indigo-500/20 to-indigo-500/5 border-indigo-500/30 text-indigo-400',
    emerald: 'from-emerald-500/20 to-emerald-500/5 border-emerald-500/30 text-emerald-400',
    purple: 'from-purple-500/20 to-purple-500/5 border-purple-500/30 text-purple-400',
    amber: 'from-amber-500/20 to-amber-500/5 border-amber-500/30 text-amber-400',
  }

  return (
    <div className={cn(
      "p-5 rounded-2xl border bg-gradient-to-br",
      colorClasses[color]
    )}>
      <div className="text-[10px] font-black uppercase tracking-widest text-white/60 mb-2">
        {label}
      </div>
      <div className="text-3xl font-black text-white mb-1">
        {value}
      </div>
      <div className="text-[10px] font-medium text-white/50">
        {trend}
      </div>
    </div>
  )
}

function StatusBar({ label, value, color }: {
  label: string
  value: number
  color: 'emerald' | 'indigo' | 'purple'
}) {
  const colorClasses = {
    emerald: 'bg-emerald-400',
    indigo: 'bg-indigo-400',
    purple: 'bg-purple-400',
  }

  return (
    <div>
      <div className="flex justify-between items-end mb-1.5">
        <span className="text-xs font-bold text-white/70">{label}</span>
        <span className="text-xs font-black text-white">{value}%</span>
      </div>
      <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all", colorClasses[color])}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  )
}

// ── Helper Functions ──────────────────────────────────────────────────────

function getTimeAgo(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.floor(diffHr / 24)
  if (diffDay < 7) return `${diffDay}d ago`
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

function getTimeGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

function formatTime(ms: number): string {
  const minutes = Math.floor(ms / (60 * 1000))
  const hours = Math.floor(minutes / 60)
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`
  }
  return `${minutes}m`
}
