"use client"

import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Key, Eye, EyeOff, Save, CheckCircle2, XCircle, Zap, Settings2, Shield, Activity } from 'lucide-react'
import { cn } from '@/shared/lib/utils'

// ─── Types ──────────────────────────────────────────────────────────

interface ApiKeyStatus {
  openai_configured: boolean
  openrouter_configured: boolean
  tavily_configured: boolean
  cohere_configured: boolean
  openai_masked?: string
  openrouter_masked?: string
  tavily_masked?: string
  cohere_masked?: string
}

interface ModelParams {
  temperature: number
  max_tokens?: number | null
  top_p?: number | null
  frequency_penalty?: number | null
  presence_penalty?: number | null
}

interface ApiModelSettings {
  api_keys?: ApiKeyStatus
  temperature: number
  max_tokens?: number | null
  top_p?: number | null
  frequency_penalty?: number | null
  presence_penalty?: number | null
  model_name: string
  enable_input_guardrail?: boolean
  enable_output_guardrail?: boolean
  enable_phoenix_tracing?: boolean
  phoenix_project?: string | null
}

interface ApiModelTabProps {
  settings: ApiModelSettings | null
  onReload: () => void
}

// ─── Available Models ───────────────────────────────────────────────

const MODELS = {
  openai: [
    { id: 'gpt-5.2-2025-12-11', name: 'GPT-5.2', provider: 'OpenAI' },
    { id: 'gpt-5-2025-08-07', name: 'GPT-5', provider: 'OpenAI' },
    { id: 'gpt-5-mini-2025-08-07', name: 'GPT-5 Mini', provider: 'OpenAI' },
    { id: 'gpt-5-nano-2025-08-07', name: 'GPT-5 Nano', provider: 'OpenAI' },
    { id: 'gpt-4.1-2025-04-14', name: 'GPT-4.1', provider: 'OpenAI' },
  ],
  openrouter: [
    { id: 'openai/gpt-oss-120b:free', name: 'GPT OSS 120B (Free)', provider: 'OpenRouter' },
    { id: 'openai/gpt-oss-120b', name: 'GPT OSS 120B', provider: 'OpenRouter' },
  ],
}

// ─── Reusable Components ────────────────────────────────────────────

function ApiKeyInput({
  label,
  value,
  onChange,
  configured,
  masked,
  provider,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  configured: boolean
  masked?: string
  provider: string
}) {
  const [show, setShow] = useState(false)
  const [isEditing, setIsEditing] = useState(false)

  const displayValue = isEditing ? value : (configured && !isEditing ? masked || '••••••••' : value)

  return (
    <div className="rounded-2xl border p-5 bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={cn(
            "h-9 w-9 rounded-xl flex items-center justify-center",
            configured ? "bg-green-500/10" : "bg-slate-500/10"
          )}>
            <Key className={cn("h-4 w-4", configured ? "text-green-500" : "text-slate-400")} />
          </div>
          <div>
            <label className="text-sm font-bold text-[var(--settings-section-title)] block">{label}</label>
            <p className="text-[10px] text-slate-400 font-medium">{provider}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {configured && (
            <span className="text-[10px] font-bold px-2 py-1 rounded-md bg-green-500/10 text-green-500 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" /> Configured
            </span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="flex-1 relative">
          <input
            type={show ? 'text' : 'password'}
            value={displayValue}
            onChange={(e) => {
              setIsEditing(true)
              onChange(e.target.value)
            }}
            onFocus={() => setIsEditing(true)}
            placeholder={`Enter ${provider} API key...`}
            className="w-full bg-[var(--settings-input-bg)] border border-[var(--settings-input-border)] rounded-xl px-4 py-2.5 text-xs font-mono font-bold outline-none focus:border-[var(--settings-input-focus-border)] text-[var(--settings-input-text)] placeholder:text-slate-400/50 transition-colors"
          />
        </div>
        <button
          onClick={() => setShow(!show)}
          className="h-10 w-10 rounded-xl bg-[var(--settings-input-bg)] border border-[var(--settings-input-border)] flex items-center justify-center text-slate-400 hover:text-slate-600 transition-colors"
        >
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </button>
        {configured && isEditing && (
          <button
            onClick={() => {
              onChange('')
              setIsEditing(false)
            }}
            className="h-10 px-4 rounded-xl bg-red-500/10 border border-red-200 text-xs font-bold text-red-500 hover:bg-red-500 hover:text-white transition-colors"
          >
            Clear
          </button>
        )}
      </div>
    </div>
  )
}

