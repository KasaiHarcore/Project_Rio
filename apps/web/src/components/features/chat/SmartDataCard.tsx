import React from 'react'
import { cn } from '@/lib/utils'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Copy, Check, Terminal, Cpu, RefreshCw, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from '@/hooks/use-toast'
import { ContextMenu, type ContextMenuEntry } from '@/components/ui/context-menu'

interface SmartDataCardProps {
  role: 'user' | 'assistant' | 'system' | 'data'
  content: string
  timestamp?: string
  /** Display name shown in the message header (e.g. character name or username) */
  senderName?: string
  /** When true, appends a blinking cursor after the content */
  isStreaming?: boolean
}

export function SmartDataCard({ role, content, timestamp, senderName, isStreaming }: SmartDataCardProps) {
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
                {senderName ?? (role === 'assistant' ? 'SYSTEM_RESPONSE' : 'USER_QUERY')}
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
          remarkPlugins={[remarkGfm]}
          components={{
            p({ children, ...props }) {
              return (
                <p className="my-2 whitespace-pre-wrap leading-relaxed" {...props}>
                  {children}
                </p>
              )
            },
            ul({ children, ...props }) {
              return (
                <ul className="my-2 list-disc pl-5" {...props}>
                  {children}
                </ul>
              )
            },
            ol({ children, ...props }) {
              return (
                <ol className="my-2 list-decimal pl-5" {...props}>
                  {children}
                </ol>
              )
            },
            li({ children, ...props }) {
              return (
                <li className="my-1" {...props}>
                  {children}
                </li>
              )
            },
            a({ children, href, ...props }) {
              return (
                <a
                  href={href}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="underline underline-offset-2"
                  {...props}
                >
                  {children}
                </a>
              )
            },
            table({ children, ...props }) {
              return (
                <div className="my-3 w-full overflow-x-auto">
                  <table className="w-full border-collapse text-xs" {...props}>
                    {children}
                  </table>
                </div>
              )
            },
            thead({ children, ...props }) {
              return (
                <thead className="bg-black/5 dark:bg-white/5" {...props}>
                  {children}
                </thead>
              )
            },
            tbody({ children, ...props }) {
              return (
                <tbody {...props}>
                  {children}
                </tbody>
              )
            },
            tr({ children, ...props }) {
              return (
                <tr className="border-b border-black/10 dark:border-white/10" {...props}>
                  {children}
                </tr>
              )
            },
            th({ children, ...props }) {
              return (
                <th className="px-3 py-2 text-left font-bold" {...props}>
                  {children}
                </th>
              )
            },
            td({ children, ...props }) {
              return (
                <td className="px-3 py-2 align-top" {...props}>
                  {children}
                </td>
              )
            },
            pre({ children }) {
              return <>{children}</>
            },
            code({ className, children, ...props }) {
              const match = /language-(\w+)/.exec(className || '')
              const isBlock = Boolean(match) || String(children).includes('\n')
              if (isBlock) {
                const text = String(children).replace(/\n$/, '')
                return (
                  <div className="relative group rounded-lg overflow-hidden my-4 border border-opacity-20 bg-opacity-50">
                    <div className="flex items-center justify-between px-3 py-1 text-[10px] font-mono border-b bg-[var(--msg-code-block-header-bg)] border-[var(--msg-code-block-header-border)] text-[var(--msg-code-block-header-text)]">
                      <div className="flex items-center gap-1">
                        <Terminal size={10} />
                        <span>{match ? match[1].toUpperCase() : 'CODE'}</span>
                      </div>
                    </div>
                    <pre className="m-0 overflow-x-auto p-3 bg-[var(--msg-code-block-bg)] text-[var(--msg-code-block-text)]">
                      <code className={className} {...props}>
                        {text}
                      </code>
                    </pre>
                  </div>
                )
              }

              return (
                <code
                  className={cn(
                    "rounded px-1 py-0.5 text-xs font-mono bg-[var(--msg-code-bg)] text-[var(--msg-code-text)]",
                    className,
                  )}
                  {...props}
                >
                  {children}
                </code>
              )
            },
          }}
        >
          {content}
        </ReactMarkdown>
        {isStreaming && (
          <span
            className="inline-block w-[2px] h-[1.1em] ml-0.5 align-middle rounded-sm bg-[var(--msg-role-text)]"
            style={{ animation: 'cursor-blink 1s step-end infinite' }}
          />
        )}
      </div>
      {isStreaming && (
        <style>{`@keyframes cursor-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }`}</style>
      )}
    </motion.div>
    </ContextMenu>
  )
}
