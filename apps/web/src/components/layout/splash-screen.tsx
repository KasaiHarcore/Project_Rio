"use client"

import React, { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { agentConfig } from '@/shared/lib/agent-config'
import { cn } from '@/shared/lib/utils'
import { useUIStore } from '@/shared/store/ui-store'

// ==========================================
// CONFIGURATION — Dark mode only
// ==========================================

const SPLASH_CONFIG = {
    bg: '#0f111a',
    bgGradient: 'from-[#1a1625] via-[#0f111a] to-[#0a0c14]',
    vignette: '#0f111a',
    gridColor: 'rgba(244, 63, 94, 0.3)',
    hexBorder: 'border-rose-500/20',
    hexBg: 'bg-rose-900/10',
    primary: '#f43f5e',
    primaryGlow: 'rgba(244,63,94,0.4)',
    ringBorder: 'border-rose-900/50',
    dashBorder: 'border-rose-900/30',
    textMain: '#e2e8f0',
    textSub: 'text-slate-500',
    textFooter: 'text-slate-600',
    btnBg: 'bg-[#0d1117]/60',
    btnHoverBg: 'group-hover:bg-[#0d1117]',
    btnBorder: 'border-rose-500/30',
    btnHoverBorder: 'group-hover:border-rose-500',
    loadingImg: '/images/rio_load.png',
    successImg: '/images/rio_load.png',
} as const

type SplashTheme = typeof SPLASH_CONFIG

interface SplashScreenProps {
    onComplete?: () => void
}

export function SplashScreen({ onComplete }: SplashScreenProps) {
    const [progress, setProgress] = useState(0)
    const [isReady, setIsReady] = useState(false)
    const [isExiting, setIsExiting] = useState(false)

    const t = SPLASH_CONFIG

    // Simulated Loading Sequence
    useEffect(() => {
        const timer = setInterval(() => {
            setProgress(prev => {
                if (prev >= 100) {
                    clearInterval(timer)
                    setIsReady(true)
                    return 100
                }
                return prev + Math.floor(Math.random() * 5) + 1
            })
        }, 100)
        return () => clearInterval(timer)
    }, [])

    const handleStart = () => {
        if (isReady && !isExiting) {
            setIsExiting(true)
            setTimeout(() => {
                if (onComplete) onComplete()
            }, 800)
        }
    }

    return (
        <AnimatePresence>
            {!isExiting && (
                <motion.div
                    className="fixed inset-0 z-50 overflow-hidden font-sans cursor-pointer select-none"
                    style={{ backgroundColor: t.bg }}
                    role="button"
                    tabIndex={0}
                    aria-label="Click or press Enter to start"
                    onClick={handleStart}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleStart(); } }}
                    exit={{ opacity: 0, scale: 1.05, filter: "blur(20px)" }}
                    transition={{ duration: 0.8, ease: "easeInOut" }}
                >
                    <TechBackground t={t} />

                    <div className="relative z-20 flex flex-col items-center justify-center w-full h-full pb-10">
                        <MainLoader progress={progress} isReady={isReady} t={t} />
                        <StatusText isReady={isReady} t={t} />
                        <StartPrompt isReady={isReady} t={t} />
                    </div>

                    <SystemFooter t={t} />
                </motion.div>
            )}
        </AnimatePresence>
    )
}

// ==========================================
// SUB-COMPONENTS
// ==========================================

function TechBackground({ t }: { t: SplashTheme }) {
    const hexagons = useMemo(() => Array.from({ length: 20 }, (_, i) => i), [])

    return (
        <>
            <div className={cn("absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))]", t.bgGradient)} />

            <div className="absolute inset-0 overflow-hidden opacity-50">
                {hexagons.map((i) => (
                    <FloatingHexagon key={i} index={i} t={t} />
                ))}
            </div>

            <div
                className="absolute inset-0 opacity-20"
                style={{
                    backgroundImage: `linear-gradient(${t.gridColor} 1px, transparent 1px), linear-gradient(90deg, ${t.gridColor} 1px, transparent 1px)`,
                    backgroundSize: '60px 60px',
                    transform: 'perspective(500px) rotateX(60deg) translateY(-100px) scale(2)',
                    transformOrigin: 'top center'
                }}
            />

            <div className="absolute inset-0 opacity-80" style={{ background: `radial-gradient(transparent 0%, ${t.vignette} 100%)` }} />
        </>
    )
}

function FloatingHexagon({ index, t }: { index: number, t: SplashTheme }) {
    const [pos, setPos] = useState({ x: 0, y: 0, duration: 15 })

    useEffect(() => {
        setPos({
            x: Math.random() * 100,
            y: Math.random() * 100,
            duration: 10 + Math.random() * 20
        })
    }, [])

    return (
        <motion.div
            className={cn("absolute w-16 h-16 border", t.hexBorder, t.hexBg)}
            style={{
                left: `${pos.x}%`,
                top: `${pos.y}%`,
                clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)'
            }}
            animate={{
                y: [0, -100, 0],
                rotate: [0, 180, 360],
                opacity: [0, 0.6, 0]
            }}
            transition={{
                duration: pos.duration,
                repeat: Infinity,
                ease: "linear"
            }}
        />
    )
}

