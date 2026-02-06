import React from 'react'
import { motion } from 'framer-motion'
import { Plus, Clock, AlertCircle, CheckCircle2, ArrowRight } from 'lucide-react'
import { useUIStore } from '@/store/ui-store'
import { MOCK_MISSIONS, Mission, MissionStatus } from '@/types/mission'
import { cn } from '@/lib/utils'
import { CharacterSelector } from './CharacterSelector'
import { useTheme } from '@/components/providers/theme-provider'
import { getCycleConfig } from '@/lib/cycle-config'

export function MissionBoard() {
  const startMission = useUIStore((state) => state.startMission)
  const { theme } = useTheme()
  const config = getCycleConfig(theme)
  const isNight = theme === 'dark'

  return (
    <div className="flex-1 overflow-y-auto p-8 relative z-10 w-full max-w-7xl mx-auto">
      {/* Header Section */}
      <div className="mb-12 relative flex items-start justify-between">
        <div>
            <div className={cn("absolute -left-4 -top-4 w-20 h-20 border-l-2 border-t-2 rounded-tl-3xl pointer-events-none transition-colors", isNight ? "border-rose-500/30" : "border-blue-200")}></div>
            <h1 className={cn("text-4xl font-black tracking-tight", isNight ? "text-white" : "text-slate-800")}>
            SCHALE <span className={cn("transition-colors", config.colors.text)}>OFFICE</span>
            </h1>
            <div className="flex items-center gap-4 mt-2 text-slate-500 font-medium">
            <span className={cn("flex items-center gap-2 text-xs font-bold tracking-widest uppercase px-2 py-1 rounded transition-colors", config.colors.badgeBg, config.colors.badgeText )}>
                SYS.VER.3.0
            </span>
            <span className={cn("text-sm", isNight ? "text-slate-400" : "text-slate-500")}>Welcome back, Sensei. There are {MOCK_MISSIONS.filter(m => m.status === 'ACTIVE').length} active tasks pending.</span>
            </div>
        </div>

        {/* Character Selector Widget */}
        <CharacterSelector />
      </div>

      {/* Quick Action & Status Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
        {/* Status Metrics moved to fill start */}
        {/* System Load */}
        <div className={cn("rounded-2xl border p-6 backdrop-blur-sm relative overflow-hidden transition-colors", isNight ? "bg-slate-900/50 border-white/10" : "bg-white/60 border-blue-100")}>
            <div className="flex justify-between items-start mb-4">
                <span className="text-[10px] font-black tracking-widest text-slate-400 uppercase">System Load</span>
                <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
            </div>
            <div className={cn("text-3xl font-black", isNight ? "text-white" : "text-slate-700")}>12<span className="text-sm font-bold text-slate-400 ml-1">%</span></div>
            <div className={cn("mt-4 w-full h-1 rounded-full overflow-hidden", isNight ? "bg-white/10" : "bg-slate-100")}>
                <div className="h-full bg-emerald-500 w-[12%]"></div>
            </div>
        </div>
        
        {/* Tokens */}
        <div className={cn("rounded-2xl border p-6 backdrop-blur-sm relative overflow-hidden transition-colors", isNight ? "bg-slate-900/50 border-white/10" : "bg-white/60 border-blue-100")}>
                <div className="flex justify-between items-start mb-4">
                <span className="text-[10px] font-black tracking-widest text-slate-400 uppercase">Token Usage</span>
            </div>
            <div className={cn("text-3xl font-black", isNight ? "text-white" : "text-slate-700")}>2.4<span className="text-sm font-bold text-slate-400 ml-1">K</span></div>
                <div className={cn("mt-4 w-full h-1 rounded-full overflow-hidden", isNight ? "bg-white/10" : "bg-slate-100")}>
                <div className={cn("h-full w-[45%] transition-colors", isNight ? "bg-rose-500" : "bg-blue-500")}></div>
            </div>
        </div>

        {/* Active Agents */}
        <div className={cn("rounded-2xl border p-6 backdrop-blur-sm relative overflow-hidden transition-colors", isNight ? "bg-slate-900/50 border-white/10" : "bg-white/60 border-blue-100")}>
                <div className="flex justify-between items-start mb-4">
                <span className="text-[10px] font-black tracking-widest text-slate-400 uppercase">Active Agents</span>
            </div>
            <div className={cn("text-3xl font-black", isNight ? "text-white" : "text-slate-700")}>01<span className="text-sm font-bold text-slate-400 ml-1">/ 03</span></div>
            <div className="flex gap-1 mt-4">
                    <div className={cn("h-1 flex-1 rounded-full transition-colors", isNight ? "bg-rose-500" : "bg-blue-500")}></div>
                    <div className={cn("h-1 flex-1 rounded-full", isNight ? "bg-white/10" : "bg-slate-200")}></div>
                    <div className={cn("h-1 flex-1 rounded-full", isNight ? "bg-white/10" : "bg-slate-200")}></div>
            </div>
        </div>

        {/* Total Time / Study Streak (New Metric to replace Button) */}
        <div className={cn("rounded-2xl border p-6 backdrop-blur-sm relative overflow-hidden transition-colors", isNight ? "bg-slate-900/50 border-white/10" : "bg-white/60 border-blue-100")}>
                <div className="flex justify-between items-start mb-4">
                <span className="text-[10px] font-black tracking-widest text-slate-400 uppercase">Login Streak</span>
            </div>
             <div className={cn("text-3xl font-black", isNight ? "text-white" : "text-slate-700")}>14<span className="text-sm font-bold text-slate-400 ml-1">DAYS</span></div>
             <div className="flex items-center gap-1 mt-4 text-[10px] font-bold text-slate-400">
                <CheckCircle2 size={12} className="text-emerald-500" /> All Clear
             </div>
        </div>
      </div>

      {/* Mission List */}
      <h2 className={cn("text-lg font-black mb-6 flex items-center gap-2", isNight ? "text-slate-200" : "text-slate-700")}>
        <span className={cn("w-1.5 h-6 rounded-full transition-colors", isNight ? "bg-rose-500" : "bg-blue-500")}></span>
        CURRENT MISSIONS
      </h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {MOCK_MISSIONS.map((mission) => (
          <MissionCard key={mission.id} mission={mission} isNight={isNight} />
        ))}
      </div>
    </div>
  )
}

