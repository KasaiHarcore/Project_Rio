"use client"

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Sparkles, Zap, Brain, Check } from 'lucide-react'
import { cn } from '@/shared/lib/utils'

interface ModelOption {
  id: string
  name: string
  description: string
  icon: React.ComponentType<Record<string, unknown>>
  badge?: string
  recommended?: boolean
}

const AVAILABLE_MODELS: ModelOption[] = [
  {
    id: 'gpt-4o-mini',
    name: 'GPT-4o Mini',
    description: 'Fast and cost-effective for most tasks. Best for everyday queries.',
    icon: Zap,
    badge: 'FASTEST',
    recommended: true,
  },
  {
    id: 'gpt-4o',
    name: 'GPT-4o',
    description: 'Most capable model with advanced reasoning. Best for complex problems.',
    icon: Brain,
    badge: 'MOST CAPABLE',
  },
  {
    id: 'gpt-4-turbo',
    name: 'GPT-4 Turbo',
    description: 'Balanced performance and speed for advanced tasks.',
    icon: Sparkles,
  },
  {
    id: 'gpt-3.5-turbo',
    name: 'GPT-3.5 Turbo',
    description: 'Older model, faster but less capable than GPT-4 variants.',
    icon: Zap,
  },
]

interface ModelPickerModalProps {
  isOpen: boolean
  onClose: () => void
  currentModel: string
  onSelectModel: (modelId: string) => void
}

export function ModelPickerModal({
  isOpen,
  onClose,
  currentModel,
  onSelectModel,
}: ModelPickerModalProps) {
  const [selectedModel, setSelectedModel] = useState(currentModel)

  const handleConfirm = () => {
    onSelectModel(selectedModel)
    onClose()
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4 font-sans">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className="relative w-full max-w-2xl overflow-hidden rounded-3xl border shadow-2xl z-10 bg-[var(--settings-bg)] border-[var(--settings-border)]"
            style={{ boxShadow: `0 25px 50px -12px var(--settings-shadow)` }}
          >
            {/* Header */}
            <div className="border-b p-6 bg-[var(--settings-sidebar-bg)] border-[var(--settings-sidebar-border)]">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-2xl font-black tracking-tight text-[var(--settings-name)]">
                    Choose AI Model
                  </h2>
                  <p className="text-sm text-slate-400 mt-1">
                    Select the model that best fits your needs
                  </p>
                </div>
                <button
                  onClick={onClose}
                  className="h-10 w-10 rounded-full flex items-center justify-center transition-colors hover:bg-slate-200/10"
                  aria-label="Close"
                >
                  <X className="h-5 w-5 text-slate-400" />
                </button>
              </div>
            </div>

            {/* Model List */}
            <div className="p-6 space-y-3 max-h-[60vh] overflow-y-auto custom-scrollbar">
              {AVAILABLE_MODELS.map((model) => {
                const Icon = model.icon
                const isSelected = selectedModel === model.id
                const isCurrent = currentModel === model.id

                return (
                  <button
                    key={model.id}
                    onClick={() => setSelectedModel(model.id)}
                    className={cn(
                      "w-full rounded-2xl border p-5 text-left transition-all relative overflow-hidden",
                      isSelected
                        ? "border-[var(--settings-tab-active-bg)] bg-[var(--settings-tab-active-bg)]/5 shadow-lg"
                        : "border-[var(--settings-card-border)] bg-[var(--settings-card-bg)] hover:border-[var(--settings-input-focus-border)]"
                    )}
                  >
                    {/* Selection indicator */}
                    {isSelected && (
                      <motion.div
                        layoutId="selected-model"
                        className="absolute top-4 right-4 h-6 w-6 rounded-full bg-[var(--settings-tab-active-bg)] flex items-center justify-center"
                        transition={{ type: "spring", bounce: 0.2, duration: 0.6 }}
                      >
                        <Check className="h-4 w-4 text-white" strokeWidth={3} />
                      </motion.div>
                    )}

                    <div className="flex items-start gap-4 pr-10">
                      {/* Icon */}
                      <div
                        className={cn(
                          "h-12 w-12 rounded-xl flex items-center justify-center flex-shrink-0 transition-colors",
                          isSelected
                            ? "bg-[var(--settings-tab-active-bg)]"
                            : "bg-slate-500/10"
                        )}
                      >
                        <Icon
                          className={cn(
                            "h-6 w-6 transition-colors",
                            isSelected ? "text-white" : "text-slate-400"
                          )}
                        />
                      </div>

                      {/* Content */}
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h3 className="text-base font-bold text-[var(--settings-section-title)]">
                            {model.name}
                          </h3>
                          {model.badge && (
                            <span className="text-[9px] font-black tracking-wider px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-500">
                              {model.badge}
                            </span>
                          )}
                          {model.recommended && (
                            <span className="text-[9px] font-black tracking-wider px-2 py-0.5 rounded-full bg-green-500/10 text-green-500">
                              RECOMMENDED
                            </span>
                          )}
                          {isCurrent && (
                            <span className="text-[9px] font-black tracking-wider px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-500">
                              CURRENT
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-400">{model.description}</p>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>

            {/* Footer */}
            <div className="border-t p-6 bg-[var(--settings-sidebar-bg)] border-[var(--settings-sidebar-border)]">
              <div className="flex items-center justify-between gap-4">
                <p className="text-xs text-slate-400">
                  Your model choice affects response quality and speed
                </p>
                <div className="flex gap-3">
                  <button
                    onClick={onClose}
                    className="px-5 py-2.5 rounded-xl text-sm font-bold transition-all border border-[var(--settings-card-border)] text-[var(--settings-section-title)] hover:bg-slate-200/5"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleConfirm}
                    disabled={selectedModel === currentModel}
                    className="px-5 py-2.5 rounded-xl text-sm font-bold text-white transition-all shadow-lg bg-[var(--settings-tab-active-bg)] hover:opacity-90 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Confirm Selection
                  </button>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
