import React from 'react'
import { cn } from '@/lib/utils'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { Copy, Check, Terminal, ExternalLink, Cpu } from 'lucide-react'
import { useState } from 'react'

interface SmartDataCardProps {
  role: 'user' | 'assistant' | 'system' | 'data'
  content: string
  isPlana?: boolean
  timestamp?: string
}

export function SmartDataCard({ role, content, isPlana, timestamp }: SmartDataCardProps) {
  const isAssistant = role === 'assistant'
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Animation variants for the card
  const cardVariants = {
    hidden: { opacity: 0, y: 20, scale: 0.95 },
    visible: { 
      opacity: 1, 
      y: 0, 
      scale: 1,
      transition: { duration: 0.4, ease: "easeOut" }
    }
  }

  return (
    <motion.div 
      initial="hidden"
      animate="visible"
      variants={cardVariants}
      className={cn(
        "relative overflow-hidden rounded-xl border p-5 shadow-sm transition-all duration-300",
        // Arona Theme (Light / High-Tech Blue)
        !isPlana && isAssistant && "bg-white/70 backdrop-blur-xl border-blue-100/50 shadow-[0_8px_30px_rgb(0,0,0,0.04)] hover:shadow-blue-100/50 hover:border-blue-200",
        !isPlana && !isAssistant && "bg-slate-50 border-slate-200/50", // User card (Neutral)

        // Plana Theme (Dark / Cyber Red)
        isPlana && isAssistant && "bg-[#161b22]/90 backdrop-blur-xl border-rose-900/30 shadow-[0_8px_30px_rgba(225,29,72,0.05)] hover:border-rose-500/30",
        isPlana && !isAssistant && "bg-[#0d1117] border-slate-800", // User card (Dark)
      )}
    >
      {/* Decorative High-Tech Header Line */}
      {isAssistant && (
         <div className={cn(
             "absolute left-0 top-0 h-[2px] w-full bg-gradient-to-r",
             isPlana ? "from-rose-600 via-rose-900/50 to-transparent" : "from-[#1289F4] via-cyan-400 to-transparent"
         )} />
      )}

      {/* Decorative Corner Accents (Cyberpunk Style) */}
      {isAssistant && (
          <>
            <div className={cn("absolute top-0 right-0 p-2", isPlana ? "text-rose-900/20" : "text-blue-100")}>
                <Cpu size={24} className="opacity-50" />
            </div>
          </>
      )}

      {/* Header Info (Role & Actions) */}
      <div className="flex items-center justify-between mb-3 border-b border-dashed border-opacity-20 pb-2 border-gray-400">
        <div className="flex items-center gap-2">
            <span className={cn(
                "text-[10px] font-black tracking-widest uppercase",
                isAssistant 
                    ? (isPlana ? "text-rose-400" : "text-blue-500") 
                    : (isPlana ? "text-slate-500" : "text-slate-400")
            )}>
                {role === 'assistant' ? 'SYSTEM_RESPONSE' : 'USER_QUERY'}
            </span>
            {timestamp && (
                <span className="text-[10px] text-gray-400 font-mono opacity-60">
                    [{timestamp}]
                </span>
            )}
        </div>
        
        {/* Actions */}
        <div className="flex items-center gap-1">
            <button 
                onClick={handleCopy}
                className={cn(
                    "p-1 rounded hover:bg-black/5 transition-colors",
                    isPlana ? "hover:bg-white/10 text-slate-400" : "text-slate-400"
                )}
                title="Copy content"
            >
                {copied ? <Check size={12} /> : <Copy size={12} />}
            </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className={cn(
          "prose prose-sm max-w-none break-words",
          isPlana ? "prose-invert prose-p:text-slate-300 prose-headings:text-slate-200 prose-pre:bg-[#0d1117] prose-pre:border-slate-800" : "prose-p:text-slate-600 prose-headings:text-slate-700 prose-pre:bg-slate-900"
      )}>
        <ReactMarkdown
          components={{
             // Custom Code Block Styling
             code({className, children, ...props}) {
               const match = /language-(\w+)/.exec(className || '')
               return match ? (
                 <div className="relative group rounded-lg overflow-hidden my-4 border border-opacity-20 bg-opacity-50">
                    <div className={cn(
                        "flex items-center justify-between px-3 py-1 text-[10px] font-mono border-b",
                        isPlana ? "bg-[#0d1117] border-slate-700 text-slate-400" : "bg-slate-100 border-slate-200 text-slate-500"
                    )}>
                        <div className="flex items-center gap-1">
                            <Terminal size={10} />
                            <span>{match[1].toUpperCase()}</span>
                        </div>
                    </div>
                    <code className={className} {...props}>
                      {children}
                    </code>
                 </div>
               ) : (
                 <code className={cn(
                     "rounded px-1 py-0.5 text-xs font-mono",
                     isPlana ? "bg-rose-900/30 text-rose-200" : "bg-blue-100 text-blue-700"
                 )} {...props}>
                   {children}
                 </code>
               )
             }
          }}
        >
          {content}
        </ReactMarkdown>
      </div>

      {/* Footer Status (Tech Fluff) */}
      {isAssistant && (
         <div className="mt-4 flex items-center gap-4 pt-2 border-t border-transparent">
             <div className="flex items-center gap-1.5">
                 <div className={cn("h-1.5 w-1.5 rounded-full animate-pulse", isPlana ? "bg-rose-500" : "bg-emerald-500")} />
                 <span className="text-[9px] font-mono uppercase text-gray-400">
                     Execution Complete
                 </span>
             </div>
         </div>
      )}
    </motion.div>
  )
}
