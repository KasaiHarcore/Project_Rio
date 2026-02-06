"use client"

import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { User, Key, Sliders, X, Check, Shield } from 'lucide-react'
import { useTheme } from '@/components/providers/theme-provider'
import { cn } from '@/lib/utils'

interface SettingsModalProps {
  isOpen: boolean
  onClose: () => void
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState('account')
  const { theme } = useTheme()
  const isNight = theme === 'dark'

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 font-sans text-slate-700">
          {/* Backdrop */}
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-slate-900/40 backdrop-blur-md"
          />

          {/* Modal Content */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            className={cn(
                "relative flex h-[700px] w-full max-w-5xl overflow-hidden rounded-[2.5rem] border shadow-2xl z-10",
                isNight ? "bg-[#0d1117] border-rose-900/40 shadow-rose-900/20" : "bg-white border-blue-100"
            )}
          >
            {/* Sidebar */}
            <aside className={cn(
                "w-64 border-r p-8 flex flex-col",
                isNight ? "border-rose-900/30 bg-[#010409]/50" : "border-blue-50 bg-blue-50/30"
            )}>
              <div className="mb-10">
                <h2 className={cn("text-xs font-black tracking-[0.2em] uppercase", isNight ? "text-rose-500" : "text-blue-500")}>System Settings</h2>
              </div>

              <nav className="space-y-2 flex-1">
                {[
                  { id: 'account', label: 'Account', icon: User },
                  { id: 'keys', label: 'Neural Keys', icon: Key },
                  { id: 'personalize', label: 'Personalize', icon: Sliders },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={cn(
                        "flex w-full items-center rounded-xl p-3 text-sm font-bold transition-all",
                         activeTab === tab.id 
                            ? (isNight ? 'bg-rose-600 text-white shadow-lg shadow-rose-900/20' : 'bg-blue-500 text-white shadow-lg shadow-blue-100')
                            : (isNight ? 'text-slate-500 hover:bg-rose-900/10 hover:text-rose-400' : 'text-slate-500 hover:bg-white hover:text-blue-500')
                    )}
                  >
                    <tab.icon className="mr-3 h-4 w-4" strokeWidth={2.5} />
                    {tab.label}
                  </button>
                ))}
              </nav>

              <button 
                onClick={onClose}
                className="text-[10px] font-black tracking-[0.2em] text-slate-300 uppercase transition-colors hover:text-red-400 text-left"
              >
                Close Terminal
              </button>
            </aside>

            {/* Main Content Area */}
            <div className="flex-1 overflow-y-auto p-12">
                
