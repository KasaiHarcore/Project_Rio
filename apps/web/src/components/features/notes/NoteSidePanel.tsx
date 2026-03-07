"use client"

import React from 'react'
import { cn } from '@/lib/utils'
import { useNoteStore, type NoteBlock } from '@/store/note-store'
import {
    Headphones, FileText, ListTree,
    Upload, Play, Pause, SkipForward, SkipBack,
    Volume2,
} from 'lucide-react'

/* ═══════════════════════════════════════════════════════════════════ */

type Tab = 'audio' | 'transcript' | 'outline'

const TABS: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: 'audio', label: 'Audio', icon: Headphones },
    { id: 'transcript', label: 'Transcript', icon: FileText },
    { id: 'outline', label: 'Outline', icon: ListTree },
]

/* ═══════════════════════════════════════════════════════════════════ */

export function NoteSidePanel() {
    const activeNote = useNoteStore((s) => s.getActiveNote())
    const sidePanelTab = useNoteStore((s) => s.sidePanelTab)
    const setSidePanelTab = useNoteStore((s) => s.setSidePanelTab)

    const headings = React.useMemo(() => {
        if (!activeNote?.content) return []
        const matches = activeNote.content.match(/^#{1,6}\s+(.*)$/gm)
        return matches?.map((m, i) => ({
            id: `heading-${i}`,
            content: m.replace(/^#+\s+/, ''),
            type: 'heading' as const
        })) ?? []
    }, [activeNote?.content])

    return (
        <aside className="w-72 flex flex-col border-l overflow-hidden bg-[var(--note-sidepanel-bg)] border-[var(--note-sidepanel-border)]">
            {/* Tab bar */}
            <div className="flex items-center border-b border-[var(--note-sidepanel-border)] px-2 py-2">
                {TABS.map((tab) => {
                    const isActive = sidePanelTab === tab.id
                    return (
                        <button
                            key={tab.id}
                            onClick={() => setSidePanelTab(tab.id)}
                            className={cn(
                                "flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider transition-all",
                                isActive
                                    ? "text-[var(--note-sidepanel-tab-active)] bg-[var(--note-sidepanel-tab-active)]/10"
                                    : "text-[var(--note-sidepanel-tab-inactive)] hover:text-[var(--note-text)] hover:bg-white/5"
                            )}
                        >
                            <tab.icon className="h-3.5 w-3.5" />
                            <span className="hidden xl:inline">{tab.label}</span>
                        </button>
                    )
                })}
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-y-auto custom-scrollbar">
                {sidePanelTab === 'audio' && <AudioTab />}
                {sidePanelTab === 'transcript' && <TranscriptTab />}
                {sidePanelTab === 'outline' && <OutlineTab headings={headings} />}
            </div>
        </aside>
    )
}

/* ── Audio Tab ── */
function AudioTab() {
    return (
        <div className="p-4 space-y-4">
            {/* Upload zone */}
            <div className="rounded-xl border-2 border-dashed border-[var(--note-collection-border)] p-6 text-center hover:border-[var(--note-accent)]/30 transition-colors cursor-pointer">
                <Upload className="h-8 w-8 mx-auto mb-2 text-[var(--note-muted)]" />
                <p className="text-xs font-bold text-[var(--note-muted)]">
                    Upload audio file
                </p>
                <p className="text-[10px] text-[var(--note-muted)]/60 mt-1">
                    MP3, WAV, M4A supported
                </p>
            </div>

            {/* Player placeholder */}
            <div className="rounded-xl bg-[var(--note-card-bg)] border border-[var(--note-card-border)] p-3">
                {/* Progress bar */}
                <div className="h-1 rounded-full bg-white/10 mb-3 overflow-hidden">
                    <div className="h-full w-0 rounded-full bg-[var(--note-accent)] transition-all" />
                </div>

                {/* Time */}
                <div className="flex items-center justify-between text-[9px] font-mono text-[var(--note-muted)] mb-3">
                    <span>0:00</span>
                    <span>0:00</span>
                </div>

                {/* Controls */}
                <div className="flex items-center justify-center gap-3">
                    <button className="p-1.5 rounded-lg text-[var(--note-muted)] hover:text-[var(--note-text)] transition-colors">
                        <SkipBack size={16} />
                    </button>
                    <button className="p-3 rounded-full bg-[var(--note-accent)]/20 text-[var(--note-accent)] hover:bg-[var(--note-accent)]/30 transition-colors">
                        <Play size={18} />
                    </button>
                    <button className="p-1.5 rounded-lg text-[var(--note-muted)] hover:text-[var(--note-text)] transition-colors">
                        <SkipForward size={16} />
                    </button>
                </div>

                {/* Volume */}
                <div className="flex items-center gap-2 mt-3">
                    <Volume2 size={12} className="text-[var(--note-muted)]" />
                    <div className="flex-1 h-1 rounded-full bg-white/10">
                        <div className="h-full w-3/4 rounded-full bg-[var(--note-muted)]" />
                    </div>
                </div>
            </div>

            <p className="text-[9px] text-center text-[var(--note-muted)]/50 font-bold uppercase tracking-wider">
                Audio features coming soon
            </p>
        </div>
    )
}

/* ── Transcript Tab ── */
function TranscriptTab() {
    const activeNote = useNoteStore((s) => s.getActiveNote())
    const transcript = activeNote?.audio?.transcript

    return (
        <div className="p-4">
            {transcript ? (
                <div className="space-y-3">
                    {transcript.split('\n\n').map((para, i) => (
                        <p key={i} className="text-xs leading-relaxed text-[var(--note-text)]">
                            {para}
                        </p>
                    ))}
                </div>
            ) : (
                <div className="text-center py-12">
                    <FileText className="h-8 w-8 mx-auto mb-2 text-[var(--note-muted)]/30" />
                    <p className="text-xs font-bold text-[var(--note-muted)]">No transcript</p>
                    <p className="text-[10px] text-[var(--note-muted)]/60 mt-1">
                        Upload audio to generate a transcript
                    </p>
                </div>
            )}
        </div>
    )
}

/* ── Outline Tab ── */
function OutlineTab({ headings }: { headings: NoteBlock[] }) {
    const setActiveNoteId = useNoteStore((s) => s.setActiveNoteId)

    return (
        <div className="p-4">
            {headings.length === 0 ? (
                <div className="text-center py-12">
                    <ListTree className="h-8 w-8 mx-auto mb-2 text-[var(--note-muted)]/30" />
                    <p className="text-xs font-bold text-[var(--note-muted)]">No headings</p>
                    <p className="text-[10px] text-[var(--note-muted)]/60 mt-1">
                        Add heading blocks to build an outline
                    </p>
                </div>
            ) : (
                <div className="space-y-1">
                    {headings.map((h) => (
                        <div
                            key={h.id}
                            className="group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-all hover:bg-white/5"
                        >
                            <div className="w-1 h-4 rounded-full bg-[var(--note-accent)]/40 group-hover:bg-[var(--note-accent)] transition-colors" />
                            <span className="text-sm font-semibold text-[var(--note-heading)] truncate">
                                {h.content || 'Untitled section'}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
