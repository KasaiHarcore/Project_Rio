import React, { useMemo } from 'react'
import { motion } from 'framer-motion'
import { Play, Sparkles, Activity, ShieldAlert, Cpu } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useEmotionalStore, Mood, RelationshipTier } from '@/features/emotional/store'
import { CHARACTERS } from '@/features/rio/types'
import { useRouter } from 'next/navigation'
import Image from 'next/image'

/* ─── Mood → contextual greeting suffix ─── */
const MOOD_CONTEXT: Record<Mood, string> = {
    happy: "System performance: optimal. Ready for complex calculations.",
    excited: "New data detected — analysis protocols are fully engaged.",
    neutral: "All systems nominal. Awaiting your next directive, Sensei.",
    sad: "...Error log review recommended. I am experiencing minor deviations.",
    frustrated: "Multiple anomalies flagged. Attempting to recalibrate sensors.",
    tired: "Operating in low-power mode. Suggest scheduling a maintenance cycle.",
}

const TIER_LABELS: Record<RelationshipTier, { label: string; color: string }> = {
    stranger: { label: 'New Contact', color: 'text-slate-400' },
    acquaintance: { label: 'Acquaintance', color: 'text-blue-400' },
    friend: { label: 'Trusted', color: 'text-emerald-400' },
    close_friend: { label: 'Close Ally', color: 'text-violet-400' },
    bonded: { label: 'Bonded', color: 'text-rose-400' },
}

interface DashboardHeroProps {
    level: number
    xpProgress: number
    xpInLevel: number
    xpForNext: number
    totalXp: number
    activeThreads: number
}

