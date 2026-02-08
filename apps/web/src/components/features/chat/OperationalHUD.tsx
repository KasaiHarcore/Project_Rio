import React from 'react'
import { cn } from '@/lib/utils'
import { motion, AnimatePresence } from 'framer-motion'
import { Activity, Database, Search, Zap, Wifi, ArrowLeft } from 'lucide-react'

interface OperationalHUDProps {
  status: 'ready' | 'submitted' | 'streaming' | 'error'
  title?: string
  onBack?: () => void
}

export function OperationalHUD({ status, title = "OPERATIONAL_MODE", onBack }: OperationalHUDProps) {
  
  const hudState = React.useMemo(() => {
    switch (status) {
        case 'streaming': return { label: 'PROCESSING', icon: Zap, colorVar: '--hud-state-streaming' }
        case 'submitted': return { label: 'INDEXING', icon: Search, colorVar: '--hud-state-submitted' }
        case 'error': return { label: 'ERROR', icon: Activity, colorVar: '--destructive' as const }
        default: return { label: 'ONLINE', icon: Wifi, colorVar: '--hud-state-ready' }
    }
  }, [status])

  return (
    <div
      className="relative backdrop-blur-md border-b z-20 overflow-hidden transition-all duration-500 bg-[var(--hud-bg)] border-[var(--hud-border)]"
      style={{ boxShadow: 'var(--hud-shadow)' }}
    >
      <div className="flex items-center justify-between px-6 py-3 relative z-10">
          
          {/* Left: Identity Block */}
          <div className="flex items-center gap-3">
              {onBack && (
                <button 
                  onClick={onBack}
                  aria-label="Go back to dashboard"
                  className="p-2 rounded-lg transition-colors group text-[var(--hud-back-text)] hover:bg-[var(--hud-back-hover)] hover:text-[var(--hud-back-hover-text)]"
                >
                  <ArrowLeft size={18} />
                </button>
              )}

              <div className="p-2 rounded-lg border backdrop-blur-sm bg-[var(--hud-icon-bg)] border-[var(--hud-icon-border)]">
                 <Database size={16} className="text-[var(--hud-icon-text)]" />
              </div>
              <div className="flex flex-col">
                  <h2 className="text-xs font-black tracking-[0.2em] uppercase text-[var(--hud-title-text)]">
                      {title}
                  </h2>
              </div>
          </div>

          {/* Right: Dynamic Status Indicator */}
          <div className="flex items-center gap-3 pl-4 pr-3 py-1.5 rounded-full border border-opacity-30 bg-[var(--hud-status-bg)] border-[var(--hud-status-border)]">
               <span className="text-[9px] font-bold uppercase tracking-widest text-[var(--hud-status-label)]">
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
                        <hudState.icon size={12} className="animate-pulse" style={{ color: `var(${hudState.colorVar})` }} />
                        <span className="text-[10px] font-black tracking-wider" style={{ color: `var(${hudState.colorVar})` }}>
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
            className="absolute bottom-0 left-0 h-[2px] w-full bg-[var(--hud-progress-bar)]"
            initial={{ scaleX: 0, originX: 0 }}
            animate={{ scaleX: 1 }}
            transition={{ duration: 0.5, ease: "circIn" }}
          />
      )}
    </div>
  )
}
