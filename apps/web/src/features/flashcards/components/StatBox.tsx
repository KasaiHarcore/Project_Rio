"use client"

import React from 'react'
import { cn } from '@/shared/lib/utils'

export interface StatBoxProps {
  icon: React.ReactNode
  label: string
  value: string | number
  highlight?: boolean
  color?: string
}

export function StatBox({
  icon,
  label,
  value,
  highlight = false,
  color = 'from-slate-600 to-slate-700',
}: StatBoxProps) {
  return (
    <div className="relative overflow-hidden rounded-2xl border p-5 shadow-sm bg-[var(--card-bg)] border-[var(--card-border)]">
      <div className={`absolute top-0 left-0 h-1 w-full bg-gradient-to-r ${color}`} />
      <p className={cn(
        'text-2xl font-black',
        highlight ? 'text-[var(--primary)]' : 'text-page-card-title',
      )}>
        {value}
      </p>
      <p className="text-[10px] font-bold tracking-wider text-page-muted uppercase">{label}</p>
    </div>
  )
}
