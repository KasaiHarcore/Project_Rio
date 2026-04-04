"use client"

import React from 'react'
import { cn } from '@/shared/lib/utils'
import { CHARACTERS, CharacterId } from '@/features/rio/types'
import Image from 'next/image'

/** Icon paths matching the actual files in /public/images/ */
const CHARACTER_ICONS: Record<string, string> = {
  rio: '/images/avatar.png',
}

function useActiveCharacter() {
  const char = CHARACTERS[0]
  const icon = CHARACTER_ICONS[char.id] ?? CHARACTER_ICONS.rio
  return { char, icon }
}

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

const imageSizes = { sm: 32, md: 48, lg: 72, xl: 88 }

export function AgentAvatar({ size = 'md', showGlow = false, className }: AgentAvatarProps) {
  const { char, icon } = useActiveCharacter()

  return (
    <div className="relative inline-block group/avatar">
      {/* Animated Halo Effect */}
      {showGlow && (
        <>
          <div className="absolute -top-4 left-1/2 -translate-x-1/2 w-16 h-4 rounded-[100%] blur-md animate-[pulse_3s_infinite] bg-[var(--avatar-glow)]" />
          <div className="absolute -top-6 left-1/2 -translate-x-1/2 w-20 h-2 bg-white/40 rounded-[100%] blur-sm animate-[pulse_4s_infinite]" />
        </>
      )}

      <div
        className={cn(
          'relative flex items-center justify-center overflow-hidden border shadow-[0_8px_30px_rgb(0,0,0,0.04)] transition-all duration-500 ease-in-out',
          sizeClasses[size],
          "bg-[var(--avatar-bg)] border-[var(--avatar-border)] hover:border-[var(--avatar-hover-border)]",
          showGlow && 'ring-4 ring-[var(--avatar-ring)]',
          'hover:scale-[1.02] hover:-translate-y-1',
          className
        )}
      >
        <Image
          src={icon}
          alt={char.name}
          width={imageSizes[size]}
          height={imageSizes[size]}
          className="object-contain"
        />
      </div>
    </div>
  )
}

export function AgentMessageAvatar({ className, characterId }: { className?: string; characterId?: CharacterId }) {
  const global = useActiveCharacter()

  const char = characterId
    ? (CHARACTERS.find(c => c.id === characterId) ?? global.char)
    : global.char
  const icon = characterId
    ? (CHARACTER_ICONS[characterId] ?? global.icon)
    : global.icon

  return (
    <div
      className={cn(
        'relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-xl border shadow-sm transition-all duration-300',
        "bg-[var(--avatar-bg)] border-[var(--avatar-border)] hover:border-[var(--avatar-hover-border)]",
        className
      )}
    >
      <Image
        src={icon}
        alt={char.name}
        width={32}
        height={32}
        className="object-contain"
      />
    </div>
  )
}
