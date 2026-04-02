"use client"

import React, { useState, useEffect } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { Zap, Plus, Play, Loader2, Trash2, Clock, Calendar, Hash, Power } from 'lucide-react'
import { cn } from "@/shared/lib/utils"
import { toast } from "@/shared/hooks/use-toast"
import { useAutomationStore } from '@/features/automations/store'
import type { AutomationCreate } from '@/features/automations/api'

/* ── Cron helpers ── */

function cronToHuman(expr: string): string {
  const trimmed = expr.trim()
  if (trimmed === '0 * * * *') return 'Every hour'
  if (trimmed === '0 9 * * *') return 'Every day at 9:00 AM'
  if (trimmed === '0 9 * * 1') return 'Every Monday at 9:00 AM'
  if (trimmed === '0 9 * * 1-5') return 'Every weekday at 9:00 AM'

  const match6h = trimmed.match(/^0 \*\/(\d+) \* \* \*$/)
  if (match6h) return `Every ${match6h[1]} hours`

  const matchDaily = trimmed.match(/^(\d+) (\d+) \* \* \*$/)
  if (matchDaily) {
    const h = parseInt(matchDaily[2])
    const ampm = h >= 12 ? 'PM' : 'AM'
    const h12 = h === 0 ? 12 : h > 12 ? h - 12 : h
    return `Every day at ${h12}:${matchDaily[1].padStart(2, '0')} ${ampm}`
  }

  return trimmed
}

const CRON_PRESETS = [
  { label: 'Every hour', value: '0 * * * *' },
  { label: 'Daily 9am', value: '0 9 * * *' },
  { label: 'Every Monday', value: '0 9 * * 1' },
  { label: 'Weekdays', value: '0 9 * * 1-5' },
  { label: 'Every 6h', value: '0 */6 * * *' },
]

const TIMEZONES = [
  'UTC',
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Paris',
  'Europe/Berlin',
  'Asia/Tokyo',
  'Asia/Shanghai',
  'Asia/Kolkata',
  'Australia/Sydney',
]