function MainLoader({ progress, isReady, t }: { progress: number, isReady: boolean, t: SplashTheme }) {
    const clampedProgress = Math.min(100, progress)

    return (
        <div className="relative w-64 h-64 mb-10 flex items-center justify-center">
            <motion.div
                className={cn("absolute inset-0 border-[1px] rounded-full", t.ringBorder)}
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            >
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3 h-3 rounded-full" style={{ backgroundColor: t.primary, boxShadow: `0 0 10px ${t.primary}` }} />
            </motion.div>

            <motion.div
                className={cn("absolute inset-6 border-[1px] border-dashed rounded-full", t.dashBorder)}
                animate={{ rotate: -360 }}
                transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
            />

            <div className="relative z-10 flex flex-col items-center">
                <motion.div
                    key={isReady ? "ready" : "loading"}
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="text-center"
                >
                    {isReady ? (
                        <motion.div
                            initial={{ scale: 0 }} animate={{ scale: 1 }}
                            className="flex items-center justify-center p-4"
                        >
                            <img
                                src={t.successImg}
                                alt="System Ready"
                                className="w-48 h-48 object-contain"
                                style={{ filter: `drop-shadow(0 0 10px ${t.primaryGlow})` }}
                            />
                        </motion.div>
                    ) : (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1, scale: [0.95, 1, 0.95] }}
                            transition={{ repeat: Infinity, duration: 2 }}
                            className="flex items-center justify-center p-4"
                        >
                            <img
                                src={t.loadingImg}
                                alt="Loading..."
                                className="w-48 h-48 object-contain opacity-80"
                            />
                        </motion.div>
                    )}
                </motion.div>
            </div>

            <svg className="absolute inset-0 w-full h-full -rotate-90 pointer-events-none">
                <circle
                    cx="128" cy="128" r="120"
                    fill="none"
                    stroke={t.primary}
                    strokeWidth="3"
                    strokeDasharray="753"
                    strokeDashoffset={753 - (753 * clampedProgress) / 100}
                    strokeLinecap="round"
                    className="transition-all duration-300 ease-out opacity-90"
                    style={{ filter: `drop-shadow(0 0 4px ${t.primaryGlow})` }}
                />
            </svg>
        </div>
    )
}

function StatusText({ isReady, t }: { isReady: boolean, t: SplashTheme }) {
    return (
        <div className="h-24 flex flex-col items-center justify-top overflow-hidden">
            <AnimatePresence mode="wait">
                {!isReady ? (
                    <motion.div
                        key="loading"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="text-center"
                    >
                        <h2 className="text-xl font-bold tracking-[0.2em] font-mono" style={{ color: t.primary }}>
                            CONNECTING TO SCHALE
                        </h2>
                        <p className={cn("text-sm font-mono mt-2 font-bold uppercase", t.textSub)}>
                            Initializing Sensei Neural Link...
                        </p>
                    </motion.div>
                ) : (
                    <motion.div
                        key="ready"
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="text-center"
                    >
                        <h2 className="text-3xl font-black tracking-wider" style={{ color: t.textMain }}>
                            AUTHENTICATION CLEAR
                        </h2>
                        <div className="h-1 w-20 mx-auto my-3 rounded-full" style={{ backgroundColor: t.primary }} />
                        <p className={cn("text-sm font-bold tracking-widest uppercase", t.textSub)}>
                            Welcome back, Sensei
                        </p>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

function StartPrompt({ isReady, t }: { isReady: boolean, t: SplashTheme }) {
    return (
        <div className="absolute bottom-32 h-16 w-full flex justify-center items-center">
            <AnimatePresence>
                {isReady && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="relative group cursor-pointer"
                    >
                        <div className="absolute inset-0 rounded-full blur-xl animate-pulse" style={{ backgroundColor: `${t.primary}20` }} />

                        <div className={cn(
                            "relative px-12 py-4 backdrop-blur-md border rounded-full flex items-center gap-4 transition-all group-hover:shadow-lg group-hover:scale-105",
                            t.btnBg, t.btnBorder, t.btnHoverBg, t.btnHoverBorder
                        )}>
                            <div className="w-2 h-2 rounded-full animate-ping" style={{ backgroundColor: t.primary }} />
                            <span className="text-lg font-black tracking-[0.2em] transition-colors" style={{ color: t.textMain }}>
                                TOUCH TO START
                            </span>
                            <div className="w-2 h-2 rounded-full animate-ping" style={{ backgroundColor: t.primary }} />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

function SystemFooter({ t }: { t: SplashTheme }) {
    return (
        <div className="absolute bottom-8 w-full text-center opacity-60">
            <div className={cn("flex justify-center items-center gap-4 text-[10px] font-bold uppercase tracking-widest font-mono", t.textFooter)}>
                <span>System: Online</span>
                <span style={{ color: t.primary }}>•</span>
                <span>S.C.H.A.L.E</span>
            </div>
        </div>
    )
}
