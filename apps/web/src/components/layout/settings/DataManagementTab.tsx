"use client"

import React, { useState } from 'react'
import { Download, Archive, AlertTriangle, Trash2, Database, FileText } from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { DangerButton, SectionHeader } from './primitives'

// ─── Component ──────────────────────────────────────────────────────

export function DataManagementTab() {
  const [exportFormat, setExportFormat] = useState<'json' | 'csv' | 'md'>('json')

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Export */}
      <section>
        <SectionHeader title="Export Data" />
        <div className="rounded-2xl border p-6 bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
          <p className="text-sm font-bold text-[var(--settings-section-title)] mb-1">Export Chat History</p>
          <p className="text-xs text-slate-400 mb-4">Download all your conversations in the format of your choice.</p>
          <div className="flex items-center gap-3">
            {(['json', 'csv', 'md'] as const).map((fmt) => (
              <button key={fmt} onClick={() => setExportFormat(fmt)}
                className={cn("px-4 py-2 rounded-xl text-xs font-bold uppercase border transition-all",
                  exportFormat === fmt
                    ? "bg-[var(--settings-tab-active-bg)] text-white border-transparent"
                    : "bg-transparent border-[var(--settings-card-border)] text-[var(--settings-section-title)] hover:border-[var(--settings-input-focus-border)]"
                )}>
                .{fmt}
              </button>
            ))}
            <button className="ml-auto flex items-center gap-2 px-5 py-2 rounded-xl text-xs font-bold bg-[var(--settings-tab-active-bg)] text-white transition-all hover:opacity-90 active:scale-[0.98]">
              <Download className="h-4 w-4" /> Export
            </button>
          </div>
        </div>
      </section>

      {/* Archive */}
      <section>
        <SectionHeader title="Archive" />
        <div className="rounded-2xl border p-6 flex items-center justify-between bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
          <div className="flex items-center gap-4">
            <div className="h-10 w-10 rounded-xl bg-amber-500/10 flex items-center justify-center flex-shrink-0">
              <Archive className="h-5 w-5 text-amber-500" />
            </div>
            <div>
              <p className="text-sm font-bold text-[var(--settings-section-title)]">Archive All History</p>
              <p className="text-xs text-slate-400 mt-0.5">Move all conversations to archive. They can be restored later.</p>
            </div>
          </div>
          <button className="px-4 py-2 rounded-xl text-xs font-bold border transition-all text-amber-600 border-amber-200 hover:bg-amber-500 hover:text-white hover:border-amber-500">
            Archive
          </button>
        </div>
      </section>

      {/* Danger Zone */}
      <section>
        <SectionHeader title="Danger Zone" badge={<span className="text-[10px] font-bold text-red-400 flex items-center gap-1"><AlertTriangle className="h-3 w-3" /> IRREVERSIBLE</span>} />
        <div className="space-y-3">
          <DangerButton icon={Trash2} label="Delete History" description="Permanently delete all chat conversations" onClick={() => {}} confirmLabel="Click again to confirm" />
          <DangerButton icon={Database} label="Clear Knowledge Base" description="Remove all uploaded documents from the vector store" onClick={() => {}} confirmLabel="Click again to confirm" />
          <DangerButton icon={FileText} label="Clear Artifacts" description="Delete all generated artifacts and cached outputs" onClick={() => {}} confirmLabel="Click again to confirm" />
        </div>
      </section>
    </div>
  )
}
