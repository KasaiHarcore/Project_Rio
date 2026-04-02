"use client"

import React from 'react'
import { AgentMessageAvatar } from '@/components/ui/agent-avatar'

/**
 * Three bouncing dots typing indicator, styled to match agent message bubbles.
 * Shown when status is 'submitted' (before first token arrives).
 */
export function TypingIndicator() {
  return (
    <div className="mx-auto flex max-w-5xl items-start gap-4">
      <div className="flex flex-col items-center flex-shrink-0 mt-1 gap-1">
        <AgentMessageAvatar />
      </div>
      <div className="flex-1 min-w-0 max-w-[85%]">
        <div className="relative overflow-hidden rounded-xl border p-5 shadow-sm bg-[var(--msg-assistant-bg)] backdrop-blur-xl border-[var(--msg-assistant-border)]">
          <div className="absolute left-0 top-0 h-[2px] w-full" style={{ background: 'var(--msg-header-line)' }} />
          <div className="flex items-center gap-1.5 h-5">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="inline-block h-2 w-2 rounded-full bg-[var(--msg-role-text)] opacity-60"
                style={{
                  animation: 'typing-bounce 1.4s ease-in-out infinite',
                  animationDelay: `${i * 0.2}s`,
                }}
              />
            ))}
          </div>
        </div>
      </div>
      <style jsx>{`
        @keyframes typing-bounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
          30% { transform: translateY(-6px); opacity: 1; }
        }
      `}</style>
    </div>
  )
}
