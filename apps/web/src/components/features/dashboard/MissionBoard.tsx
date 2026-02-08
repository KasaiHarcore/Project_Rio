import React from 'react'
import { motion } from 'framer-motion'
import { Plus, Clock, AlertCircle, CheckCircle2, ArrowRight, Activity, Play, Archive, Edit3, Trash2 } from 'lucide-react'
import { useUIStore } from '@/store/ui-store'
import { MOCK_MISSIONS, Mission, MissionStatus } from '@/types/mission'
import { cn } from '@/lib/utils'
import { CharacterSelector } from './CharacterSelector'
import { useTheme } from '@/components/providers/theme-provider'
import { getCycleConfig } from '@/lib/cycle-config'
import { BentoCard } from '@/components/ui/bento-card'
import { AnimatedCounter } from '@/components/ui/animated-counter'
import { SparklineChart } from '@/components/ui/sparkline-chart'
import { ProgressRing } from '@/components/ui/progress-ring'
import { ContextMenu, type ContextMenuEntry } from '@/components/ui/context-menu'
import { toast } from '@/hooks/use-toast'

export function MissionBoard() {
  const startMission = useUIStore((state) => state.startMission)
  const { theme } = useTheme()
  const config = getCycleConfig(theme)

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-8 relative z-10 w-full max-w-7xl mx-auto">
      {/* Header Section */}
      <div className="mb-12 relative flex items-start justify-between">
        <div>
            <div className="absolute -left-4 -top-4 w-20 h-20 border-l-2 border-t-2 rounded-tl-3xl pointer-events-none transition-colors border-[var(--dash-corner-border)]"></div>
            <h1 className="text-4xl font-black tracking-tight text-dash-title">
            SCHALE <span className={cn("transition-colors", config.colors.text)}>OFFICE</span>
            </h1>
            <div className="flex items-center gap-4 mt-2 text-slate-500 font-medium">
            <span className={cn("flex items-center gap-2 text-xs font-bold tracking-widest uppercase px-2 py-1 rounded transition-colors", config.colors.badgeBg, config.colors.badgeText )}>
                SYS.VER.3.0
            </span>
            <span className="text-sm text-dash-subtitle">Welcome back, Sensei. There are {MOCK_MISSIONS.filter(m => m.status === 'ACTIVE').length} active tasks pending.</span>
            </div>
        </div>

        {/* Character Selector Widget */}
        <CharacterSelector />
      </div>

      {/* Quick Action & Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
        {/* System Load — ProgressRing */}
        <BentoCard>
            <div className="flex justify-between items-start mb-3">
                <span className="text-[10px] font-black tracking-widest text-slate-500 uppercase">System Load</span>
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            </div>
            <div className="flex items-center gap-4">
                <ProgressRing
                  value={12}
                  size={56}
                  strokeWidth={5}
                  progressColor="#10b981"
                >
                  <span className="text-xs font-black text-bento-value">12%</span>
                </ProgressRing>
                <div className="flex-1 min-w-0">
                  <AnimatedCounter
                    value={12}
                    suffix="%"
                    className="text-2xl font-black text-bento-value"
                    suffixClassName="text-xs font-bold text-slate-500 ml-0.5"
                  />
                  <p className="text-[10px] text-slate-500 font-bold mt-0.5">Nominal</p>
                </div>
            </div>
        </BentoCard>
        
        {/* Token Usage — Sparkline */}
        <BentoCard>
            <div className="flex justify-between items-start mb-3">
                <span className="text-[10px] font-black tracking-widest text-slate-500 uppercase">Token Usage</span>
                <Activity size={14} className="text-slate-500" />
            </div>
            <AnimatedCounter
              value={2.4}
              decimals={1}
              suffix="K"
              className="text-2xl font-black text-bento-value"
              suffixClassName="text-xs font-bold text-slate-500 ml-0.5"
            />
            <div className="mt-3">
              <SparklineChart
                data={[1.1, 1.4, 0.9, 1.8, 2.1, 1.6, 2.4]}
                width={140}
                height={28}
                color="var(--bento-bar-fill, #3b82f6)"
              />
            </div>
        </BentoCard>

        {/* Active Agents — Animated Counter with segmented bar */}
        <BentoCard>
            <div className="flex justify-between items-start mb-3">
                <span className="text-[10px] font-black tracking-widest text-slate-500 uppercase">Active Agents</span>
            </div>
            <div className="flex items-baseline gap-0.5">
              <AnimatedCounter
                value={1}
                className="text-2xl font-black text-bento-value"
              />
              <span className="text-sm font-bold text-slate-500">/ 03</span>
            </div>
            <div className="flex gap-1.5 mt-3">
                {[1, 2, 3].map((i) => (
                    <motion.div
                      key={i}
                      className={cn(
                        "h-1.5 flex-1 rounded-full",
                        i <= 1 ? "bg-bento-bar-fill" : "bg-bento-bar-track"
                      )}
                      initial={{ scaleX: 0 }}
                      animate={{ scaleX: 1 }}
                      transition={{ duration: 0.5, delay: 0.3 + i * 0.1, ease: "easeOut" }}
                      style={{ transformOrigin: "left" }}
                    />
                ))}
            </div>
        </BentoCard>

        {/* Login Streak — Animated Counter with streak dots */}
        <BentoCard>
            <div className="flex justify-between items-start mb-3">
                <span className="text-[10px] font-black tracking-widest text-slate-500 uppercase">Login Streak</span>
            </div>
            <AnimatedCounter
              value={14}
              suffix=" DAYS"
              className="text-2xl font-black text-bento-value"
              suffixClassName="text-xs font-bold text-slate-500 ml-0.5"
            />
            <div className="flex items-center gap-1 mt-3">
              {Array.from({ length: 7 }).map((_, i) => (
                <motion.div
                  key={i}
                  className="h-1.5 w-1.5 rounded-full bg-emerald-500"
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ delay: 0.5 + i * 0.08, duration: 0.3, type: "spring" }}
                />
              ))}
              <span className="text-[10px] font-bold text-emerald-500 ml-1.5">Active</span>
            </div>
        </BentoCard>
      </div>

      {/* Mission List */}
      <h2 className="text-lg font-black mb-6 flex items-center gap-2 text-foreground">
        <span className="w-1.5 h-6 rounded-full transition-colors bg-primary"></span>
        CURRENT MISSIONS
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {MOCK_MISSIONS.map((mission) => (
          <MissionCard key={mission.id} mission={mission} />
        ))}
      </div>
    </div>
  )
}

