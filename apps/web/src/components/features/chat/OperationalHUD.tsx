import React from 'react'
import { cn } from '@/lib/utils'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, Database, Search, Zap, Wifi, ArrowLeft } from 'lucide-react'
import { useTheme } from '@/components/providers/theme-provider'

interface OperationalHUDProps {
  status: 'ready' | 'submitted' | 'streaming' | 'error'
  isPlana?: boolean
  title?: string
  onBack?: () => void
}

export function OperationalHUD({ status, isPlana, title = "OPERATIONAL_MODE", onBack }: OperationalHUDProps) {
  
  // Map AI SDK status to our detailed HUD states
  const hudState = React.useMemo(() => {
    switch (status) {
        case 'streaming': return { label: 'PROCESSING', icon: Zap, color: isPlana ? 'text-rose-400' : 'text-blue-500' }
        case 'submitted': return { label: 'INDEXING', icon: Search, color: isPlana ? 'text-orange-400' : 'text-amber-500' }
        case 'error': return { label: 'ERROR', icon: Activity, color: 'text-red-500' }
        default: return { label: 'ONLINE', icon: Wifi, color: isPlana ? 'text-emerald-400' : 'text-emerald-500' }
    }
  }, [status, isPlana])

  return (
    <div className={cn(
        "relative backdrop-blur-md border-b z-20 overflow-hidden transition-all duration-500",
        isPlana 
            ? "bg-[#0d1117]/80 border-rose-900/30 shadow-[0_4px_20px_rgba(225,29,72,0.1)]" 
            : "bg-white/80 border-blue-100/50 shadow-sm"
    )}>
      {/* Background Grid Animation (Subtle) */}
      <div className="absolute inset-0 opacity-[0.03]" 
           style={{ backgroundImage: `radial-gradient(${isPlana ? '#fff' : '#000'} 1px, transparent 1px)`, backgroundSize: '16px 16px' }} 
      />

      <div className="flex items-center justify-between px-6 py-3 relative z-10">
          
          {/* Left: Identity Block */}
          <div className="flex items-center gap-3">
              {onBack && (
                <button 
                  onClick={onBack}
                  className={cn(
                    "p-2 rounded-lg transition-colors group",
                    isPlana ? "hover:bg-rose-900/20 text-slate-500 hover:text-rose-400" : "hover:bg-blue-50 text-slate-400 hover:text-blue-500"
                  )}
                >
                  <ArrowLeft size={18} />
                </button>
              )}

              <div className={cn(
                  "p-2 rounded-lg border backdrop-blur-sm",
                  isPlana ? "bg-rose-950/30 border-rose-900/40" : "bg-blue-50 border-blue-100"
              )}>
                 <Database size={16} className={cn(isPlana ? "text-rose-400" : "text-blue-500")} />
              </div>
              <div className="flex flex-col">
                  <h2 className={cn("text-xs font-black tracking-[0.2em] uppercase", isPlana ? "text-slate-200" : "text-slate-700")}>
                      {title}
                  </h2>
                  <div className="flex items-center gap-1.5 mt-0.5">
                      <span className={cn("text-[10px] font-mono", isPlana ? "text-slate-500" : "text-slate-400")}>ID:</span>
                      <span className={cn("text-[10px] font-mono", isPlana ? "text-slate-400" : "text-slate-500")}>SIG-01.99.2</span>
                  </div>
              </div>
          </div>

          {/* Right: Dynamic Status Indicator */}
          <div className={cn(
              "flex items-center gap-3 pl-4 pr-3 py-1.5 rounded-full border border-opacity-30",
              isPlana ? "bg-[#161b22] border-rose-900/30" : "bg-slate-50 border-blue-100"
          )}>
               <span className={cn("text-[9px] font-bold uppercase tracking-widest", isPlana ? "text-slate-400" : "text-slate-500")}>
                   SYSTEM STATUS
               </span>
               <div className="h-3 w-[1px] bg-gray-500/20" />
               
               <AnimatePresence mode='wait'>
                    <motion.div 
                        key={hudState.label}
                        initial={{ opacity: 0, y: 5 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -5 }}
                        className="flex items-center gap-2"
                    >
                        <hudState.icon size={12} className={cn("animate-pulse", hudState.color)} />
                        <span className={cn("text-[10px] font-black tracking-wider", hudState.color)}>
                            {hudState.label}
                        </span>
                    </motion.div>
               </AnimatePresence>
          </div>
      </div>
      
      {/* Progress Line for Processing */}
      {status === 'streaming' && (
          <motion.div 
            layoutId="active-line"
            className={cn("absolute bottom-0 left-0 h-[2px] w-full", isPlana ? "bg-rose-500" : "bg-blue-500")}
            initial={{ scaleX: 0, originX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.5, ease: "circIn" }}
          />
      )}
    </div>
  )
}