function ModelSelector({
  value,
  onChange,
  apiKeys,
}: {
  value: string
  onChange: (v: string) => void
  apiKeys?: ApiKeyStatus
}) {
  // Determine which models are available based on configured API keys
  const availableModels = [
    ...(apiKeys?.openai_configured ? MODELS.openai : []),
    ...(apiKeys?.openrouter_configured ? MODELS.openrouter : []),
  ]

  return (
    <div className="rounded-2xl border p-5 bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
      <div className="flex items-center gap-3 mb-3">
        <div className="h-9 w-9 rounded-xl bg-purple-500/10 flex items-center justify-center">
          <Zap className="h-4 w-4 text-purple-500" />
        </div>
        <div>
          <label className="text-sm font-bold text-[var(--settings-section-title)] block">Model Selection</label>
          <p className="text-[10px] text-slate-400 font-medium">Choose your AI model</p>
        </div>
      </div>

      {availableModels.length === 0 ? (
        <div className="bg-amber-500/5 border border-amber-200 rounded-xl p-4 text-center">
          <p className="text-xs font-bold text-amber-600">Configure an API key to unlock models</p>
        </div>
      ) : (
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full bg-[var(--settings-input-bg)] border border-[var(--settings-input-border)] rounded-xl px-4 py-2.5 text-sm font-bold outline-none focus:border-[var(--settings-input-focus-border)] text-[var(--settings-input-text)] transition-colors cursor-pointer"
        >
          {availableModels.map((model) => (
            <option className="bg-[#0d1117] text-[#e6edf3]" key={model.id} value={model.id}>
              {model.name} ({model.provider})
            </option>
          ))}
        </select>
      )}
    </div>
  )
}

