"use client"

import React from 'react'
import { cn } from '@/lib/utils'
import { agentConfig } from '@/lib/agent-config'

interface AgentAvatarProps {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  showGlow?: boolean
  className?: string
}

const sizeClasses = {
  sm: 'h-10 w-10 rounded-xl',
  md: 'h-14 w-14 rounded-2xl',
  lg: 'h-20 w-20 rounded-2xl',
  xl: 'h-24 w-24 rounded-3xl',
}

const textSizes = {
  sm: 'text-[10px]',
  md: 'text-xs',
  lg: 'text-lg',
  xl: 'text-xl',
}

export function AgentAvatar({ size = 'md', showGlow = false, className }: AgentAvatarProps) {
  const hasImage = !!agentConfig.avatar

  return (
    <div className="relative group/avatar">
       {/* Animated Halo Effect - Simple but Alive */}
       {showGlow && (
         <>
             <div className="absolute -top-4 left-1/2 -translate-x-1/2 w-16 h-4 bg-blue-400/30 rounded-[100%] blur-md animate-[pulse_3s_infinite]" />
             <div className="absolute -top-6 left-1/2 -translate-x-1/2 w-20 h-2 bg-white/40 rounded-[100%] blur-sm animate-[pulse_4s_infinite]" />
         </>
       )}

        <div
            className={cn(
                'relative flex items-center justify-center overflow-hidden border bg-white shadow-[0_8px_30px_rgb(0,0,0,0.04)] transition-all duration-500 ease-in-out',
                sizeClasses[size],
                'border-blue-100 hover:border-blue-300',
                showGlow && 'ring-4 ring-blue-100/50',
                // Hover "Breath" effect
                'hover:scale-[1.02] hover:-translate-y-1',
                className
            )}
        >
        
        {hasImage ? (
            <img
            src={agentConfig.avatar!}
            alt={agentConfig.name}
            className="h-full w-full object-cover transition-transform duration-700 hover:scale-110"
            />
        ) : (
            <>
            <div className="absolute inset-0 bg-gradient-to-br from-blue-50/50 to-transparent"></div>
            <span className={cn('font-black text-blue-600/50', textSizes[size])}>AI</span>
            </>
        )}
        </div>
    </div>
  )
}

// Compact version for message avatars
export function AgentMessageAvatar({ className }: { className?: string }) {
  const hasImage = !!agentConfig.avatar

  return (
    <div
      className={cn(
        'relative flex h-14 w-14 items-center justify-center overflow-hidden rounded-2xl border border-blue-100 bg-white shadow-[0_8px_30px_rgb(0,0,0,0.04)] transition-all duration-300 hover:scale-110 hover:border-blue-300',
        className
      )}
    >
      {hasImage ? (
        <img
          src={agentConfig.avatar!}
          alt={agentConfig.name}
          className="h-full w-full object-cover"
        />
      ) : (
        <>
          <div className="absolute inset-0 bg-gradient-to-br from-blue-50/50 to-transparent"></div>
          <span className="text-xs font-black text-blue-600/50">AI</span>
        </>
      )}
    </div>
  )
}