export function DashboardHero({
    level,
    xpProgress,
    xpInLevel,
    xpForNext,
    totalXp,
    activeThreads,
}: DashboardHeroProps) {
    const router = useRouter()
    const mood = useEmotionalStore((s) => s.mood)
    const affinity = useEmotionalStore((s) => s.affinity)
    const relationshipTier = useEmotionalStore((s) => s.relationshipTier)

    const character = CHARACTERS[0]
    const greeting = useMemo(() => {
        const greetings = character.greetings
        return greetings[Math.floor(Math.random() * greetings.length)]
    }, [character.greetings])

    const moodContext = MOOD_CONTEXT[mood] ?? MOOD_CONTEXT.neutral
    const tierInfo = TIER_LABELS[relationshipTier] ?? TIER_LABELS.stranger

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            className="relative w-full rounded-[2rem] overflow-hidden mb-10 group"
        >
            {/* Background Graphic (Music App Style) */}
            <div className="absolute inset-0 z-0">
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-900 via-[#1a1c2e] to-zinc-950 opacity-90 transition-all duration-1000 group-hover:scale-105" />

                {/* Decorative glowing blobs */}
                <div className="absolute -top-[50%] -right-[20%] w-[100%] h-[150%] rounded-[100%] bg-indigo-500 blur-[150px] opacity-20 mix-blend-screen transition-transform duration-[5000ms] group-hover:-rotate-12" />
                <div className="absolute -bottom-[20%] -left-[10%] w-[60%] h-[80%] rounded-full bg-blue-600 blur-[120px] opacity-10 mix-blend-screen" />

                {/* Grid Overlay */}
                <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHBhdGggZD0iTTAgMGg0MHY0MEgwVjB6IiBmaWxsPSJub25lIi8+PHBhdGggZD0iTTAgNDBoNDBWMHoiIGZpbGw9Im5vbmUiIHN0cm9rZT0icmdiYSgyNTUsMjU1LDI1NSwwLjAyKSIvPjwvc3ZnPg==')] opacity-50 mask-image:linear-gradient(to_bottom,black,transparent)" />
            </div>

            <div className="relative z-10 flex flex-col lg:flex-row items-center justify-between p-8 lg:p-12 min-h-[300px]">
                {/* Left Content */}
                <div className="flex-1 max-w-2xl flex flex-col justify-center">
                    <motion.div
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.2, duration: 0.5 }}
                        className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/10 backdrop-blur-md w-fit mb-6"
                    >
                        <Sparkles className="w-4 h-4 text-indigo-400" />
                        <span className="text-xs font-bold text-indigo-200 tracking-widest uppercase">
                            System Active • {tierInfo.label}
                        </span>
                    </motion.div>

                    <motion.h1
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.3, duration: 0.5 }}
                        className="text-4xl lg:text-5xl xl:text-6xl font-black text-white leading-[1.1] tracking-tight mb-4"
                    >
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-200 via-indigo-200 to-indigo-400">
                            {greeting.split('.')[0]}
                        </span>
                        {greeting.split('.').length > 1 && (
                            <><br /><span className="text-white/90 text-3xl lg:text-4xl font-extrabold">{greeting.split('.').slice(1).join('.')}</span></>
                        )}
                    </motion.h1>

                    <motion.p
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.4 }}
                        className="text-base lg:text-lg text-indigo-200/70 font-medium mb-8 max-w-xl leading-relaxed"
                    >
                        {moodContext} Currently analyzing {activeThreads} live operational threads with {(xpProgress).toFixed(1)}% system capacity utilization towards next threshold.
                    </motion.p>

                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.5 }}
                        className="flex items-center gap-4"
                    >
                        <button
                            onClick={() => router.push('/operation')}
                            className="group/btn relative overflow-hidden flex items-center gap-3 px-8 py-4 bg-white text-indigo-950 rounded-[1.25rem] font-black text-sm tracking-wide transition-transform hover:scale-105 active:scale-95"
                        >
                            <span className="absolute inset-0 bg-gradient-to-r from-indigo-100 to-white opacity-0 group-hover/btn:opacity-100 transition-opacity" />
                            <div className="relative z-10 flex items-center justify-center w-8 h-8 rounded-full bg-indigo-950 text-white">
                                <Play size={14} className="ml-0.5 fill-current" />
                            </div>
                            <span className="relative z-10">INITIATE OPERATION</span>
                        </button>

                        <div className="flex items-center gap-6 px-6 py-4 rounded-[1.25rem] bg-white/5 border border-white/10 backdrop-blur-md">
                            <div>
                                <div className="text-[10px] font-black tracking-widest text-indigo-300 uppercase mb-1">Affinity</div>
                                <div className="flex items-baseline gap-1">
                                    <span className="text-xl font-black text-white">{affinity}</span>
                                    <span className="text-xs text-white/50 font-bold">%</span>
                                </div>
                            </div>
                            <div className="w-px h-8 bg-white/10" />
                            <div>
                                <div className="text-[10px] font-black tracking-widest text-indigo-300 uppercase mb-1">Level Zero</div>
                                <div className="flex items-baseline gap-1">
                                    <span className="text-xl font-black text-white">{level}</span>
                                    <span className="text-xs text-white/50 font-bold">LVL</span>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </div>

                {/* Right Content / Overhanging Character Art */}
                <div className="relative mt-8 lg:mt-0 flex-shrink-0 w-full lg:w-[400px] h-[300px] lg:h-auto flex items-end justify-center lg:justify-end pointer-events-none">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.8, y: 50 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        transition={{ type: "spring", stiffness: 100, damping: 20, delay: 0.3 }}
                        className="relative z-20"
                    >
                        {/* A large drop shadow that perfectly contours the image */}
                        <div className="relative w-64 h-64 lg:w-80 lg:h-80 drop-shadow-[0_20px_50px_rgba(79,70,229,0.3)]">
                            <Image
                                src="/images/avatar.png"
                                alt={`Rio - ${mood}`}
                                width={400}
                                height={400}
                                className="object-contain w-full h-full scale-[1.25] origin-bottom drop-shadow-2xl"
                                priority
                            />
                        </div>

                        {/* Floating metric pills */}
                        <motion.div
                            animate={{ y: [0, -10, 0] }}
                            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                            className="absolute -left-12 top-10 flex items-center gap-2 px-3 py-2 bg-indigo-950/80 backdrop-blur-md border border-white/10 rounded-xl shadow-2xl pointer-events-auto"
                        >
                            <Cpu size={14} className="text-indigo-400" />
                            <span className="text-xs font-bold text-white tracking-wider">OPT-99%</span>
                        </motion.div>

                        <motion.div
                            animate={{ y: [0, 8, 0] }}
                            transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 1 }}
                            className="absolute -right-4 bottom-16 flex items-center gap-2 px-3 py-2 bg-indigo-950/80 backdrop-blur-md border border-white/10 rounded-xl shadow-2xl pointer-events-auto"
                        >
                            <Activity size={14} className="text-emerald-400" />
                            <span className="text-xs font-bold text-white tracking-wider">{activeThreads} SYS</span>
                        </motion.div>
                    </motion.div>
                </div>
            </div>
        </motion.div>
    )
}