function ParameterSlider({
  label,
  value,
  onChange,
  min,
  max,
  step,
  description,
  unit = '',
}: {
  label: string
  value: number | null | undefined
  onChange: (v: number | null) => void
  min: number
  max: number
  step: number
  description: string
  unit?: string
}) {
  const [enabled, setEnabled] = useState(value !== null && value !== undefined)
  const displayValue = enabled && value !== null && value !== undefined ? value : min

  const handleToggle = (newEnabled: boolean) => {
    setEnabled(newEnabled)
    if (!newEnabled) {
      onChange(null)
    } else {
      onChange(min)
    }
  }

  return (
    <div className="rounded-2xl border p-5 bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
      <div className="flex items-start justify-between mb-4">
        <div>
          <label className="text-sm font-bold text-[var(--settings-section-title)] block">{label}</label>
          <p className="text-[10px] text-slate-400 font-medium mt-0.5">{description}</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-mono font-bold text-[var(--settings-section-title)] min-w-[60px] text-right">
            {enabled ? `${displayValue}${unit}` : 'Default'}
          </span>
          <button
            onClick={() => handleToggle(!enabled)}
            className={cn(
              "h-6 w-11 rounded-full relative transition-colors flex-shrink-0",
              enabled ? "bg-[var(--settings-tab-active-bg)]" : "bg-[var(--settings-toggle-bg)]"
            )}
          >
            <div className={cn(
              "absolute top-1 h-4 w-4 bg-white rounded-full shadow-sm transition-transform",
              enabled ? "translate-x-[22px]" : "translate-x-1"
            )} />
          </button>
        </div>
      </div>

      {enabled && (
        <div className="space-y-3">
          <input
            type="range"
            min={min}
            max={max}
            step={step}
            value={displayValue}
            onChange={(e) => onChange(parseFloat(e.target.value))}
            className="w-full h-2 rounded-full appearance-none cursor-pointer bg-slate-200 dark:bg-slate-700"
            style={{
              background: `linear-gradient(to right, var(--settings-tab-active-bg) 0%, var(--settings-tab-active-bg) ${((displayValue - min) / (max - min)) * 100}%, rgb(226 232 240) ${((displayValue - min) / (max - min)) * 100}%, rgb(226 232 240) 100%)`,
            }}
          />
          <div className="flex justify-between text-[10px] font-bold text-slate-400">
            <span>{min}{unit}</span>
            <span>{max}{unit}</span>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main Component ─────────────────────────────────────────────────

export function ApiModelTab({ settings, onReload }: ApiModelTabProps) {
  const [openaiKey, setOpenaiKey] = useState('')
  const [openrouterKey, setOpenrouterKey] = useState('')
  const [tavilyKey, setTavilyKey] = useState('')
  const [cohereKey, setCohereKey] = useState('')
  const [phoenixTracing, setPhoenixTracing] = useState(settings?.enable_phoenix_tracing ?? false)
  const [phoenixProject, setPhoenixProject] = useState(settings?.phoenix_project || '')
  const [modelName, setModelName] = useState(settings?.model_name || 'gpt-4o-mini')
  const [temperature, setTemperature] = useState(settings?.temperature ?? 0.0)
  const [maxTokens, setMaxTokens] = useState(settings?.max_tokens ?? null)
  const [topP, setTopP] = useState(settings?.top_p ?? null)
  const [frequencyPenalty, setFrequencyPenalty] = useState(settings?.frequency_penalty ?? null)
  const [presencePenalty, setPresencePenalty] = useState(settings?.presence_penalty ?? null)
  const [inputGuardrail, setInputGuardrail] = useState(settings?.enable_input_guardrail ?? false)
  const [outputGuardrail, setOutputGuardrail] = useState(settings?.enable_output_guardrail ?? false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    if (settings) {
      setModelName(settings.model_name)
      setTemperature(settings.temperature ?? 0.0)
      setMaxTokens(settings.max_tokens ?? null)
      setTopP(settings.top_p ?? null)
      setFrequencyPenalty(settings.frequency_penalty ?? null)
      setPresencePenalty(settings.presence_penalty ?? null)
      setInputGuardrail(settings.enable_input_guardrail ?? false)
      setOutputGuardrail(settings.enable_output_guardrail ?? false)
      setPhoenixTracing(settings.enable_phoenix_tracing ?? false)
      setPhoenixProject(settings.phoenix_project || '')
    }
  }, [settings])

  const handleSave = async () => {
    setSaving(true)
    setMessage(null)

    try {
      const { apiUpdateSettings } = await import('@/features/settings/api')

      const payload: any = {
        model_name: modelName,
        temperature,
        max_tokens: maxTokens,
        top_p: topP,
        frequency_penalty: frequencyPenalty,
        presence_penalty: presencePenalty,
        enable_input_guardrail: inputGuardrail,
        enable_output_guardrail: outputGuardrail,
        enable_phoenix_tracing: phoenixTracing,
        phoenix_project: phoenixProject || null,
      }

      // Only include API keys if they were changed (not empty and not masked)
      if (openaiKey && !openaiKey.includes('•')) payload.openai_api_key = openaiKey
      if (openrouterKey && !openrouterKey.includes('•')) payload.openrouter_api_key = openrouterKey
      if (tavilyKey && !tavilyKey.includes('•')) payload.tavily_api_key = tavilyKey
      if (cohereKey && !cohereKey.includes('•')) payload.cohere_api_key = cohereKey

      await apiUpdateSettings(payload)

      setMessage({ type: 'success', text: 'Settings saved successfully!' })
      setTimeout(() => setMessage(null), 3000)

      // Clear API key inputs after successful save
      setOpenaiKey('')
      setOpenrouterKey('')
      setTavilyKey('')
      setCohereKey('')

      // Reload to get updated masked keys
      onReload()
    } catch (err: any) {
      console.error('Failed to save settings:', err)
      setMessage({ type: 'error', text: err.message || 'Failed to save settings' })
      setTimeout(() => setMessage(null), 5000)
    } finally {
      setSaving(false)
    }
  }

  const hasChanges =
    openaiKey.length > 0 ||
    openrouterKey.length > 0 ||
    tavilyKey.length > 0 ||
    cohereKey.length > 0 ||
    modelName !== (settings?.model_name || 'gpt-4o-mini') ||
    temperature !== (settings?.temperature ?? 0.0) ||
    maxTokens !== (settings?.max_tokens ?? null) ||
    topP !== (settings?.top_p ?? null) ||
    frequencyPenalty !== (settings?.frequency_penalty ?? null) ||
    presencePenalty !== (settings?.presence_penalty ?? null) ||
    inputGuardrail !== (settings?.enable_input_guardrail ?? false) ||
    outputGuardrail !== (settings?.enable_output_guardrail ?? false) ||
    phoenixTracing !== (settings?.enable_phoenix_tracing ?? false) ||
    phoenixProject !== (settings?.phoenix_project || '')

  return (
    <div className="space-y-8">
      {/* API Keys Section */}
      <section>
        <div className="flex items-end justify-between border-b pb-3 mb-6 border-[var(--settings-section-border)]">
          <h3 className="text-xl font-black tracking-tight text-[var(--settings-section-title)]">API Keys</h3>
          <span className="text-[10px] font-bold text-slate-400 flex items-center gap-1">
            <Key className="h-3 w-3" /> ENCRYPTED
          </span>
        </div>

        <div className="space-y-4">
          <ApiKeyInput
            label="OpenAI API Key"
            value={openaiKey}
            onChange={setOpenaiKey}
            configured={settings?.api_keys?.openai_configured || false}
            masked={settings?.api_keys?.openai_masked}
            provider="OpenAI"
          />
          <ApiKeyInput
            label="OpenRouter API Key"
            value={openrouterKey}
            onChange={setOpenrouterKey}
            configured={settings?.api_keys?.openrouter_configured || false}
            masked={settings?.api_keys?.openrouter_masked}
            provider="OpenRouter"
          />
          <ApiKeyInput
            label="Tavily API Key"
            value={tavilyKey}
            onChange={setTavilyKey}
            configured={settings?.api_keys?.tavily_configured || false}
            masked={settings?.api_keys?.tavily_masked}
            provider="Tavily (Web Search)"
          />
          <ApiKeyInput
            label="Cohere API Key"
            value={cohereKey}
            onChange={setCohereKey}
            configured={settings?.api_keys?.cohere_configured || false}
            masked={settings?.api_keys?.cohere_masked}
            provider="Cohere (Reranking)"
          />
        </div>
      </section>

      {/* Model Selection */}
      <section>
        <div className="flex items-end justify-between border-b pb-3 mb-6 border-[var(--settings-section-border)]">
          <h3 className="text-xl font-black tracking-tight text-[var(--settings-section-title)]">Model Configuration</h3>
        </div>

        <ModelSelector value={modelName} onChange={setModelName} apiKeys={settings?.api_keys} />
      </section>

      {/* Model Parameters */}
      <section>
        <div className="flex items-end justify-between border-b pb-3 mb-6 border-[var(--settings-section-border)]">
          <h3 className="text-xl font-black tracking-tight text-[var(--settings-section-title)]">Advanced Parameters</h3>
          <span className="text-[10px] font-bold text-slate-400 flex items-center gap-1">
            <Settings2 className="h-3 w-3" /> OPTIONAL
          </span>
        </div>

        <div className="space-y-4">
          <ParameterSlider
            label="Temperature"
            value={temperature}
            onChange={(v) => setTemperature(v ?? 0.0)}
            min={0}
            max={2}
            step={0.1}
            description="Controls randomness: 0 is focused, 2 is creative"
          />
          <ParameterSlider
            label="Max Tokens"
            value={maxTokens}
            onChange={setMaxTokens}
            min={100}
            max={100000}
            step={100}
            description="Maximum length of the response"
          />
          <ParameterSlider
            label="Top P"
            value={topP}
            onChange={setTopP}
            min={0}
            max={1}
            step={0.05}
            description="Nucleus sampling: controls diversity"
          />
          <ParameterSlider
            label="Frequency Penalty"
            value={frequencyPenalty}
            onChange={setFrequencyPenalty}
            min={-2}
            max={2}
            step={0.1}
            description="Reduces repetition of frequent tokens"
          />
          <ParameterSlider
            label="Presence Penalty"
            value={presencePenalty}
            onChange={setPresencePenalty}
            min={-2}
            max={2}
            step={0.1}
            description="Encourages talking about new topics"
          />
        </div>
      </section>

      {/* Guardrails Section */}
      <section>
        <div className="flex items-end justify-between border-b pb-3 mb-6 border-[var(--settings-section-border)]">
          <h3 className="text-xl font-black tracking-tight text-[var(--settings-section-title)]">Guardrails</h3>
          <span className="text-[10px] font-bold text-slate-400 flex items-center gap-1">
            <Shield className="h-3 w-3" /> SAFETY
          </span>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border p-5 flex items-center justify-between bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
            <div className="pr-4">
              <p className="text-sm font-bold text-[var(--settings-section-title)]">Input Guardrail</p>
              <p className="text-xs text-slate-400 mt-1">Check user messages for harmful or unsafe content before processing</p>
            </div>
            <button
              onClick={() => setInputGuardrail(!inputGuardrail)}
              className={cn(
                "h-6 w-11 rounded-full relative cursor-pointer transition-colors flex-shrink-0",
                inputGuardrail ? "bg-[var(--settings-tab-active-bg)]" : "bg-[var(--settings-toggle-bg)]"
              )}
            >
              <div className={cn(
                "absolute top-1 h-4 w-4 bg-white rounded-full shadow-sm transition-transform",
                inputGuardrail ? "translate-x-[22px]" : "translate-x-1"
              )} />
            </button>
          </div>

          <div className="rounded-2xl border p-5 flex items-center justify-between bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
            <div className="pr-4">
              <p className="text-sm font-bold text-[var(--settings-section-title)]">Output Guardrail</p>
              <p className="text-xs text-slate-400 mt-1">Check AI responses for harmful or unsafe content before displaying</p>
            </div>
            <button
              onClick={() => setOutputGuardrail(!outputGuardrail)}
              className={cn(
                "h-6 w-11 rounded-full relative cursor-pointer transition-colors flex-shrink-0",
                outputGuardrail ? "bg-[var(--settings-tab-active-bg)]" : "bg-[var(--settings-toggle-bg)]"
              )}
            >
              <div className={cn(
                "absolute top-1 h-4 w-4 bg-white rounded-full shadow-sm transition-transform",
                outputGuardrail ? "translate-x-[22px]" : "translate-x-1"
              )} />
            </button>
          </div>
        </div>
      </section>

      {/* Phoenix Tracing Section */}
      <section>
        <div className="flex items-end justify-between border-b pb-3 mb-6 border-[var(--settings-section-border)]">
          <h3 className="text-xl font-black tracking-tight text-[var(--settings-section-title)]">Phoenix Tracing</h3>
          <span className="text-[10px] font-bold text-slate-400 flex items-center gap-1">
            <Activity className="h-3 w-3" /> OBSERVABILITY
          </span>
        </div>

        <div className="space-y-4">
          <div className="rounded-2xl border p-5 flex items-center justify-between bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
            <div className="pr-4">
              <p className="text-sm font-bold text-[var(--settings-section-title)]">Enable Tracing</p>
              <p className="text-xs text-slate-400 mt-1">Send workflow traces to Arize Phoenix for debugging and observability</p>
            </div>
            <button
              onClick={() => setPhoenixTracing(!phoenixTracing)}
              className={cn(
                "h-6 w-11 rounded-full relative cursor-pointer transition-colors flex-shrink-0",
                phoenixTracing ? "bg-[var(--settings-tab-active-bg)]" : "bg-[var(--settings-toggle-bg)]"
              )}
            >
              <div className={cn(
                "absolute top-1 h-4 w-4 bg-white rounded-full shadow-sm transition-transform",
                phoenixTracing ? "translate-x-[22px]" : "translate-x-1"
              )} />
            </button>
          </div>

          <div className="rounded-2xl border p-5 bg-[var(--settings-card-bg)] border-[var(--settings-card-border)]">
            <div className="flex items-center gap-3 mb-3">
              <div className="h-9 w-9 rounded-xl bg-blue-500/10 flex items-center justify-center">
                <Activity className="h-4 w-4 text-blue-500" />
              </div>
              <div>
                <label className="text-sm font-bold text-[var(--settings-section-title)] block">Project Name</label>
                <p className="text-[10px] text-slate-400 font-medium">Phoenix project to send traces to</p>
              </div>
            </div>
            <input
              type="text"
              value={phoenixProject}
              onChange={(e) => setPhoenixProject(e.target.value)}
              placeholder="project-rio"
              className="w-full bg-[var(--settings-input-bg)] border border-[var(--settings-input-border)] rounded-xl px-4 py-2.5 text-xs font-mono font-bold outline-none focus:border-[var(--settings-input-focus-border)] text-[var(--settings-input-text)] placeholder:text-slate-400/50 transition-colors"
            />
          </div>
        </div>
      </section>

      {/* Save Button */}
      <div className="flex items-center gap-4 pt-4">
        <button
          onClick={handleSave}
          disabled={!hasChanges || saving}
          className="flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-bold text-white transition-all shadow-lg bg-[var(--settings-tab-active-bg)] hover:opacity-90 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Save className="h-4 w-4" /> {saving ? 'Saving...' : 'Save Changes'}
        </button>

        <AnimatePresence>
          {message && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={cn(
                "text-xs font-bold px-4 py-2 rounded-xl",
                message.type === 'success' ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"
              )}
            >
              {message.text}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
