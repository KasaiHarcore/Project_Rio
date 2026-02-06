"use client"

import React, { useState, useEffect, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { agentConfig } from '@/lib/agent-config'
import { cn } from '@/lib/utils'

// ==========================================
// CONFIGURATION
// ==========================================
const ANIMATION_CONFIG = {
    // Colors based on Blue Archive / Sci-Fi Anime UI (Schale Light Mode)
    // Now using CSS variables from globals.css for consistency
    COLORS: {
        BG_MAIN: 'var(--background)',    // #f3f7f9
        BG_ACCENT: 'var(--card)',        // #ffffff
        PRIMARY: 'var(--primary)',       // #00AEEF
        SECONDARY: 'var(--destructive)', // #FF4D4F or #FF6F91
        TEXT_MAIN: 'var(--foreground)',  // #2d3748
        TEXT_SUB: 'var(--muted-foreground)' // #64748b
    }
}

interface SplashScreenProps {
  onComplete?: () => void
}

export function SplashScreen({ onComplete }: SplashScreenProps) {
  const [progress, setProgress] = useState(0)
  const [isReady, setIsReady] = useState(false)
  const [isExiting, setIsExiting] = useState(false)

  // Simulated Loading Sequence
  useEffect(() => {
    const timer = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(timer)
          setIsReady(true)
          return 100
        }
        // Randomize speed for "real" loading feel
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
      }, 800) // Wait for exit animation
    }
  }

  return (
    <AnimatePresence>
      {!isExiting && (
        <motion.div 
            className="fixed inset-0 z-50 overflow-hidden font-sans cursor-pointer select-none bg-[#f3f7f9]"
            onClick={handleStart}
            exit={{ opacity: 0, scale: 1.05, filter: "blur(20px)" }}
            transition={{ duration: 0.8, ease: "easeInOut" }}
        >
            <TechBackground />
            
            <div className="relative z-20 flex flex-col items-center justify-center w-full h-full pb-10">
                <MainLoader progress={progress} isReady={isReady} />
                <StatusText isReady={isReady} />
                <StartPrompt isReady={isReady} />
            </div>

            <SystemFooter />
        </motion.div>
      )}
    </AnimatePresence>
  )
}

// ==========================================
// SUB-COMPONENTS
// ==========================================

