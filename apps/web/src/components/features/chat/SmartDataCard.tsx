import React from 'react'
import { cn } from '@/lib/utils'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import { Copy, Check, Terminal, ExternalLink, Cpu, RefreshCw, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from '@/hooks/use-toast'
import { ContextMenu, type ContextMenuEntry } from '@/components/ui/context-menu'

interface SmartDataCardProps {
  role: 'user' | 'assistant' | 'system' | 'data'
  content: string
  timestamp?: string
}

export function SmartDataCard({ role, content, timestamp }: SmartDataCardProps) {
  const isAssistant = role === 'assistant'
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(content)
    setCopied(true)
    toast({ title: "Copied to clipboard", variant: "success" })
    setTimeout(() => setCopied(false), 2000)
  }

  const cardVariants = {
    hidden: { opacity: 0, y: 20, scale: 0.95 },
    visible: { 
      opacity: 1, 
      y: 0, 
      scale: 1,
      transition: { duration: 0.4, ease: "easeOut" as const }
    }
  }

  const contextMenuItems: ContextMenuEntry[] = [
    { id: "copy", label: "Copy Message", icon: <Copy size={14} />, shortcut: "⌘C", action: handleCopy },
    ...(isAssistant ? [{ id: "regenerate", label: "Regenerate", icon: <RefreshCw size={14} />, action: () => toast({ title: "Regenerate requested", variant: "default" }) }] : []),
    { type: "divider" as const },
    { id: "delete", label: "Delete Message", icon: <Trash2 size={14} />, danger: true, action: () => toast({ title: "Message deleted", variant: "default" }) },
  ]

  return (
    <ContextMenu items={contextMenuItems}>
    <motion.div 
      initial="hidden"
      animate="visible"
      variants={cardVariants}
      className={cn(
        "relative overflow-hidden rounded-xl border p-5 shadow-sm transition-all duration-300",
        isAssistant
          ? "bg-[var(--msg-assistant-bg)] backdrop-blur-xl border-[var(--msg-assistant-border)] hover:border-[var(--msg-assistant-hover-border)]"
          : "bg-[var(--msg-user-bg)] border-[var(--msg-user-border)]",
      )}
      style={isAssistant ? { boxShadow: 'var(--msg-assistant-shadow)' } : undefined}
    >
      {/* Decorative High-Tech Header Line */}
      {isAssistant && (
         <div 
           className="absolute left-0 top-0 h-[2px] w-full"
           style={{ background: 'var(--msg-header-line)' }}
         />
      )}

      {/* Decorative Corner Accents */}
      {isAssistant && (
          <div className="absolute top-0 right-0 p-2 text-[var(--msg-corner-icon)]">
              <Cpu size={24} className="opacity-50" />
          </div>
      )}

      {/* Header Info (Role & Actions) */}
      <div className="flex items-center justify-between mb-3 border-b border-dashed border-opacity-20 pb-2 border-gray-400">
        <div className="flex items-center gap-2">
            <span className={cn(
                "text-[10px] font-black tracking-widest uppercase",
                isAssistant ? "text-[var(--msg-role-text)]" : "text-[var(--msg-role-user-text)]"
            )}>
                {role === 'assistant' ? 'SYSTEM_RESPONSE' : 'USER_QUERY'}
            </span>
            {timestamp && (
                <span className="text-[10px] text-[var(--msg-timestamp-text)] font-mono opacity-60">
                    [{timestamp}]
                </span>
            )}
        </div>
        
        {/* Actions */}
        <div className="flex items-center gap-1">
            <button 
                onClick={handleCopy}
                className="p-1 rounded transition-colors text-[var(--msg-copy-text)] hover:bg-[var(--msg-copy-hover)]"
                aria-label={copied ? "Copied" : "Copy message content"}
                title="Copy content"
            >
                {copied ? <Check size={12} /> : <Copy size={12} />}
            </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="prose prose-sm max-w-none break-words dark:prose-invert prose-p:text-foreground/80 prose-headings:text-foreground/90 prose-pre:bg-surface-inset prose-pre:border-border">
        <ReactMarkdown
          components={{
             code({className, children, ...props}) {
               const match = /language-(\w+)/.exec(className || '')
               return match ? (
                 <div className="relative group rounded-lg overflow-hidden my-4 border border-opacity-20 bg-opacity-50">
                    <div className="flex items-center justify-between px-3 py-1 text-[10px] font-mono border-b bg-[var(--msg-code-block-header-bg)] border-[var(--msg-code-block-header-border)] text-[var(--msg-code-block-header-text)]">
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
                 <code className="rounded px-1 py-0.5 text-xs font-mono bg-[var(--msg-code-bg)] text-[var(--msg-code-text)]" {...props}>
                   {children}
                 </code>
               )
             }
          }}
        >
          {content}
        </ReactMarkdown>
      </div>

      {/* Footer — Timestamp */}
      {isAssistant && (
         <div className="mt-3 flex items-center gap-4 pt-2">
             <div className="flex items-center gap-1.5">
                 <div className="h-1.5 w-1.5 rounded-full bg-[var(--msg-dot-color)]" />
                 <span className="text-[9px] font-mono text-[var(--msg-timestamp-text)]">
                     {timestamp}
                 </span>
             </div>
         </div>
      )}
    </motion.div>
    </ContextMenu>
  )
}
