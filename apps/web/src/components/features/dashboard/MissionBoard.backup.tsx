import React, { useEffect, useState, useCallback, useMemo } from 'react'
import { motion } from 'framer-motion'
import { Plus, Clock, CheckCircle2, ArrowRight, Activity, MessageSquare, Upload, BookOpen, Loader2, Sparkles, Star, Target, Timer } from 'lucide-react'
import { cn } from '@/lib/utils'
import { BentoCard } from '@/components/ui/bento-card'
import { AnimatedCounter } from '@/components/ui/animated-counter'
import { SparklineChart } from '@/components/ui/sparkline-chart'
import { ProgressRing } from '@/components/ui/progress-ring'
import { apiGetDashboardStats, DashboardStats, ThreadStat } from '@/lib/api'
import { useRouter } from 'next/navigation'
import { useMissionStore, Mission } from '@/store/mission-store'

export function MissionBoard() {
  const router = useRouter()

  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchStats = useCallback(async () => {
    try {
      setLoading(true)
      const data = await apiGetDashboardStats()
      setStats(data)
    } catch {
      // fallback: keep null, show zeros
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchStats() }, [fetchStats])

  // Derive display values from real stats (fallback to 0)
  const activeThreads = stats?.active_threads ?? 0
  const totalThreads = stats?.total_threads ?? 0
  const totalMessages = stats?.total_messages ?? 0
  const totalDocuments = stats?.total_documents ?? 0
  const messagesToday = stats?.messages_today ?? 0
  const messagesByDay = stats?.messages_by_day ?? [0, 0, 0, 0, 0, 0, 0]
  const recentThreads = stats?.recent_threads ?? []
  const level = stats?.level ?? 1
  const totalXp = stats?.total_xp ?? 0
  const xpInLevel = stats?.xp_in_level ?? 0
  const xpForNext = stats?.xp_for_next ?? 100
  const xpProgress = xpForNext > 0 ? Math.round((xpInLevel / xpForNext) * 100) : 0

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-8 relative z-10 w-full max-w-7xl mx-auto">
      {/* Header Section */}
      <div className="mb-10 relative flex items-start justify-between">
        <div>
          <div className="absolute -left-4 -top-4 w-20 h-20 border-l-2 border-t-2 rounded-tl-3xl pointer-events-none transition-colors border-[var(--dash-corner-border)]"></div>
          <h1 className="text-4xl font-black tracking-tight text-dash-title">
            SCHALE <span className={cn("transition-colors", "text-rose-500")}>OFFICE</span>
          </h1>
          <div className="flex items-center gap-4 mt-2 text-slate-500 font-medium">
            <span className={cn("flex items-center gap-2 text-xs font-bold tracking-widest uppercase px-2 py-1 rounded transition-colors", "bg-rose-900/40", "text-rose-400")}>
              LV.{level}
            </span>
            <span className="text-sm text-dash-subtitle">System Operational. {activeThreads > 0 ? `${activeThreads} active operations${activeThreads > 1 ? 's' : ''} in progress.` : 'Logic consistency verified.'}</span>
          </div>
        </div>
      </div>

      {/* ═══ Section 1: Quick Actions ═══ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-10">
        <motion.button
          whileHover={{ y: -2 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => router.push('/knowledge')}
          className="flex items-center gap-3 px-5 py-4 rounded-xl border-2 border-dashed transition-colors bg-[var(--bento-bg)] border-[var(--bento-border)] hover:border-emerald-400 hover:bg-emerald-50/50 dark:hover:bg-emerald-950/20 group"
        >
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
            <Upload size={20} className="text-emerald-500" />
          </div>
          <div className="text-left">
            <span className="text-sm font-bold text-foreground block">Upload Document</span>
            <span className="text-[10px] text-muted-foreground font-medium">Add to knowledge base</span>
          </div>
        </motion.button>

        <motion.button
          whileHover={{ y: -2 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => router.push('/knowledge')}
          className="flex items-center gap-3 px-5 py-4 rounded-xl border-2 border-dashed transition-colors bg-[var(--bento-bg)] border-[var(--bento-border)] hover:border-violet-400 hover:bg-violet-50/50 dark:hover:bg-violet-950/20 group"
        >
          <div className="w-10 h-10 rounded-lg bg-violet-500/10 flex items-center justify-center group-hover:bg-violet-500/20 transition-colors">
            <BookOpen size={20} className="text-violet-500" />
          </div>
          <div className="text-left">
            <span className="text-sm font-bold text-foreground block">Knowledge Base</span>
            <span className="text-[10px] text-muted-foreground font-medium">{totalDocuments} document{totalDocuments !== 1 ? 's' : ''} indexed</span>
          </div>
        </motion.button>
      </div>

      {/* ═══ Section 2: Activity Overview ═══ */}
      <h2 className="text-xs font-black tracking-widest text-muted-foreground uppercase mb-4">
        Activity Overview
      </h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        {/* Level / XP Progress */}
        <BentoCard>
          <div className="flex justify-between items-start mb-3">
            <span className="text-[10px] font-black tracking-widest text-muted-foreground uppercase">Level</span>
            <Star size={14} className="text-amber-500" />
          </div>
          <div className="flex items-center gap-4">
            <ProgressRing
              value={xpProgress}
              size={56}
              strokeWidth={5}
              progressColor="var(--header-level-ring, #f59e0b)"
            >
              <span className="text-sm font-black text-bento-value">{level}</span>
            </ProgressRing>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-bold text-muted-foreground">
                {xpInLevel} / {xpForNext} XP
              </div>
              <div className="w-full h-1.5 rounded-full overflow-hidden mt-1.5 bg-slate-200/30">
                <motion.div
                  className="h-full rounded-full bg-amber-500"
                  initial={{ width: 0 }}
                  animate={{ width: `${xpProgress}%` }}
                  transition={{ duration: 1, ease: "easeOut" }}
                />
              </div>
              <p className="text-[10px] text-slate-500 font-bold mt-1">{totalXp} total XP</p>
            </div>
          </div>
        </BentoCard>

        {/* Message Activity — Sparkline */}
        <BentoCard>
          <div className="flex justify-between items-start mb-3">
            <span className="text-[10px] font-black tracking-widest text-muted-foreground uppercase">Messages</span>
            <Activity size={14} className="text-slate-500" />
          </div>
          <AnimatedCounter
            value={totalMessages}
            className="text-2xl font-black text-bento-value"
          />
          <div className="mt-3">
            <SparklineChart
              data={messagesByDay}
              width={140}
              height={28}
              color="var(--bento-bar-fill, #3b82f6)"
            />
          </div>
        </BentoCard>

        {/* Active Threads */}
        <BentoCard>
          <div className="flex justify-between items-start mb-3">
            <span className="text-[10px] font-black tracking-widest text-muted-foreground uppercase">Active Threads</span>
          </div>
          <div className="flex items-baseline gap-0.5">
            <AnimatedCounter
              value={activeThreads}
              className="text-2xl font-black text-bento-value"
            />
            <span className="text-sm font-bold text-slate-500">/ {String(totalThreads).padStart(2, '0')}</span>
          </div>
          <div className="flex gap-1.5 mt-3">
            {Array.from({ length: Math.max(totalThreads, 3) }).slice(0, 5).map((_, i) => (
              <motion.div
                key={i}
                className={cn(
                  "h-1.5 flex-1 rounded-full",
                  i < activeThreads ? "bg-bento-bar-fill" : "bg-bento-bar-track"
                )}
                initial={{ scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: 0.5, delay: 0.3 + i * 0.1, ease: "easeOut" }}
                style={{ transformOrigin: "left" }}
              />
            ))}
          </div>
        </BentoCard>

        {/* Knowledge Base */}
        <BentoCard>
          <div className="flex justify-between items-start mb-3">
            <span className="text-[10px] font-black tracking-widest text-muted-foreground uppercase">Knowledge Base</span>
          </div>
          <AnimatedCounter
            value={totalDocuments}
            suffix=" DOCS"
            className="text-2xl font-black text-bento-value"
            suffixClassName="text-xs font-bold text-slate-500 ml-0.5"
          />
          <div className="flex items-center gap-1 mt-3">
            {Array.from({ length: Math.min(totalDocuments, 7) }).map((_, i) => (
              <motion.div
                key={i}
                className="h-1.5 w-1.5 rounded-full bg-emerald-500"
                initial={{ scale: 0, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                transition={{ delay: 0.5 + i * 0.08, duration: 0.3, type: "spring" }}
              />
            ))}
            <span className="text-[10px] font-bold text-emerald-500 ml-1.5">{totalDocuments > 0 ? 'Indexed' : 'Empty'}</span>
          </div>
        </BentoCard>
      </div>

      {/* ═══ Section 3: Recent Conversations + Upcoming Deadlines ═══ */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
        {/* Left Half: Recent Conversations */}
        <div className="flex flex-col">
          <h2 className="text-xs font-black tracking-widest text-muted-foreground uppercase mb-4 flex items-center gap-2">
            <span className="w-1 h-4 rounded-full transition-colors bg-primary"></span>
            Recent Conversations
          </h2>

          <div className="space-y-2 flex-1 overflow-y-auto pr-1 custom-scrollbar">
            {loading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-slate-400" />
              </div>
            ) : recentThreads.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-10 rounded-xl border border-dashed bg-[var(--bento-bg)] border-[var(--bento-border)]"
              >
                <Sparkles className="w-8 h-8 text-muted-foreground/40 mx-auto mb-3" />
                <p className="text-sm font-bold text-muted-foreground">No conversations yet</p>
                <p className="text-xs text-muted-foreground/60 mt-1">Start a new chat to begin earning XP!</p>
                <button
                  onClick={() => router.push('/operation?new=true')}
                  className="mt-4 inline-flex items-center gap-1.5 text-xs font-bold px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:opacity-90 transition-opacity"
                >
                  <Plus size={14} /> New Chat
                </button>
              </motion.div>
            ) : (
              recentThreads.map((thread, index) => (
                <ConversationRow key={thread.id} thread={thread} index={index} />
              ))
            )}
          </div>

          {/* Link to full operation page */}
          <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            onClick={() => router.push('/operation')}
            className="w-full flex items-center justify-center gap-2 py-3 mt-2 text-xs font-bold text-muted-foreground hover:text-primary transition-colors rounded-xl border border-dashed border-[var(--bento-border)] hover:border-primary/30"
          >
            View All Chats <ArrowRight size={14} />
          </motion.button>
        </div>

        {/* Right Half: Upcoming Mission Deadlines */}
        <div className="flex flex-col">
          <h2 className="text-xs font-black tracking-widest text-muted-foreground uppercase mb-4 flex items-center gap-2">
            <span className="w-1 h-4 rounded-full transition-colors bg-amber-500"></span>
            Upcoming Deadlines
          </h2>

          <UpcomingDeadlines />
        </div>
      </div>
    </div>
  )
}

// ── Upcoming Deadlines widget (real mission data) ────────────────────

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

  useEffect(() => { fetchMissions() }, [fetchMissions])

  // Filter to active missions with deadlines, sorted soonest-first, limit 6
  const deadlineMissions = useMemo(() => {
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
          className="text-center py-10 rounded-xl border border-dashed bg-[var(--bento-bg)] border-[var(--bento-border)] flex-1 flex flex-col items-center justify-center"
        >
          <CheckCircle2 className="w-8 h-8 text-emerald-500/40 mx-auto mb-3" />
          <p className="text-sm font-bold text-muted-foreground">All caught up!</p>
          <p className="text-xs text-muted-foreground/60 mt-1">No upcoming deadlines</p>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1">
      <div className="space-y-2 flex-1 overflow-y-auto pr-1 custom-scrollbar">
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
                "group flex items-center gap-3 px-4 py-3 rounded-xl border cursor-pointer transition-all hover:shadow-md",
                "bg-[var(--bento-bg)] border-[var(--bento-border)] hover:border-amber-300 dark:hover:border-amber-700"
              )}
            >
              {/* Priority badge */}
              <div className={cn(
                "w-9 h-9 rounded-lg flex items-center justify-center shrink-0",
                mission.priority === 'critical' ? "bg-red-500/10" : mission.priority === 'low' ? "bg-slate-500/10" : "bg-amber-500/10"
              )}>
                <Target size={16} className={mission.priority === 'critical' ? "text-red-500" : mission.priority === 'low' ? "text-slate-500" : "text-amber-500"} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-bold truncate text-foreground group-hover:text-amber-600 dark:group-hover:text-amber-400 transition-colors">
                  {mission.title}
                </h3>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className={cn(
                    "text-[10px] font-bold uppercase px-1.5 py-0.5 rounded",
                    PRIORITY_COLORS[mission.priority] ?? PRIORITY_COLORS.normal
                  )}>
                    {mission.priority}
                  </span>
                  {mission.category && (
                    <span className="text-[10px] text-muted-foreground font-medium">{mission.category}</span>
                  )}
                  {mission.progress > 0 && (
                    <>
                      <span className="text-[10px] text-muted-foreground/50">•</span>
                      <span className="text-[10px] text-muted-foreground font-medium">{mission.progress}%</span>
                    </>
                  )}
                </div>
              </div>

              {/* Time remaining */}
              <div className="flex items-center gap-1.5 shrink-0">
                <Timer size={12} className={getUrgencyColor(deadline)} />
                <span className={cn("text-xs font-bold", getUrgencyColor(deadline))}>
                  {formatTimeRemaining(deadline)}
                </span>
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Link to full mission page */}
      <motion.button
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        onClick={() => router.push('/mission')}
        className="w-full flex items-center justify-center gap-2 py-3 mt-2 text-xs font-bold text-muted-foreground hover:text-primary transition-colors rounded-xl border border-dashed border-[var(--bento-border)] hover:border-primary/30"
      >
        View All Missions <ArrowRight size={14} />
      </motion.button>
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
          ? "bg-[var(--mission-active-bg)] border-[var(--mission-active-border)]"
          : "bg-[var(--bento-bg)] border-[var(--bento-border)] hover:border-border"
      )}
    >
      {/* Status dot */}
      <div className={cn(
        "w-2.5 h-2.5 rounded-full shrink-0",
        isActive ? "bg-emerald-500 animate-pulse" : "bg-slate-300"
      )} />

      {/* Title + meta */}
      <div className="flex-1 min-w-0">
        <h3 className="text-sm font-bold truncate text-foreground group-hover:text-primary transition-colors">
          {thread.title ?? 'Untitled Conversation'}
        </h3>
        <div className="flex items-center gap-3 mt-0.5">
          <span className="text-[10px] text-muted-foreground font-medium">
            {thread.message_count} message{thread.message_count !== 1 ? 's' : ''}
          </span>
          <span className="text-[10px] text-muted-foreground/50">•</span>
          <span className="text-[10px] text-muted-foreground font-medium">{timeAgo}</span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="hidden sm:flex items-center gap-2 shrink-0">
        <div className="w-16 h-1.5 rounded-full overflow-hidden bg-slate-200/30">
          <div
            className="h-full rounded-full transition-all bg-[var(--mission-progress-fill)]"
            style={{ width: `${thread.progress}%` }}
          />
        </div>
        <span className="text-[10px] font-bold text-muted-foreground w-8 text-right">{thread.progress}%</span>
      </div>

      {/* Arrow */}
      <ArrowRight size={16} className="text-muted-foreground/40 group-hover:text-primary transition-colors shrink-0" />
    </motion.div>
  )
}

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
