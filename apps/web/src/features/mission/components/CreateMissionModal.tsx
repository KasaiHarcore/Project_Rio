"use client"

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import {
    Calendar as CalendarIcon,
    Clock,
    Loader2,
    Plus,
    X,
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import type { Mission, MissionPriority } from '@/features/mission/types'

/* ═══════════════════════════════════════════════════════════════════
 * CREATE MISSION MODAL — Notion-style rich creation form
 * ═══════════════════════════════════════════════════════════════════ */

interface CreateMissionModalProps {
    categories: string[]
    onClose: () => void
    onCreate: (data: Partial<Mission>) => Promise<void>
}

export function CreateMissionModal({ categories, onClose, onCreate }: CreateMissionModalProps) {
    const [title, setTitle] = useState('')
    const [description, setDescription] = useState('')
    const [priority, setPriority] = useState<MissionPriority>('normal')
    const [stepsText, setStepsText] = useState('')
    const [deadline, setDeadline] = useState('')
    const [scheduledStart, setScheduledStart] = useState('')
    const [estimatedMinutes, setEstimatedMinutes] = useState('')
    const [category, setCategory] = useState('')
    const [newCategory, setNewCategory] = useState('')
    const [notes, setNotes] = useState('')
    const [meetUrl, setMeetUrl] = useState('')
    const [tagsText, setTagsText] = useState('')
    const [submitting, setSubmitting] = useState(false)

    const effectiveCategory = category === '__new__' ? newCategory.trim() : (category || null)

    const handleSubmit = async () => {
        if (!title.trim()) return
        setSubmitting(true)
        const steps = stepsText
            .split('\n')
            .map((l) => l.trim())
            .filter(Boolean)
            .map((text) => ({ text, done: false }))
        const tags = tagsText
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean)
        await onCreate({
            title: title.trim(),
            description: description.trim() || null,
            priority,
            steps,
            tags,
            source: 'user',
            status: 'active',
            deadline: deadline ? new Date(deadline).toISOString() : null,
            scheduled_start: scheduledStart ? new Date(scheduledStart).toISOString() : null,
            estimated_minutes: estimatedMinutes ? Number(estimatedMinutes) : null,
            category: effectiveCategory || null,
            notes: notes.trim() || null,
            meet_url: meetUrl.trim() || null,
        })
        setSubmitting(false)
    }

    const inputCn = cn(
        "w-full px-3 py-2 rounded-lg text-sm outline-none border transition-colors",
        "bg-slate-900 border-slate-800 text-slate-200 placeholder:text-slate-600 focus:border-rose-600"
    )

    const labelCn = cn("text-[10px] font-bold uppercase tracking-wider mb-1 block", "text-slate-500")

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
            onClick={onClose}
        >
            <motion.div
                initial={{ scale: 0.95, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.95, y: 20 }}
                className={cn(
                    "w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-2xl border-2 shadow-2xl",
                    "bg-[#0a0e14] border-rose-900/30"
                )}
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className={cn("flex items-center justify-between px-6 py-4 border-b", "border-slate-800")}>
                    <h2 className="text-lg font-black text-page-title">New Mission</h2>
                    <button onClick={onClose} className={cn("p-1.5 rounded-lg", "text-slate-500 hover:text-rose-400 hover:bg-rose-900/20")}>
                        <X size={18} />
                    </button>
                </div>

                <div className="px-6 py-5 space-y-4">
                    {/* Title */}
                    <div>
                        <input
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="Mission title..."
                            maxLength={200}
                            className={cn(inputCn, "text-lg font-bold")}
                            autoFocus
                        />
                    </div>

                    {/* Description */}
                    <div>
                        <label className={labelCn}>Description</label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="What is this mission about?"
                            rows={2}
                            maxLength={2000}
                            className={cn(inputCn, "resize-none")}
                        />
                    </div>

                    {/* Row: Priority + Category */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className={labelCn}>Priority</label>
                            <div className="flex gap-1.5">
                                {(['low', 'normal', 'critical'] as MissionPriority[]).map((p) => (
                                    <button
                                        key={p}
                                        onClick={() => setPriority(p)}
                                        className={cn(
                                            "flex-1 text-[10px] uppercase font-bold py-2 rounded-lg transition-all",
                                            priority === p
                                                ? "bg-rose-600 text-white"
                                                : "bg-slate-800 text-slate-500 hover:text-rose-400"
                                        )}
                                    >
                                        {p}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <div>
                            <label className={labelCn}>Category</label>
                            <select
                                value={category}
                                onChange={(e) => setCategory(e.target.value)}
                                className={cn(inputCn, "appearance-none cursor-pointer")}
                            >
                                <option className="bg-[#0f172a] text-[#e2e8f0]" value="">None</option>
                                {categories.map((c) => (
                                    <option className="bg-[#0f172a] text-[#e2e8f0]" key={c} value={c}>{c}</option>
                                ))}
                                <option className="bg-[#0f172a] text-[#e2e8f0]" value="__new__">+ New Category</option>
                            </select>
                            {category === '__new__' && (
                                <input
                                    value={newCategory}
                                    onChange={(e) => setNewCategory(e.target.value)}
                                    placeholder="Category name..."
                                    maxLength={100}
                                    className={cn(inputCn, "mt-2")}
                                />
                            )}
                        </div>
                    </div>

                    {/* Row: Deadline + Scheduled Start + Time Estimate */}
                    <div className="grid grid-cols-3 gap-4">
                        <div>
                            <label className={labelCn}>
                                <CalendarIcon size={10} className="inline mr-1 -mt-0.5" />
                                Deadline
                            </label>
                            <input
                                type="datetime-local"
                                value={deadline}
                                onChange={(e) => setDeadline(e.target.value)}
                                className={inputCn}
                                style={{ colorScheme: 'dark' }}
                            />
                        </div>
                        <div>
                            <label className={labelCn}>
                                <CalendarIcon size={10} className="inline mr-1 -mt-0.5" />
                                Start Date
                            </label>
                            <input
                                type="datetime-local"
                                value={scheduledStart}
                                onChange={(e) => setScheduledStart(e.target.value)}
                                className={inputCn}
                                style={{ colorScheme: 'dark' }}
                            />
                        </div>
                        <div>
                            <label className={labelCn}>
                                <Clock size={10} className="inline mr-1 -mt-0.5" />
                                Time Estimate
                            </label>
                            <div className="flex items-center gap-2">
                                <input
                                    type="number"
                                    min={1}
                                    max={14400}
                                    value={estimatedMinutes}
                                    onChange={(e) => setEstimatedMinutes(e.target.value)}
                                    placeholder="0"
                                    className={cn(inputCn, "flex-1")}
                                />
                                <span className={cn("text-xs font-bold shrink-0", "text-slate-600")}>min</span>
                            </div>
                        </div>
                    </div>

                    {/* Tags */}
                    <div>
                        <label className={labelCn}>Tags (comma-separated)</label>
                        <input
                            value={tagsText}
                            onChange={(e) => setTagsText(e.target.value)}
                            placeholder="e.g. study, backend, react"
                            className={inputCn}
                        />
                    </div>

                    {/* Steps */}
                    <div>
                        <label className={labelCn}>Checklist Steps (one per line)</label>
                        <textarea
                            value={stepsText}
                            onChange={(e) => setStepsText(e.target.value)}
                            placeholder={"Read documentation\nBuild prototype\nWrite tests"}
                            rows={4}
                            className={cn(inputCn, "resize-none font-mono text-xs")}
                        />
                    </div>

                    {/* Notes & Meet URL */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className={labelCn}>Notes (additional context)</label>
                            <textarea
                                value={notes}
                                onChange={(e) => setNotes(e.target.value)}
                                placeholder="Any extra details, links, references..."
                                rows={2}
                                maxLength={10000}
                                className={cn(inputCn, "resize-none")}
                            />
                        </div>
                        <div>
                            <label className={labelCn}>Meeting Link</label>
                            <input
                                value={meetUrl}
                                onChange={(e) => setMeetUrl(e.target.value)}
                                placeholder="https://meet.google.com/..."
                                className={inputCn}
                            />
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className={cn("flex items-center justify-end gap-3 px-6 py-4 border-t", "border-slate-800")}>
                    <button
                        onClick={onClose}
                        className={cn("px-5 py-2.5 rounded-xl font-bold text-sm transition-colors", "text-slate-400 hover:bg-slate-800")}
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={!title.trim() || submitting}
                        className={cn(
                            "px-6 py-2.5 rounded-xl font-bold text-sm transition-colors flex items-center gap-2",
                            "bg-rose-600 hover:bg-rose-700 text-white disabled:bg-slate-800 disabled:text-slate-600"
                        )}
                    >
                        {submitting ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
                        CREATE MISSION
                    </button>
                </div>
            </motion.div>
        </motion.div>
    )
}