function MissionCard({ mission }: { mission: Mission }) {
    const startMission = useUIStore((state) => state.startMission)

    const missionContextMenu: ContextMenuEntry[] = [
        { id: "start", label: mission.status === 'ACTIVE' ? "Resume Mission" : "Start Mission", icon: <Play size={14} />, action: () => startMission(mission.id) },
        { id: "edit", label: "Edit Mission", icon: <Edit3 size={14} />, action: () => toast({ title: `Editing: ${mission.title}` }) },
        { type: "divider" },
        { id: "archive", label: "Archive", icon: <Archive size={14} />, action: () => toast({ title: "Mission archived" }) },
        { id: "delete", label: "Delete Mission", icon: <Trash2 size={14} />, danger: true, action: () => toast({ title: "Mission deleted", variant: "error" }) },
    ]

    return (
        <ContextMenu items={missionContextMenu}>
        <motion.div 
            whileHover={{ y: -2 }}
            className={cn(
                "group relative overflow-hidden rounded-xl border p-6 transition-all hover:shadow-lg backdrop-blur-sm",
                mission.status === 'ACTIVE' 
                    ? "bg-[var(--mission-active-bg)] border-[var(--mission-active-border)] ring-1 ring-[var(--mission-active-border)]"
                    : "bg-[var(--mission-inactive-bg)] border-[var(--mission-inactive-border)] hover:border-border"
            )}
            style={mission.status === 'ACTIVE' ? { boxShadow: `0 4px 20px var(--mission-active-shadow, transparent)` } : undefined}
        >
             {mission.status === 'ACTIVE' && (
                <div className="absolute top-0 right-0 px-3 py-1 text-white text-[10px] font-bold rounded-bl-xl z-20 bg-[var(--mission-active-badge-bg)]">
                    ACTIVE
                </div>
            )}

            <div className="flex justify-between items-start mb-4">
                <div className="space-y-1">
                     <div className="flex gap-2 mb-2">
                        {mission.tags.map(tag => (
                            <span key={tag} className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase border bg-[var(--mission-tag-bg)] text-[var(--mission-tag-text)] border-[var(--mission-tag-border)]">
                                {tag}
                            </span>
                        ))}
                    </div>
                    <h3 className="text-lg font-bold transition-colors text-[var(--mission-title)] group-hover:text-[var(--mission-title-hover)]">
                        {mission.title}
                    </h3>
                </div>
                <div className="p-2 rounded-lg transition-colors bg-[var(--mission-status-bg)] text-[var(--mission-status-text)] group-hover:bg-[var(--mission-status-hover-bg)] group-hover:text-[var(--mission-status-hover-text)]">
                     {getStatusIcon(mission.status)}
                </div>
            </div>

            <p className="text-sm text-muted-foreground mb-6 line-clamp-2">
                {mission.description}
            </p>

            <div className="flex items-center justify-between mt-auto pt-4 border-t border-[var(--mission-footer-border)]">
                <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider">Progress</span>
                    <div className="flex items-center gap-2 mt-1">
                        <div className="w-24 h-1.5 rounded-full overflow-hidden bg-[var(--mission-progress-track)]">
                            <div 
                                className="h-full rounded-full transition-all duration-1000 bg-[var(--mission-progress-fill)]"
                                style={{ width: `${mission.progress || 0}%` }}
                            ></div>
                        </div>
                        <span className="text-xs font-bold text-[var(--mission-progress-text)]">{mission.progress}%</span>
                    </div>
                </div>

                <button 
                    onClick={() => startMission(mission.id)}
                    className="flex items-center gap-1.5 text-xs font-bold transition-colors px-3 py-1.5 rounded-lg text-[var(--mission-resume-text)] hover:text-[var(--mission-resume-hover-text)] hover:bg-[var(--mission-resume-hover-bg)]"
                >
                    RESUME <ArrowRight className="w-3.5 h-3.5" />
                </button>
            </div>
        </motion.div>
        </ContextMenu>
    )
}

function getStatusIcon(status: MissionStatus) {
    switch(status) {
        case 'ACTIVE': return <Clock className="w-5 h-5" />;
        case 'COMPLETED': return <CheckCircle2 className="w-5 h-5" />;
        case 'DRAFT': return <AlertCircle className="w-5 h-5" />;
        default: return <Clock className="w-5 h-5" />;
    }
}