export function AutomationsView() {
  const {
    automations, loading, running,
    fetchAutomations, createAutomation, deleteAutomation, toggleEnabled, runAutomation,
  } = useAutomationStore()

  const [showCreate, setShowCreate] = useState(false)
  const [formName, setFormName] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [formInstruction, setFormInstruction] = useState('')
  const [formCron, setFormCron] = useState('0 9 * * *')
  const [formAgentMode, setFormAgentMode] = useState('chat')
  const [formDelivery, setFormDelivery] = useState('notification')
  const [formTimezone, setFormTimezone] = useState('UTC')
  const [formMaxRuns, setFormMaxRuns] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    fetchAutomations()
  }, [fetchAutomations])

  const resetForm = () => {
    setFormName('')
    setFormDescription('')
    setFormInstruction('')
    setFormCron('0 9 * * *')
    setFormAgentMode('chat')
    setFormDelivery('notification')
    setFormTimezone('UTC')
    setFormMaxRuns('')
  }

  const handleCreate = async () => {
    if (!formName.trim() || !formInstruction.trim() || !formCron.trim()) {
      toast({ title: 'Missing fields', description: 'Name, instruction, and cron are required.', variant: 'warning' })
      return
    }

    setCreating(true)
    const data: AutomationCreate = {
      name: formName.trim(),
      description: formDescription.trim() || undefined,
      cron_expression: formCron.trim(),
      timezone: formTimezone,
      agent_instruction: formInstruction.trim(),
      agent_mode: formAgentMode,
      result_delivery: formDelivery,
      max_runs: formMaxRuns ? parseInt(formMaxRuns) : undefined,
    }

    const result = await createAutomation(data)
    setCreating(false)

    if (result) {
      toast({ title: 'Automation created', description: `"${result.name}" is now scheduled.`, variant: 'success' })
      resetForm()
      setShowCreate(false)
    } else {
      toast({ title: 'Failed to create automation', variant: 'error' })
    }
  }

  const handleDelete = async (id: string, name: string) => {
    const ok = await deleteAutomation(id)
    if (ok) {
      toast({ title: 'Automation deleted', description: `"${name}" removed.`, variant: 'success' })
    } else {
      toast({ title: 'Failed to delete', variant: 'error' })
    }
  }

  const handleRun = async (id: string, name: string) => {
    const answer = await runAutomation(id)
    if (answer !== null) {
      toast({ title: 'Run completed', description: `"${name}" finished successfully.`, variant: 'success' })
    } else {
      toast({ title: 'Run failed', description: `"${name}" encountered an error.`, variant: 'error' })
    }
  }

  return (
    <DashboardLayout>
      <PageTransition className="flex-1 flex flex-col overflow-hidden bg-[var(--page-bg)]">
        {/* Header */}
        <header className="relative flex h-16 items-center justify-between border-b px-8 backdrop-blur-md flex-shrink-0 border-[var(--page-header-border)] bg-[var(--page-header-bg)]">
          <div className="absolute bottom-0 left-0 h-[1px] w-full opacity-50 bg-gradient-to-r from-transparent via-[var(--page-header-line)] to-transparent" />

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-xl shadow-lg",
                  "bg-gradient-to-br from-amber-700 to-amber-900"
                )}
                style={{ boxShadow: '0 10px 15px -3px var(--page-icon-shadow)' }}
              >
                <Zap className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-black text-page-title">Automations</h1>
                <p className="text-[10px] font-bold tracking-wider uppercase text-page-subtitle">Scheduled Tasks</p>
              </div>
            </div>
          </div>

          <button
            onClick={() => setShowCreate(!showCreate)}
            className="bg-[var(--primary)] text-white rounded-lg px-4 py-2 text-sm font-medium hover:opacity-90 flex items-center gap-2"
          >
            <Plus className="h-4 w-4" />
            Create
          </button>
        </header>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 lg:p-8">
          {/* Create Form */}
          {showCreate && (
            <div className="mb-8 rounded-2xl border p-6 bg-[var(--card-bg)] border-[var(--card-border)]">
              <h2 className="text-sm font-bold text-page-card-title mb-4">New Automation</h2>

              <div className="grid gap-4 md:grid-cols-2">
                {/* Name */}
                <div>
                  <label className="text-[10px] font-bold tracking-wider uppercase text-page-muted mb-1 block">Name</label>
                  <input
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    placeholder="Daily summary..."
                    className="w-full bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                  />
                </div>

                {/* Description */}
                <div>
                  <label className="text-[10px] font-bold tracking-wider uppercase text-page-muted mb-1 block">Description</label>
                  <input
                    value={formDescription}
                    onChange={(e) => setFormDescription(e.target.value)}
                    placeholder="Optional description..."
                    className="w-full bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                  />
                </div>

                {/* Agent Mode */}
                <div>
                  <label className="text-[10px] font-bold tracking-wider uppercase text-page-muted mb-1 block">Agent Mode</label>
                  <select
                    value={formAgentMode}
                    onChange={(e) => setFormAgentMode(e.target.value)}
                    className="w-full bg-[#161b22] border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                  >
                    <option className="bg-[#161b22] text-[#e6edf3]" value="chat">Chat</option>
                    <option className="bg-[#161b22] text-[#e6edf3]" value="rag">RAG</option>
                    <option className="bg-[#161b22] text-[#e6edf3]" value="web">Web</option>
                  </select>
                </div>

                {/* Result Delivery */}
                <div>
                  <label className="text-[10px] font-bold tracking-wider uppercase text-page-muted mb-1 block">Result Delivery</label>
                  <select
                    value={formDelivery}
                    onChange={(e) => setFormDelivery(e.target.value)}
                    className="w-full bg-[#161b22] border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                  >
                    <option className="bg-[#161b22] text-[#e6edf3]" value="notification">Notification</option>
                    <option className="bg-[#161b22] text-[#e6edf3]" value="note">Note</option>
                    <option className="bg-[#161b22] text-[#e6edf3]" value="chat_thread">Chat Thread</option>
                  </select>
                </div>

                {/* Timezone */}
                <div>
                  <label className="text-[10px] font-bold tracking-wider uppercase text-page-muted mb-1 block">Timezone</label>
                  <select
                    value={formTimezone}
                    onChange={(e) => setFormTimezone(e.target.value)}
                    className="w-full bg-[#161b22] border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                  >
                    {TIMEZONES.map((tz) => (
                      <option className="bg-[#161b22] text-[#e6edf3]" key={tz} value={tz}>{tz}</option>
                    ))}
                  </select>
                </div>

                {/* Max Runs */}
                <div>
                  <label className="text-[10px] font-bold tracking-wider uppercase text-page-muted mb-1 block">Max Runs (optional)</label>
                  <input
                    type="number"
                    min="1"
                    value={formMaxRuns}
                    onChange={(e) => setFormMaxRuns(e.target.value)}
                    placeholder="Unlimited"
                    className="w-full bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                  />
                </div>
              </div>

              {/* Agent Instruction */}
              <div className="mt-4">
                <label className="text-[10px] font-bold tracking-wider uppercase text-page-muted mb-1 block">Agent Instruction</label>
                <textarea
                  rows={3}
                  value={formInstruction}
                  onChange={(e) => setFormInstruction(e.target.value)}
                  placeholder="What should the agent do each run..."
                  className="w-full bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[var(--primary)] resize-none"
                />
              </div>

              {/* Cron Builder */}
              <div className="mt-4">
                <label className="text-[10px] font-bold tracking-wider uppercase text-page-muted mb-1 block">Schedule</label>
                <div className="flex flex-wrap gap-2 mb-3">
                  {CRON_PRESETS.map((preset) => (
                    <button
                      key={preset.value}
                      onClick={() => setFormCron(preset.value)}
                      className={cn(
                        "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                        formCron === preset.value
                          ? "bg-[var(--primary)] text-white"
                          : "text-muted-foreground hover:text-foreground hover:bg-white/5 border border-[var(--card-border)]"
                      )}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
                <input
                  value={formCron}
                  onChange={(e) => setFormCron(e.target.value)}
                  placeholder="0 9 * * *"
                  className="w-full bg-transparent border border-[var(--card-border)] rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-[var(--primary)]"
                />
                <p className="mt-1.5 text-xs text-page-muted">
                  {cronToHuman(formCron)}
                </p>
              </div>

              {/* Submit */}
              <div className="mt-5 flex items-center gap-3">
                <button
                  onClick={handleCreate}
                  disabled={creating}
                  className="bg-[var(--primary)] text-white rounded-lg px-4 py-2 text-sm font-medium hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
                >
                  {creating && <Loader2 className="h-4 w-4 animate-spin" />}
                  Create Automation
                </button>
                <button
                  onClick={() => { setShowCreate(false); resetForm() }}
                  className="text-muted-foreground hover:text-foreground hover:bg-white/5 rounded-lg px-3 py-2 text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="mb-8 grid gap-4 md:grid-cols-3">
            {[
              { label: 'Total Automations', value: automations.length, color: 'from-amber-500 to-amber-700' },
              { label: 'Enabled', value: automations.filter((a) => a.enabled).length, color: 'from-emerald-500 to-emerald-700' },
              { label: 'Total Runs', value: automations.reduce((sum, a) => sum + a.run_count, 0), color: 'from-blue-500 to-blue-700' },
            ].map((stat, i) => (
              <div key={i} className="relative overflow-hidden rounded-2xl border p-5 shadow-sm bg-[var(--card-bg)] border-[var(--card-border)]">
                <div className={`absolute top-0 left-0 h-1 w-full bg-gradient-to-r ${stat.color}`} />
                <p className="text-2xl font-black text-page-card-title">{stat.value}</p>
                <p className="text-[10px] font-bold tracking-wider text-page-muted uppercase">{stat.label}</p>
              </div>
            ))}
          </div>

          {/* List Header */}
          <div className="mb-4">
            <h2 className="text-[10px] font-black tracking-widest uppercase text-page-section-label">
              {loading ? 'Loading...' : `Automations (${automations.length})`}
            </h2>
          </div>

          {/* Automation Cards */}
          {automations.length === 0 && !loading ? (
            <div className="text-center py-12">
              <Zap className="mx-auto h-12 w-12 text-page-muted mb-4 opacity-60" />
              <p className="text-page-muted">No automations yet</p>
              <p className="text-sm text-page-muted mt-1">Create a scheduled automation to run agent tasks on a recurring basis.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {automations.map((auto) => (
                <div
                  key={auto.id}
                  className="group relative rounded-2xl border p-5 shadow-sm backdrop-blur-sm transition-all hover:shadow-md bg-[var(--card-bg)] border-[var(--card-border)] hover:border-amber-700/40"
                >
                  <div className="flex items-start gap-4">
                    {/* Icon */}
                    <div className={cn(
                      "rounded-xl p-3 transition-transform group-hover:scale-110",
                      auto.enabled ? "bg-amber-900/20 text-amber-400" : "bg-slate-800/40 text-slate-500"
                    )}>
                      <Zap className="h-6 w-6" />
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <h3 className="font-bold text-page-card-title">{auto.name}</h3>
                        <span className={cn(
                          "rounded px-2 py-0.5 text-[9px] font-bold uppercase",
                          auto.enabled ? "bg-emerald-900/30 text-emerald-400" : "bg-slate-800 text-slate-500"
                        )}>
                          {auto.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                        <span className="rounded px-2 py-0.5 text-[9px] font-bold uppercase bg-blue-900/30 text-blue-400">
                          {auto.agent_mode}
                        </span>
                      </div>

                      {auto.description && (
                        <p className="text-sm text-page-muted mb-2">{auto.description}</p>
                      )}

                      {/* Cron + Schedule */}
                      <div className="flex items-center gap-2 mb-2">
                        <span className="rounded-lg px-2 py-1 text-xs font-mono bg-slate-800/60 text-slate-400">
                          {auto.cron_expression}
                        </span>
                        <span className="text-xs text-page-muted">
                          {cronToHuman(auto.cron_expression)}
                        </span>
                      </div>

                      {/* Meta row */}
                      <div className="flex flex-wrap items-center gap-4 text-[10px] text-slate-400">
                        {auto.next_run_at && (
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            Next: {new Date(auto.next_run_at).toLocaleString()}
                          </span>
                        )}
                        {auto.last_run_at && (
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            Last: {new Date(auto.last_run_at).toLocaleString()}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <Hash className="h-3 w-3" />
                          Runs: {auto.run_count}{auto.max_runs ? ` / ${auto.max_runs}` : ''}
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {/* Run Now */}
                      <button
                        onClick={() => handleRun(auto.id, auto.name)}
                        disabled={running[auto.id]}
                        className={cn(
                          "flex items-center justify-center rounded-lg border p-2.5 transition-colors",
                          "border-blue-900/50 bg-blue-900/20 text-blue-400 hover:bg-blue-900/40 disabled:opacity-50"
                        )}
                        title="Run Now"
                      >
                        {running[auto.id]
                          ? <Loader2 className="h-4 w-4 animate-spin" />
                          : <Play className="h-4 w-4" />
                        }
                      </button>

                      {/* Toggle Enable/Disable */}
                      <button
                        onClick={() => toggleEnabled(auto.id)}
                        className={cn(
                          "flex items-center justify-center rounded-lg border p-2.5 transition-colors",
                          auto.enabled
                            ? "border-emerald-900/50 bg-emerald-900/20 text-emerald-400 hover:bg-emerald-900/40"
                            : "border-slate-700/50 bg-slate-800/20 text-slate-500 hover:bg-slate-700/40"
                        )}
                        title={auto.enabled ? 'Disable' : 'Enable'}
                      >
                        <Power className="h-4 w-4" />
                      </button>

                      {/* Delete */}
                      <button
                        onClick={() => handleDelete(auto.id, auto.name)}
                        className={cn(
                          "flex items-center justify-center rounded-lg border p-2.5 transition-colors",
                          "border-red-900/50 bg-red-900/20 text-red-400 hover:bg-red-900/40"
                        )}
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </PageTransition>
    </DashboardLayout>
  )
}
