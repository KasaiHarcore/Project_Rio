"use client"

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/shared/lib/utils'

// ─── Reusable Settings Primitives ──────────────────────────────────

export function SettingsInput({ label, type = 'text', placeholder, value, onChange, rightElement, className }: {
  label: string; type?: string; placeholder?: string; value: string; onChange: (v: string) => void; rightElement?: React.ReactNode; className?: string
}) {
  return (
    <div className={cn("rounded-2xl border p-4 transition-colors bg-[var(--settings-input-bg)] border-[var(--settings-input-border)] focus-within:border-[var(--settings-input-focus-border)] focus-within:bg-[var(--settings-input-focus-bg)]", className)}>
      <label className="text-[9px] font-black tracking-widest uppercase block mb-1.5 text-[var(--settings-input-label)]">{label}</label>
      <div className="flex items-center gap-2">
        <input type={type} placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)}
          className="w-full bg-transparent font-mono text-sm font-bold outline-none text-[var(--settings-input-text)] placeholder:text-slate-400/50" />
        {rightElement}
      </div>
    </div>
  )
}

export function SettingsTextarea({ label, placeholder, value, onChange, rows = 6, hint }: {
  label: string; placeholder?: string; value: string; onChange: (v: string) => void; rows?: number; hint?: string
}) {
  return (
    <div className="rounded-2xl border p-4 transition-colors bg-[var(--settings-input-bg)] border-[var(--settings-input-border)] focus-within:border-[var(--settings-input-focus-border)] focus-within:bg-[var(--settings-input-focus-bg)]">
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-[9px] font-black tracking-widest uppercase text-[var(--settings-input-label)]">{label}</label>
        {hint && <span className="text-[9px] font-bold text-slate-400">{hint}</span>}
      </div>
      <textarea placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)} rows={rows}
        className="w-full bg-transparent text-sm font-medium outline-none resize-none text-[var(--settings-input-text)] placeholder:text-slate-400/50 leading-relaxed" />
    </div>
  )
}

export function Toggle({ enabled, onChange }: { enabled: boolean; onChange: (v: boolean) => void }) {
  return (
    <button onClick={() => onChange(!enabled)}
      className={cn("h-6 w-11 rounded-full relative cursor-pointer transition-colors flex-shrink-0",
        enabled ? "bg-[var(--settings-tab-active-bg)]" : "bg-[var(--settings-toggle-bg)]"
      )}>
      <div className={cn("absolute top-1 h-4 w-4 bg-white rounded-full shadow-sm transition-transform",
        enabled ? "translate-x-[22px]" : "translate-x-1"
      )} />
    </button>
  )
}

export function ToggleRow({ label, description, enabled, onChange }: {
  label: string; description: string; enabled: boolean; onChange: (v: boolean) => void
}) {
  return (
    <div className="rounded-2xl border p-5 flex items-center justify-between bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
      <div className="pr-4">
        <p className="text-sm font-bold text-[var(--settings-section-title)]">{label}</p>
        <p className="text-xs text-slate-400 mt-1">{description}</p>
      </div>
      <Toggle enabled={enabled} onChange={onChange} />
    </div>
  )
}

export function DangerButton({ icon: Icon, label, description, onClick, confirmLabel }: {
  icon: React.ComponentType<Record<string, unknown>>; label: string; description: string; onClick: () => void; confirmLabel?: string
}) {
  const [confirming, setConfirming] = useState(false)
  const handleClick = () => {
    if (confirmLabel && !confirming) { setConfirming(true); setTimeout(() => setConfirming(false), 3000); return }
    onClick(); setConfirming(false)
  }
  return (
    <div className="rounded-2xl border p-5 flex items-center justify-between bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
      <div className="flex items-center gap-4">
        <div className="h-10 w-10 rounded-xl bg-red-500/10 flex items-center justify-center flex-shrink-0">
          <Icon className="h-5 w-5 text-red-500" />
        </div>
        <div>
          <p className="text-sm font-bold text-[var(--settings-section-title)]">{label}</p>
          <p className="text-xs text-slate-400 mt-0.5">{description}</p>
        </div>
      </div>
      <button onClick={handleClick}
        className={cn("px-4 py-2 rounded-xl text-xs font-bold transition-all border",
          confirming ? "bg-red-500 text-white border-red-500 animate-pulse" : "bg-transparent text-red-500 border-red-200 hover:bg-red-500 hover:text-white hover:border-red-500"
        )}>
        {confirming ? (confirmLabel || 'Confirm?') : label}
      </button>
    </div>
  )
}

export function SectionHeader({ title, badge }: { title: string; badge?: React.ReactNode }) {
  return (
    <div className="flex items-end justify-between border-b pb-3 mb-6 border-[var(--settings-section-border)]">
      <h3 className="text-xl font-black tracking-tight text-[var(--settings-section-title)]">{title}</h3>
      {badge}
    </div>
  )
}

export function SaveMessage({ type, message }: { type: 'success' | 'error'; message: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      className={cn(
        "text-xs font-bold px-4 py-2 rounded-xl",
        type === 'success' ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"
      )}
    >
      {message}
    </motion.div>
  )
}
