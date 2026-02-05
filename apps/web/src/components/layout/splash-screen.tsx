"use client"

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface SplashScreenProps {
  onComplete?: () => void
}

export function SplashScreen({ onComplete }: SplashScreenProps) {
  const [progress, setProgress] = useState(0)
  const [logs, setLogs] = useState<string[]>([])
  const [isReady, setIsReady] = useState(false)

  // Simulation of booting process
  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval)
          setIsReady(true)
          return 100
        }
        return prev + 1
      })
    }, 40) // 4 seconds total

    const timeouts = [
      setTimeout(() => setLogs(p => [...p, ">> ACCESSING SCHALE_NETWORK_PROTOCOL..."]), 500),
      setTimeout(() => setLogs(p => [...p, ">> VERIFYING IDENTITY: SENSEI_AUTHORIZED"]), 1500),
      setTimeout(() => setLogs(p => [...p, ">> CONNECTING TO NEURAL ARCHIVE..."]), 2500),
      setTimeout(() => setLogs(p => [...p, ">> LOADING AGENT_CORE_V2.0.6..."]), 3500),
    ]

    return () => {
      clearInterval(interval)
      timeouts.forEach(clearTimeout)
    }
  }, [])

  return (
    <div className="fixed inset-0 z-50 bg-[#F0F7FF] flex flex-col items-center justify-center font-sans overflow-hidden">
      {/* Dynamic Background */}
      <div className="absolute inset-0 z-0">
         <motion.div 
            animate={{ opacity: [0.5, 1, 0.5] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-blue-200/20 rounded-full blur-[120px]"
         />
         <div 
            className="absolute inset-0 opacity-[0.05]" 
            style={{ 
                backgroundImage: 'linear-gradient(#3b82f6 1px, transparent 1px), linear-gradient(90deg, #3b82f6 1px, transparent 1px)', 
                backgroundSize: '50px 50px' 
            }}
         />
      </div>

      <div className="relative z-10 flex flex-col items-center w-full max-w-md px-8">
        
        {/* Central Spinning Ring Complex */}
        <div className="relative w-64 h-64 mb-16">
          {/* Outer Dashed Ring - Slow Spin */}
          <motion.div 
            animate={{ rotate: 360 }}
            transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
            className="absolute inset-0 border-[3px] border-dashed border-blue-300/50 rounded-full"
          />
          
          {/* Inner Solid Ring - Reverse Spin */}
          <motion.div 
            animate={{ rotate: -360 }}
            transition={{ duration: 10, repeat: Infinity, ease: "linear" }}
            className="absolute inset-4 border-2 border-blue-400/60 rounded-full shadow-[0_0_30px_rgba(59,130,246,0.2)]"
          />
          
          {/* Fast Loader Ring */}
          <motion.div 
             animate={{ rotate: 360 }}
             transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
             className="absolute inset-0 rounded-full border-[6px] border-transparent border-t-blue-500"
          />

          {/* Central Percentage */}
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-5xl font-black text-blue-600 tracking-tighter tabular-nums">
              {progress}<span className="text-3xl">%</span>
            </span>
            <span className="text-[10px] font-black text-blue-400 uppercase tracking-[0.3em] mt-2 animate-pulse">
              {progress < 100 ? 'Linking' : 'Connected'}
            </span>
          </div>
        </div>

        {/* Status Area */}
        <div className="text-center space-y-6 w-full h-40">
           {/* Badge */}
           <div className="inline-flex items-center space-x-2 px-4 py-1.5 bg-white/80 backdrop-blur-sm border border-blue-100 rounded-full shadow-sm">
             <div className="relative flex h-2 w-2">
                <span className={cn("animate-ping absolute inline-flex h-full w-full rounded-full opacity-75", isReady ? "bg-green-400" : "bg-blue-400")}></span>
                <span className={cn("relative inline-flex rounded-full h-2 w-2", isReady ? "bg-green-500" : "bg-blue-500")}></span>
             </div>
             <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                {isReady ? "System Online" : "Deploying Neural Modules..."}
             </span>
           </div>
           
           {/* Title */}
           <motion.h1 
             initial={{ opacity: 0, y: 10 }}
             animate={{ opacity: 1, y: 0 }}
             className="text-2xl font-black text-slate-800 tracking-tight uppercase"
           >
             {isReady ? "Welcome Back, Sensei" : "Initiating Connection"}
           </motion.h1>
           
           {/* Terminal Logs */}
           <div className="font-mono text-[10px] text-blue-400/80 h-16 flex flex-col items-center justify-start space-y-1">
             <AnimatePresence>
                {logs.map((log, i) => (
                    <motion.p 
                        key={i} 
                        initial={{ opacity: 0, height: 0 }} 
                        animate={{ opacity: 1, height: 'auto' }}
                        className="truncate max-w-full"
                    >
                        {log}
                    </motion.p>
                ))}
             </AnimatePresence>
           </div>
        </div>

        {/* Action Button - Appears when ready */}
        <div className="h-20 mt-8 flex items-center justify-center">
            <AnimatePresence>
                {isReady && (
                    <motion.button
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onClick={onComplete}
                        className="group relative px-12 py-4 overflow-hidden rounded-2xl bg-blue-500 text-white font-black shadow-[0_10px_30px_rgba(59,130,246,0.3)] transition-all"
                    >
                        <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.3),transparent)] -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]"></div>
                        <span className="relative flex items-center tracking-widest uppercase text-sm">
                            Enter Workspace
                            <ArrowRight className="h-5 w-5 ml-3" />
                        </span>
                    </motion.button>
                )}
            </AnimatePresence>
        </div>

      </div>

      {/* Decorative Corners */}
      <div className="fixed bottom-8 left-8 border-l-2 border-blue-400 pl-4 py-1 opacity-60">
        <p className="text-[10px] font-black text-slate-400 uppercase">Location</p>
        <p className="text-xs font-bold text-blue-500 uppercase">Kivotos // Central Sector</p>
      </div>
      
      <div className="fixed bottom-8 right-8 text-right border-r-2 border-blue-400 pr-4 py-1 opacity-60">
        <p className="text-[10px] font-black text-slate-400 uppercase">System Time</p>
        <p className="text-xs font-bold text-blue-500 uppercase">02 FEB 2026 // 10:32 AM</p>
      </div>

    </div>
  )
}