function TechBackground() {
  // Generate hexagonal grid
  const hexagons = useMemo(() => Array.from({ length: 20 }, (_, i) => i), [])

  return (
    <>
        {/* Light Gradient Background */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-white via-[#f3f7f9] to-[#e2e8f0]" />

        {/* Floating Particles/Hexagons (Blue Tint) */}
        <div className="absolute inset-0 overflow-hidden opacity-50">
            {hexagons.map((i) => (
                <FloatingHexagon key={i} index={i} />
            ))}
        </div>

        {/* Animated Grid Floor (Light Blue) */}
        <div 
            className="absolute inset-0 opacity-20"
            style={{ 
                backgroundImage: 'linear-gradient(rgba(0, 174, 239, 0.4) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 174, 239, 0.4) 1px, transparent 1px)', 
                backgroundSize: '60px 60px',
                transform: 'perspective(500px) rotateX(60deg) translateY(-100px) scale(2)',
                transformOrigin: 'top center'
            }}
        />
        
        {/* Soft Vignette */}
        <div className="absolute inset-0 bg-[radial-gradient(transparent_0%,_#f3f7f9_100%)] opacity-80" />
    </>
  )
}

function FloatingHexagon({ index }: { index: number }) {
    // FIX: Hydration Mismatch
    // We must ensure the initial render on server matches the client.
    // Random values cause mismatches. We move random generation to useEffect (Client-only).
    const [pos, setPos] = useState({ x: 0, y: 0, duration: 15 })
    
    useEffect(() => {
        // Deterministic randomness based on index if we wanted, or just true random on mount
        setPos({
            x: Math.random() * 100,
            y: Math.random() * 100,
            duration: 10 + Math.random() * 20
        })
    }, [])
    
    return (
        <motion.div
            className="absolute w-16 h-16 border border-sky-400/30 bg-sky-100/10"
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

function MainLoader({ progress, isReady }: { progress: number, isReady: boolean }) {
    const clampedProgress = Math.min(100, progress)
    
    return (
        <div className="relative w-64 h-64 mb-10 flex items-center justify-center">
            {/* Outer Rotating Ring (Subtle Blue Grey) */}
            <motion.div 
                className="absolute inset-0 border-[1px] border-slate-300 rounded-full"
                animate={{ rotate: 360 }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            >
                <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3 h-3 bg-primary rounded-full shadow-[0_0_10px_var(--primary)]" />
            </motion.div>

            {/* Inner Counter-Rotating Hexagon Ring */}
            <motion.div 
                className="absolute inset-6 border-[1px] border-dashed border-slate-300/80 rounded-full"
                animate={{ rotate: -360 }}
                transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
            />

            {/* Central Progress Display */}
            <div className="relative z-10 flex flex-col items-center">
                 <motion.div 
                    key={isReady ? "ready" : "loading"}
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="text-center"
                 >
                    {isReady ? (
                        // Readiness Image
                        <motion.div  
                            initial={{ scale: 0 }} animate={{ scale: 1 }} 
                            className="flex items-center justify-center p-4"
                        >
                            <img 
                                src="/images/splash_screen_success.png" 
                                alt="System Ready" 
                                className="w-48 h-48 object-contain drop-shadow-[0_0_10px_rgba(18,137,244,0.4)]"
                            />
                        </motion.div>
                    ) : (
                         // Loading Image
                         <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1, scale: [0.95, 1, 0.95] }}
                            transition={{ repeat: Infinity, duration: 2 }}
                            className="flex items-center justify-center p-4"
                         >
                            <img 
                                src="/images/splash_screen_loading.png" 
                                alt="Loading..." 
                                className="w-48 h-48 object-contain opacity-80"
                            />
                            {/* Optional: Keep small percentage below if desired, but user asked to change it TO the image. I'll remove the big numbers. */}
                         </motion.div>
                    )}
                 </motion.div>
            </div>

            {/* Active Arc (SVG based) */}
             <svg className="absolute inset-0 w-full h-full -rotate-90 pointer-events-none">
                 <circle
                     cx="128" cy="128" r="120"
                     fill="none"
                     stroke="#1289F4"
                     strokeWidth="3"
                    strokeDasharray="753" // Circumference ~ 2*PI*120
                    strokeDashoffset={753 - (753 * clampedProgress) / 100}
                    strokeLinecap="round"
                    className="transition-all duration-300 ease-out opacity-90 drop-shadow-[0_0_4px_rgba(18,137,244,0.4)]"
                 />
             </svg>
        </div>
    )
}

function StatusText({ isReady }: { isReady: boolean }) {
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
                        <h2 className="text-xl font-bold text-[#1289F4] tracking-[0.2em] font-mono">
                            CONNECTING TO SCHALE
                        </h2>
                        <p className="text-sm text-slate-400 font-mono mt-2 font-bold uppercase">
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
                         <h2 className="text-3xl font-black text-[#454C5D] tracking-wider">
                            AUTHENTICATION CLEAR
                         </h2>
                         <div className="h-1 w-20 bg-[#1289F4] mx-auto my-3 rounded-full" />
                         <p className="text-sm font-bold text-slate-500 tracking-widest uppercase">
                            Welcome back, Sensei
                         </p>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

function StartPrompt({ isReady }: { isReady: boolean }) {
    return (
        <div className="absolute bottom-32 h-16 w-full flex justify-center items-center">
            <AnimatePresence>
                {isReady && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="relative group cursor-pointer"
                    >
                        {/* Pulse Ring */}
                        <div className="absolute inset-0 bg-[#1289F4]/20 rounded-full blur-xl animate-pulse" />
                        
                        <div className="relative px-12 py-4 bg-white/60 backdrop-blur-md border border-[#1289F4]/30 rounded-full flex items-center gap-4 transition-all group-hover:bg-white group-hover:shadow-lg group-hover:scale-105 group-hover:border-[#1289F4]">
                             <div className="w-2 h-2 bg-[#1289F4] rounded-full animate-ping" />
                             <span className="text-lg font-black text-[#454C5D] tracking-[0.2em] group-hover:text-[#1289F4] transition-colors">
                                TOUCH TO START
                             </span>
                             <div className="w-2 h-2 bg-[#1289F4] rounded-full animate-ping" />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

function SystemFooter() {
    return (
        <div className="absolute bottom-8 w-full text-center opacity-60">
            <div className="flex justify-center items-center gap-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest font-mono">
                <span>System: Online</span>
                <span className="text-[#1289F4]">•</span>
                <span>Ver 4.0.21</span>
                <span className="text-[#1289F4]">•</span>
                <span>UID: 8559002</span>
            </div>
        </div>
    )
}