              {activeTab === 'keys' && (
                <div className="space-y-16 animate-in fade-in slide-in-from-bottom-4 duration-500">
                  <section>
                    <h3 className={cn("mb-6 text-xl font-black tracking-tight", isNight ? "text-slate-100" : "text-slate-800")}>Neural Gateway Keys</h3>
                    <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                        <div className={cn(
                            "group relative rounded-2xl border p-4 transition-colors",
                            isNight 
                                ? "border-rose-900/30 bg-rose-900/10 focus-within:border-rose-500 focus-within:bg-[#0d1117]" 
                                : "border-blue-100 bg-blue-50/20 focus-within:border-blue-400 focus-within:bg-white"
                        )}>
                        <label className={cn("text-[9px] font-black tracking-widest uppercase block mb-1", isNight ? "text-rose-500" : "text-blue-500")}>OpenAI Provider</label>
                        <input type="password" value="sk-••••••••••••" readOnly className={cn("w-full bg-transparent font-mono text-sm font-bold outline-none", isNight ? "text-slate-400" : "text-slate-700")} />
                        <div className="absolute top-1/2 right-4 -translate-y-1/2 text-[10px] font-bold text-green-500 flex items-center">
                            <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                            CONNECTED
                        </div>
                        </div>
                        <div className={cn(
                            "group relative rounded-2xl border p-4 transition-colors",
                             isNight
                                ? "border-rose-900/30 bg-[#0d1117] focus-within:border-rose-500"
                                : "border-blue-100 bg-white focus-within:border-blue-400"
                        )}>
                        <label className="text-[9px] font-black tracking-widest text-slate-400 uppercase block mb-1">OpenRouter API</label>
                        <input type="password" placeholder="Enter Key..." className={cn("w-full bg-transparent font-mono text-sm font-bold outline-none placeholder:text-slate-300", isNight ? "text-slate-200" : "text-slate-700")} />
                        </div>
                    </div>
                  </section>

                  <section>
                    <div className={cn("mb-6 flex items-end justify-between border-b pb-2", isNight ? "border-rose-900/30" : "border-blue-50")}>
                        <h3 className={cn("text-xl font-black tracking-tight", isNight ? "text-slate-100" : "text-slate-800")}>Core Database Sync</h3>
                        <span className="font-mono text-[10px] font-bold text-green-500 flex items-center">
                            <Shield className="w-3 h-3 mr-1" />
                            ENCRYPTED_SSL
                        </span>
                    </div>

                    <div className="space-y-6">
                        <div className="grid grid-cols-2 gap-4">
                        <div className={cn("rounded-2xl border p-4", isNight ? "bg-[#0d1117] border-rose-900/30" : "bg-white border-blue-100")}>
                            <label className="mb-1 block text-[9px] font-black tracking-widest text-slate-400 uppercase">Database Host</label>
                            <input type="text" placeholder="localhost" className={cn("w-full text-sm font-bold outline-none", isNight ? "bg-transparent text-slate-200" : "text-slate-700")} />
                        </div>
                        <div className={cn("rounded-2xl border p-4", isNight ? "bg-[#0d1117] border-rose-900/30" : "bg-white border-blue-100")}>
                            <label className="mb-1 block text-[9px] font-black tracking-widest text-slate-400 uppercase">Port</label>
                            <input type="text" placeholder="5432" className={cn("w-full text-sm font-bold outline-none", isNight ? "bg-transparent text-slate-200" : "text-slate-700")} />
                        </div>
                        </div>
                    </div>
                  </section>
                </div>
              )}

              {activeTab === 'account' && (
                 <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <div className="flex items-center space-x-6">
                        <div className={cn("h-24 w-24 rounded-full border-4 p-1", isNight ? "border-rose-900/30" : "border-blue-100")}>
                            <div className="h-full w-full rounded-full bg-slate-200 overflow-hidden">
                                <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=Sensei" alt="Avatar" className="h-full w-full object-cover" />
                            </div>
                        </div>
                        <div>
                            <h2 className={cn("text-2xl font-black", isNight ? "text-slate-100" : "text-slate-800")}>Sensei</h2>
                            <p className="text-sm font-medium text-slate-400">Clearance Level 5 // Administrator</p>
                        </div>
                    </div>

                    <section>
                         <h3 className="mb-4 text-sm font-black tracking-widest text-slate-400 uppercase">Security</h3>
                         <div className={cn("rounded-2xl border p-6 flex items-center justify-between", isNight ? "bg-[#0d1117] border-rose-900/30" : "bg-white border-blue-100")}>
                            <div>
                                <p className={cn("text-sm font-bold", isNight ? "text-slate-200" : "text-slate-800")}>Multi-Factor Authentication</p>
                                <p className="text-xs text-slate-400 mt-1">Add an extra layer of security.</p>
                            </div>
                            <div className={cn("h-6 w-11 rounded-full relative cursor-pointer transition-colors", isNight ? "bg-slate-700 hover:bg-slate-600" : "bg-slate-200 hover:bg-slate-300")}>
                                <div className="absolute top-1 left-1 h-4 w-4 bg-white rounded-full shadow-sm transition-transform"></div>
                            </div>
                         </div>
                    </section>
                 </div>
              )}

              {activeTab === 'personalize' && (
                  <div className="flex items-center justify-center h-full text-slate-400 font-medium text-sm animate-in fade-in slide-in-from-bottom-4 duration-500">
                      Module Under Construction
                  </div>
              )}

            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}