function MissionCard({ mission, isNight }: { mission: Mission, isNight: boolean }) {
    const startMission = useUIStore((state) => state.startMission)

    return (
        <motion.div 
            whileHover={{ y: -2 }}
            className={cn(
                "group relative overflow-hidden rounded-xl border p-6 transition-all hover:shadow-lg backdrop-blur-sm",
                isNight
                    ? (mission.status === 'ACTIVE' 
                        ? "bg-slate-800/80 border-rose-500/30 shadow-none ring-1 ring-rose-500/20" 
                        : "bg-slate-900/40 border-white/5 hover:border-white/10")
                    : (mission.status === 'ACTIVE' 
                        ? "bg-white border-blue-200 shadow-blue-100" 
                        : "bg-white/60 border-slate-100")
            )}
        >
             {mission.status === 'ACTIVE' && (
                <div className={cn("absolute top-0 right-0 px-3 py-1 text-white text-[10px] font-bold rounded-bl-xl z-20", isNight ? "bg-rose-500" : "bg-blue-500")}>
                    ACTIVE
                </div>
            )}

            <div className="flex justify-between items-start mb-4">
                <div className="space-y-1">
                     <div className="flex gap-2 mb-2">
                        {mission.tags.map(tag => (
                            <span key={tag} className={cn("px-1.5 py-0.5 rounded text-[9px] font-bold uppercase border", isNight ? "bg-slate-800 text-slate-400 border-white/10" : "bg-slate-100 text-slate-500 border-slate-200")}>
                                {tag}
                            </span>
                        ))}
                    </div>
                    <h3 className={cn("text-lg font-bold transition-colors", isNight ? "text-slate-200 group-hover:text-rose-400" : "text-slate-800 group-hover:text-blue-600")}>
                        {mission.title}
                    </h3>
                </div>
                <div className={cn("p-2 rounded-lg transition-colors", isNight ? "bg-white/5 text-slate-500 group-hover:text-rose-400" : "bg-slate-50 text-slate-400 group-hover:bg-blue-50 group-hover:text-blue-500")}>
                     {getStatusIcon(mission.status)}
                </div>
            </div>

            <p className="text-sm text-slate-500 mb-6 line-clamp-2">
                {mission.description}
            </p>

            <div className={cn("flex items-center justify-between mt-auto pt-4 border-t", isNight ? "border-white/5" : "border-slate-100/50")}>
                <div className="flex flex-col">
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Progress</span>
                    <div className="flex items-center gap-2 mt-1">
                        <div className="w-24 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                            <div 
                                className="h-full bg-blue-500 rounded-full transition-all duration-1000"
                                style={{ width: `${mission.progress || 0}%` }}
                            ></div>
                        </div>
                        <span className="text-xs font-bold text-slate-600">{mission.progress}%</span>
                    </div>
                </div>

                <button 
                    onClick={() => startMission(mission.id)}
                    className="flex items-center gap-1.5 text-xs font-bold text-blue-600 hover:text-blue-700 transition-colors px-3 py-1.5 rounded-lg hover:bg-blue-50"
                >
                    RESUME <ArrowRight className="w-3.5 h-3.5" />
                </button>
            </div>
        </motion.div>
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
