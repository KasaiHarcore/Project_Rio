"use client"

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  User, Key, Bell, Database, Shield, Trash2,
  Eye, EyeOff, RotateCcw, Download, Archive,
  AlertTriangle, LogOut, Server,
  MessageSquare, Bot, Sparkles, Save, Lock, FileText
} from 'lucide-react'
import { cn } from '@/lib/utils'

// ─── Types ──────────────────────────────────────────────────────────
interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

type TabId = 'profile' | 'keys' | 'prompt' | 'notifications' | 'data' | 'security'

interface ApiKeyField {
  id: string; label: string; envHint: string; placeholder: string; value: string
}

interface DbField {
  id: string; label: string; placeholder: string; value: string; type?: string
}

interface ToggleSetting {
  id: string; label: string; description: string; enabled: boolean
}

// ─── Reusable Primitives ────────────────────────────────────────────

function SettingsInput({ label, type = 'text', placeholder, value, onChange, rightElement, className }: {
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

function SettingsTextarea({ label, placeholder, value, onChange, rows = 6, hint }: {
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

function Toggle({ enabled, onChange }: { enabled: boolean; onChange: (v: boolean) => void }) {
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

function ToggleRow({ label, description, enabled, onChange }: {
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

function DangerButton({ icon: Icon, label, description, onClick, confirmLabel }: {
  icon: React.ElementType; label: string; description: string; onClick: () => void; confirmLabel?: string
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

function SectionHeader({ title, badge }: { title: string; badge?: React.ReactNode }) {
  return (
    <div className="flex items-end justify-between border-b pb-3 mb-6 border-[var(--settings-section-border)]">
      <h3 className="text-xl font-black tracking-tight text-[var(--settings-section-title)]">{title}</h3>
      {badge}
    </div>
  )
}

function StatusBadge({ connected, label }: { connected: boolean; label?: string }) {
  return (
    <span className={cn("text-[10px] font-bold flex items-center gap-1.5", connected ? "text-green-500" : "text-slate-400")}>
      <span className={cn("w-2 h-2 rounded-full", connected ? "bg-green-500 animate-pulse" : "bg-slate-300")} />
      {label || (connected ? 'CONNECTED' : 'NOT SET')}
    </span>
  )
}

// ─── 1. Profile Tab ─────────────────────────────────────────────────

function ProfileTab() {
  const [name, setName] = useState('Sensei')
  const [email, setEmail] = useState('sensei@schale.io')
  const [bio, setBio] = useState('')
  const [studyGoal, setStudyGoal] = useState('')

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <section>
        <SectionHeader title="Identity" />
        <div className="flex items-start gap-6 mb-8">
          <div className="relative group">
            <div className="h-24 w-24 rounded-full border-4 p-1 border-[var(--settings-avatar-border)] overflow-hidden">
              <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Sensei" alt="Avatar" className="h-full w-full rounded-full object-cover" />
            </div>
            <button className="absolute inset-0 flex items-center justify-center rounded-full bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity">
              <span className="text-[10px] font-bold text-white">Change</span>
            </button>
          </div>
          <div className="flex-1 space-y-1">
            <h2 className="text-2xl font-black text-[var(--settings-name)]">{name || 'Sensei'}</h2>
            <p className="text-sm font-medium text-slate-400">Clearance Level 5 // Administrator</p>
            <p className="text-xs text-slate-400 mt-2">Member since Jan 2026</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SettingsInput label="Display Name" placeholder="Sensei" value={name} onChange={setName} />
          <SettingsInput label="Email Address" type="email" placeholder="sensei@schale.io" value={email} onChange={setEmail} />
        </div>
      </section>

      <section>
        <SectionHeader title="Personal File" />
        <div className="space-y-4">
          <SettingsTextarea label="Bio / About" placeholder="Tell us about yourself..." value={bio} onChange={setBio} rows={3} hint="Optional" />
          <SettingsTextarea label="Study Goals" placeholder="e.g., Master Python by Q3, Pass AWS certification, Build a full-stack app..." value={studyGoal} onChange={setStudyGoal} rows={3} hint="Helps the AI tailor guidance" />
        </div>
      </section>

      <div className="pt-2">
        <button className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white transition-all shadow-lg bg-[var(--settings-tab-active-bg)] hover:opacity-90 active:scale-[0.98]">
          <Save className="h-4 w-4" /> Save Profile
        </button>
      </div>
    </div>
  )
}

// ─── 2. Neural Keys Tab ─────────────────────────────────────────────

function NeuralKeysTab() {
  const [apiKeys, setApiKeys] = useState<ApiKeyField[]>([
    { id: 'openai', label: 'OpenAI API Key', envHint: 'OPENAI_API_KEY', placeholder: 'sk-...', value: '' },
    { id: 'openrouter', label: 'OpenRouter API Key', envHint: 'OPENROUTER_API_KEY', placeholder: 'sk-or-v1-...', value: '' },
    { id: 'tavily', label: 'Tavily Search Key', envHint: 'TAVILY_API_KEY', placeholder: 'tvly-...', value: '' },
    { id: 'cohere', label: 'Cohere Reranker Key', envHint: 'COHERE_API_KEY', placeholder: 'Enter key...', value: '' },
  ])
  const [dbConfig, setDbConfig] = useState<DbField[]>([
    { id: 'pg_host', label: 'PostgreSQL Host', placeholder: 'localhost', value: 'localhost' },
    { id: 'pg_port', label: 'PostgreSQL Port', placeholder: '5432', value: '5432' },
    { id: 'pg_db', label: 'Database Name', placeholder: 'rag_db', value: 'rag_db' },
    { id: 'pg_user', label: 'Database User', placeholder: 'postgres', value: 'postgres' },
    { id: 'pg_pass', label: 'Database Password', placeholder: '••••••', value: '', type: 'password' },
  ])
  const [redisConfig, setRedisConfig] = useState<DbField[]>([
    { id: 'redis_host', label: 'Redis Host', placeholder: 'localhost', value: 'localhost' },
    { id: 'redis_port', label: 'Redis Port', placeholder: '6379', value: '6379' },
    { id: 'redis_pass', label: 'Redis Password', placeholder: 'Optional', value: '', type: 'password' },
  ])
  const [qdrantConfig, setQdrantConfig] = useState<DbField[]>([
    { id: 'qdrant_path', label: 'Qdrant Path / URL', placeholder: './storage/qdrant', value: './storage/qdrant' },
    { id: 'qdrant_collection', label: 'Collection Name', placeholder: 'rag-fpt', value: 'rag-fpt' },
    { id: 'embedding_model', label: 'Embedding Model', placeholder: 'sentence-transformers/all-MiniLM-L6-v2', value: 'sentence-transformers/all-MiniLM-L6-v2' },
  ])
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({})
  const togglePassword = (id: string) => setShowPasswords(prev => ({ ...prev, [id]: !prev[id] }))
  const updateApiKey = (id: string, value: string) => setApiKeys(prev => prev.map(k => k.id === id ? { ...k, value } : k))
  const updateDbField = (setter: React.Dispatch<React.SetStateAction<DbField[]>>, id: string, value: string) => setter(prev => prev.map(f => f.id === id ? { ...f, value } : f))

  return (
    <div className="space-y-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* API Keys */}
      <section>
        <SectionHeader title="Neural Gateway Keys" badge={<span className="font-mono text-[10px] font-bold text-slate-400 flex items-center gap-1"><Lock className="w-3 h-3" /> ENCRYPTED</span>} />
        <div className="grid grid-cols-1 gap-4">
          {apiKeys.map((key) => (
            <div key={key.id} className="rounded-2xl border p-4 transition-colors bg-[var(--settings-input-bg)] border-[var(--settings-input-border)] focus-within:border-[var(--settings-input-focus-border)] focus-within:bg-[var(--settings-input-focus-bg)]">
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-[9px] font-black tracking-widest uppercase text-[var(--settings-input-label)]">{key.label}</label>
                <div className="flex items-center gap-3">
                  <span className="text-[9px] font-mono text-slate-400">{key.envHint}</span>
                  <StatusBadge connected={key.value.length > 5} />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input type={showPasswords[key.id] ? 'text' : 'password'} placeholder={key.placeholder} value={key.value} onChange={(e) => updateApiKey(key.id, e.target.value)}
                  className="w-full bg-transparent font-mono text-sm font-bold outline-none text-[var(--settings-input-text)] placeholder:text-slate-400/50" />
                <button onClick={() => togglePassword(key.id)} className="text-slate-400 hover:text-slate-600 transition-colors p-1">
                  {showPasswords[key.id] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* PostgreSQL */}
      <section>
        <SectionHeader title="PostgreSQL" badge={<StatusBadge connected={true} label="ENCRYPTED_SSL" />} />
        <div className="grid grid-cols-2 gap-4">
          {dbConfig.map((field) => (
            <SettingsInput key={field.id} label={field.label}
              type={field.type === 'password' ? (showPasswords[field.id] ? 'text' : 'password') : 'text'}
              placeholder={field.placeholder} value={field.value}
              onChange={(v) => updateDbField(setDbConfig, field.id, v)}
              rightElement={field.type === 'password' ? (
                <button onClick={() => togglePassword(field.id)} className="text-slate-400 hover:text-slate-600 transition-colors p-1">
                  {showPasswords[field.id] ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                </button>
              ) : undefined}
              className={field.id === 'pg_pass' ? 'col-span-2' : ''} />
          ))}
        </div>
      </section>

      {/* Redis */}
      <section>
        <SectionHeader title="Redis Cache" badge={<StatusBadge connected={true} />} />
        <div className="grid grid-cols-3 gap-4">
          {redisConfig.map((field) => (
            <SettingsInput key={field.id} label={field.label}
              type={field.type === 'password' ? (showPasswords[field.id] ? 'text' : 'password') : 'text'}
              placeholder={field.placeholder} value={field.value}
              onChange={(v) => updateDbField(setRedisConfig, field.id, v)}
              rightElement={field.type === 'password' ? (
                <button onClick={() => togglePassword(field.id)} className="text-slate-400 hover:text-slate-600 transition-colors p-1">
                  {showPasswords[field.id] ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                </button>
              ) : undefined} />
          ))}
        </div>
      </section>

      {/* Qdrant */}
      <section>
        <SectionHeader title="Qdrant Vector Store" badge={<StatusBadge connected={true} />} />
        <div className="grid grid-cols-1 gap-4">
          {qdrantConfig.map((field) => (
            <SettingsInput key={field.id} label={field.label} placeholder={field.placeholder} value={field.value} onChange={(v) => updateDbField(setQdrantConfig, field.id, v)} />
          ))}
        </div>
      </section>

      <div className="pt-2">
        <button className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white transition-all shadow-lg bg-[var(--settings-tab-active-bg)] hover:opacity-90 active:scale-[0.98]">
          <Save className="h-4 w-4" /> Save Configuration
        </button>
      </div>
    </div>
  )
}

// ─── 3. System Prompt / Agent Config Tab ────────────────────────────

function SystemPromptTab() {
  const DEFAULT_PROMPT = `You are a helpful AI study assistant. You help users learn programming, manage study tasks, and answer technical questions. Be concise, accurate, and encouraging. When you don't know something, say so honestly.`
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_PROMPT)
  const [modelName, setModelName] = useState('gpt-4o-mini')
  const [agentMode, setAgentMode] = useState<string>('chat')
  const [enablePlanner, setEnablePlanner] = useState(true)
  const [enableReflection, setEnableReflection] = useState(true)
  const [maxIterations, setMaxIterations] = useState('10')
  const [topK, setTopK] = useState('5')

  const modes = [
    { id: 'chat', label: 'Chat', description: 'General conversation', icon: MessageSquare },
    { id: 'rag', label: 'RAG', description: 'Document retrieval', icon: Database },
    { id: 'web', label: 'Web', description: 'Internet search', icon: Sparkles },
    { id: 'sql', label: 'SQL', description: 'Database queries', icon: Server },
  ]

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <section>
        <SectionHeader title="System Prompt" />
        <SettingsTextarea label="Bot Instructions" placeholder="Define how the AI assistant should behave..." value={systemPrompt} onChange={setSystemPrompt} rows={8} hint={`${systemPrompt.length} chars`} />
        <button onClick={() => setSystemPrompt(DEFAULT_PROMPT)} className="flex items-center gap-2 mt-3 text-xs font-bold text-slate-400 hover:text-[var(--settings-input-label)] transition-colors">
          <RotateCcw className="h-3.5 w-3.5" /> Reset to Default
        </button>
      </section>

      <section>
        <SectionHeader title="Agent Mode" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {modes.map((mode) => (
            <button key={mode.id} onClick={() => setAgentMode(mode.id)}
              className={cn("rounded-2xl border p-4 text-left transition-all",
                agentMode === mode.id
                  ? "bg-[var(--settings-tab-active-bg)] text-white border-transparent shadow-lg"
                  : "bg-[var(--settings-card-bg)] border-[var(--settings-card-border)] text-[var(--settings-section-title)] hover:border-[var(--settings-input-focus-border)]"
              )}>
              <mode.icon className={cn("h-5 w-5 mb-2", agentMode === mode.id ? "text-white/80" : "text-slate-400")} />
              <p className="text-sm font-bold">{mode.label}</p>
              <p className={cn("text-[10px] mt-0.5", agentMode === mode.id ? "text-white/60" : "text-slate-400")}>{mode.description}</p>
            </button>
          ))}
        </div>
      </section>

      <section>
        <SectionHeader title="Model Configuration" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <SettingsInput label="Model Name" placeholder="gpt-4o-mini" value={modelName} onChange={setModelName} className="md:col-span-1" />
          <SettingsInput label="Max Iterations" placeholder="10" value={maxIterations} onChange={setMaxIterations} />
          <SettingsInput label="Top-K Retrieval" placeholder="5" value={topK} onChange={setTopK} />
        </div>
        <div className="space-y-3">
          <ToggleRow label="Enable Planner" description="Allow the agent to plan multi-step tasks before execution" enabled={enablePlanner} onChange={setEnablePlanner} />
          <ToggleRow label="Enable Reflection" description="Agent verifies and refines its own answers" enabled={enableReflection} onChange={setEnableReflection} />
        </div>
      </section>

      <div className="pt-2">
        <button className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white transition-all shadow-lg bg-[var(--settings-tab-active-bg)] hover:opacity-90 active:scale-[0.98]">
          <Save className="h-4 w-4" /> Save Agent Config
        </button>
      </div>
    </div>
  )
}

// ─── 4. Notifications Tab ───────────────────────────────────────────

function NotificationsTab() {
  const [notifications, setNotifications] = useState<ToggleSetting[]>([
    { id: 'mission_remind', label: 'Mission Reminders', description: 'Get notified when a mission deadline is approaching', enabled: true },
    { id: 'chat_alerts', label: 'Chat Response Alerts', description: 'Notify when AI finishes a long-running response', enabled: true },
    { id: 'system_updates', label: 'System Updates', description: 'Announcements about new features and maintenance', enabled: false },
    { id: 'weekly_summary', label: 'Weekly Progress Summary', description: 'Receive a weekly study progress report', enabled: true },
    { id: 'error_alerts', label: 'Error Notifications', description: 'Alert when system encounters errors or connection issues', enabled: true },
  ])
  const [soundEnabled, setSoundEnabled] = useState(false)
  const [emailNotifs, setEmailNotifs] = useState(false)
  const toggleNotification = (id: string) => setNotifications(prev => prev.map(n => n.id === id ? { ...n, enabled: !n.enabled } : n))

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <section>
        <SectionHeader title="Notification Preferences" />
        <div className="space-y-3">
          {notifications.map((n) => (
            <ToggleRow key={n.id} label={n.label} description={n.description} enabled={n.enabled} onChange={() => toggleNotification(n.id)} />
          ))}
        </div>
      </section>
      <section>
        <SectionHeader title="Delivery" />
        <div className="space-y-3">
          <ToggleRow label="Sound Effects" description="Play sound when notifications arrive" enabled={soundEnabled} onChange={setSoundEnabled} />
          <ToggleRow label="Email Notifications" description="Send important alerts to your email address" enabled={emailNotifs} onChange={setEmailNotifs} />
        </div>
      </section>
      <div className="pt-2">
        <button className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white transition-all shadow-lg bg-[var(--settings-tab-active-bg)] hover:opacity-90 active:scale-[0.98]">
          <Save className="h-4 w-4" /> Save Preferences
        </button>
      </div>
    </div>
  )
}

// ─── 5. Data Management Tab ─────────────────────────────────────────

function DataManagementTab() {
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

// ─── 6. Security Tab ────────────────────────────────────────────────

function SecurityTab() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [mfaEnabled, setMfaEnabled] = useState(false)
  const [showPasswords, setShowPasswords] = useState<Record<string, boolean>>({})
  const togglePassword = (id: string) => setShowPasswords(prev => ({ ...prev, [id]: !prev[id] }))
  const passwordMismatch = confirmPassword.length > 0 && newPassword !== confirmPassword

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Change Password */}
      <section>
        <SectionHeader title="Change Password" />
        <div className="space-y-4">
          <SettingsInput label="Current Password" type={showPasswords['current'] ? 'text' : 'password'} placeholder="Enter current password" value={currentPassword} onChange={setCurrentPassword}
            rightElement={<button onClick={() => togglePassword('current')} className="text-slate-400 hover:text-slate-600 transition-colors p-1">{showPasswords['current'] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <SettingsInput label="New Password" type={showPasswords['new'] ? 'text' : 'password'} placeholder="Enter new password" value={newPassword} onChange={setNewPassword}
              rightElement={<button onClick={() => togglePassword('new')} className="text-slate-400 hover:text-slate-600 transition-colors p-1">{showPasswords['new'] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>} />
            <div>
              <SettingsInput label="Confirm New Password" type={showPasswords['confirm'] ? 'text' : 'password'} placeholder="Confirm new password" value={confirmPassword} onChange={setConfirmPassword}
                rightElement={<button onClick={() => togglePassword('confirm')} className="text-slate-400 hover:text-slate-600 transition-colors p-1">{showPasswords['confirm'] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button>} />
              {passwordMismatch && <p className="text-[10px] font-bold text-red-500 mt-2 ml-1">Passwords do not match</p>}
            </div>
          </div>
          <button disabled={!currentPassword || !newPassword || passwordMismatch}
            className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white transition-all shadow-lg bg-[var(--settings-tab-active-bg)] hover:opacity-90 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed">
            <Lock className="h-4 w-4" /> Update Password
          </button>
        </div>
      </section>

      {/* MFA & Sessions */}
      <section>
        <SectionHeader title="Authentication" />
        <div className="space-y-3">
          <ToggleRow label="Multi-Factor Authentication" description="Add an extra layer of security to your account" enabled={mfaEnabled} onChange={setMfaEnabled} />
          <div className="rounded-2xl border p-5 bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm font-bold text-[var(--settings-section-title)]">Active Sessions</p>
                <p className="text-xs text-slate-400 mt-0.5">Manage devices where you&apos;re logged in</p>
              </div>
            </div>
            <div className="space-y-3">
              {[
                { device: 'Current Browser', location: 'This device', active: true },
                { device: 'Mobile App', location: 'Last active 2h ago', active: false },
              ].map((session, i) => (
                <div key={i} className="flex items-center justify-between rounded-xl border p-3 border-[var(--settings-input-border)] bg-[var(--settings-input-bg)]">
                  <div className="flex items-center gap-3">
                    <div className={cn("w-2 h-2 rounded-full", session.active ? "bg-green-500" : "bg-slate-300")} />
                    <div>
                      <p className="text-xs font-bold text-[var(--settings-section-title)]">{session.device}</p>
                      <p className="text-[10px] text-slate-400">{session.location}</p>
                    </div>
                  </div>
                  {!session.active && <button className="text-[10px] font-bold text-red-400 hover:text-red-500 transition-colors">Revoke</button>}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Logout + Delete */}
      <section>
        <SectionHeader title="Account Actions" badge={<span className="text-[10px] font-bold text-red-400 flex items-center gap-1"><AlertTriangle className="h-3 w-3" /> CRITICAL</span>} />
        <div className="space-y-3">
          <div className="rounded-2xl border p-5 flex items-center justify-between bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
            <div className="flex items-center gap-4">
              <div className="h-10 w-10 rounded-xl bg-amber-500/10 flex items-center justify-center flex-shrink-0">
                <LogOut className="h-5 w-5 text-amber-500" />
              </div>
              <div>
                <p className="text-sm font-bold text-[var(--settings-section-title)]">Log Out</p>
                <p className="text-xs text-slate-400 mt-0.5">Sign out of this session</p>
              </div>
            </div>
            <button className="px-4 py-2 rounded-xl text-xs font-bold border transition-all text-amber-600 border-amber-200 hover:bg-amber-500 hover:text-white hover:border-amber-500">
              Log Out
            </button>
          </div>
          <DangerButton icon={Trash2} label="Delete Account" description="Permanently delete your account and all associated data. This cannot be undone." onClick={() => {}} confirmLabel="I understand, delete my account" />
        </div>
      </section>
    </div>
  )
}

// ─── Tab Registry ───────────────────────────────────────────────────
const TABS: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'keys', label: 'Neural Keys', icon: Key },
  { id: 'prompt', label: 'Agent Config', icon: Bot },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'data', label: 'Data', icon: Database },
  { id: 'security', label: 'Security', icon: Shield },
]

const TAB_CONTENT: Record<TabId, React.FC> = {
  profile: ProfileTab,
  keys: NeuralKeysTab,
  prompt: SystemPromptTab,
  notifications: NotificationsTab,
  data: DataManagementTab,
  security: SecurityTab,
}

// ─── Main Modal ─────────────────────────────────────────────────────
export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<TabId>('profile')
  const ActiveContent = TAB_CONTENT[activeTab]

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 font-sans">
          {/* Backdrop */}
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose}
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-md" />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative flex flex-col md:flex-row h-[min(750px,90vh)] w-full max-w-5xl overflow-hidden rounded-[2.5rem] border shadow-2xl z-10 bg-[var(--settings-bg)] border-[var(--settings-border)]"
            style={{ boxShadow: `0 25px 50px -12px var(--settings-shadow)` }}
          >
            {/* Sidebar */}
            <aside className="w-full md:w-56 border-b md:border-b-0 md:border-r p-4 md:p-6 flex flex-col bg-[var(--settings-sidebar-bg)] border-[var(--settings-sidebar-border)]">
              <div className="mb-4 md:mb-8">
                <h2 className="text-[10px] font-black tracking-[0.2em] uppercase text-[var(--settings-heading)]">System Settings</h2>
              </div>
              <nav className="flex md:flex-col gap-1 md:gap-0 md:space-y-1 flex-1 overflow-x-auto md:overflow-x-visible pb-2 md:pb-0">
                {TABS.map((tab) => (
                  <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                    aria-label={tab.label}
                    className={cn("flex items-center rounded-xl p-2 md:p-3 text-xs md:text-sm font-bold transition-all whitespace-nowrap md:w-full",
                      activeTab === tab.id
                        ? 'bg-[var(--settings-tab-active-bg)] text-white shadow-lg'
                        : 'text-[var(--settings-tab-inactive-text)] hover:bg-[var(--settings-tab-hover-bg)] hover:text-[var(--settings-tab-hover-text)]'
                    )}
                    style={activeTab === tab.id ? { boxShadow: `0 10px 15px -3px var(--settings-tab-active-shadow)` } : undefined}>
                    <tab.icon className="mr-2 md:mr-3 h-4 w-4" strokeWidth={2.5} />
                    <span className="hidden md:inline">{tab.label}</span>
                  </button>
                ))}
              </nav>
              <button onClick={onClose} aria-label="Close settings" className="hidden md:block text-[10px] font-black tracking-[0.2em] text-slate-500 uppercase transition-colors hover:text-red-400 text-left">
                Close Terminal
              </button>
            </aside>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-10 custom-scrollbar">
              <ActiveContent />
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}


