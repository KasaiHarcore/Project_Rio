"use client"

import React, { useState } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { Search, Book, FileText, ChevronRight, Shield, Zap, Code, Terminal, ExternalLink, Bookmark } from 'lucide-react'
import { cn } from "@/lib/utils"
import { motion, AnimatePresence } from "framer-motion"
import { useTheme } from '@/components/providers/theme-provider'
import { getCycleConfig } from '@/lib/cycle-config'

// Mock Documentation Structure
type DocCategory = 'guide' | 'api' | 'system'

interface DocArticle {
  id: string
  title: string
  category: DocCategory
  readTime: string
  content: (isNight: boolean) => React.ReactNode
}


const docs: DocArticle[] = [
  {
    id: 'intro',
    title: 'System Orientation',
    category: 'guide',
    readTime: '2 min',
    content: (isNight) => (
      <div className="space-y-4">
        <div className={cn("rounded-xl border p-4 text-sm", isNight ? "bg-rose-900/20 border-rose-800/40 text-rose-200" : "bg-blue-50 border-blue-100 text-blue-800")}>
          <strong>Mission Statement:</strong> The Schale Agent System is designed to assist Sensei in managing daily operations, strategic analysis, and student data processing.
        </div>
        <p className={cn(isNight ? "text-slate-300" : "text-slate-600")}>
          Welcome to the <strong>Schale Operating System (OS_VER.3)</strong>. This platform integrates advanced Neural Network processing with a secure, highly intuitive interface for tactical command.
        </p>
        <h3 className={cn("text-lg font-bold mt-6", isNight ? "text-slate-100" : "text-slate-800")}>Core Capabilities</h3>
        <ul className={cn("list-disc pl-5 space-y-2", isNight ? "text-slate-300" : "text-slate-600")}>
          <li><strong>Natural Language Processing:</strong> Direct neural link for conversational querying.</li>
          <li><strong>RAG Architecture:</strong> Retrieval-Augmented Generation for accessing archived knowledge bases.</li>
          <li><strong>Artifact Generation:</strong> Automatic creation of code snippets, study plans, and tactical diagrams.</li>
        </ul>
      </div>
    )
  },
  {
    id: 'api-keys',
    title: 'Neural Link Configuration',
    category: 'api',
    readTime: '5 min',
    content: (isNight) => (
      <div className="space-y-4">
        <p className={cn(isNight ? "text-slate-300" : "text-slate-600")}>
          To establish a stable connection with external computation nodes (LLMs), valid security tokens are required.
        </p>
        <div className={cn("relative rounded-xl p-4 font-mono text-xs overflow-hidden group", isNight ? "bg-black/40 text-rose-300 border border-rose-900/30" : "bg-slate-900 text-blue-300")}>
            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="text-xs bg-white/10 hover:bg-white/20 px-2 py-1 rounded text-white icon-copy">Copy</button>
            </div>
            <span className={cn(isNight ? "text-rose-400" : "text-purple-400")}>export</span> SCHALE_API_KEY=<span className="text-green-400">"sk_live_..."</span><br/>
            <span className={cn(isNight ? "text-rose-400" : "text-purple-400")}>export</span> ARONA_ENDPOINT=<span className="text-green-400">"https://api.schale.gg/v1"</span>
        </div>
        <p className={cn("text-xs italic", isNight ? "text-slate-500" : "text-slate-400")}>
          WARNING: Do not share your private keys with unauthorized personnel or students from Gehenna Academy.
        </p>
      </div>
    )
  },
  {
    id: 'troubleshooting',
    title: 'Emergency Protocols',
    category: 'system',
    readTime: '3 min',
    content: (isNight) => (
      <div className="space-y-4">
        <p className={cn(isNight ? "text-slate-300" : "text-slate-600")}>
          In the event of a system crash or unexpected behavior (AI Hallucinations), follow these steps immediately.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
           <div className={cn("border rounded-xl p-4", isNight ? "border-red-900/40 bg-red-900/20" : "border-red-100 bg-red-50/50")}>
              <h4 className={cn("font-bold flex items-center gap-2 mb-2", isNight ? "text-red-400" : "text-red-600")}>
                 <Shield className="h-4 w-4" /> Containment
              </h4>
              <p className={cn("text-xs", isNight ? "text-red-300/80" : "text-red-800")}>Immediately disconnect the active session via the "Abort" button in the Mission Control panel.</p>
           </div>
           <div className={cn("border rounded-xl p-4", isNight ? "border-amber-900/40 bg-amber-900/20" : "border-amber-100 bg-amber-50/50")}>
              <h4 className={cn("font-bold flex items-center gap-2 mb-2", isNight ? "text-amber-400" : "text-amber-600")}>
                 <Zap className="h-4 w-4" /> System Reset
              </h4>
              <p className={cn("text-xs", isNight ? "text-amber-300/80" : "text-amber-800")}>Clear local cache and re-authenticate. Artifacts are safely stored in the cloud.</p>
           </div>
        </div>
      </div>
    )
  }
]

export default function DocsPage() {
  const [activeDoc, setActiveDoc] = useState<string>(docs[0].id)
  const [searchQuery, setSearchQuery] = useState('')
  
  const { theme } = useTheme()
  const isNight = theme === 'dark'
  const config = getCycleConfig(theme)
  
  const currentDoc = docs.find(d => d.id === activeDoc) || docs[0]

  return (
    <DashboardLayout>
      <PageTransition className={cn("flex-1 flex flex-col overflow-hidden", isNight ? "bg-[#0f111a]" : "bg-[#F4F9FF]")}>
        {/* Header */}
        <header className={cn(
            "relative flex h-16 items-center justify-between border-b px-8 backdrop-blur-md flex-shrink-0",
             isNight ? "border-rose-900/40 bg-[#0d1117]/50" : "border-blue-100 bg-white/40"
        )}>
          <div className={cn(
              "absolute bottom-0 left-0 h-[1px] w-full opacity-50 bg-gradient-to-r from-transparent to-transparent",
              isNight ? "via-rose-500/50" : "via-blue-300"
          )}></div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-xl shadow-lg",
                  isNight ? "bg-gradient-to-br from-rose-500 to-rose-600 shadow-rose-500/20" : "bg-gradient-to-br from-indigo-500 to-indigo-600 shadow-indigo-500/20"
              )}>
                <Book className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className={cn("text-lg font-black", isNight ? "text-slate-100" : "text-slate-800")}>Operational Manual</h1>
                <p className={cn("text-[10px] font-bold tracking-wider uppercase", isNight ? "text-slate-500" : "text-slate-400")}>Standard Procedures</p>
              </div>
            </div>
          </div>

          <div className="relative w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search protocols..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={cn(
                  "w-full pl-10 pr-4 py-2 rounded-xl border text-sm outline-none transition-all",
                  isNight 
                    ? "bg-[#0d1117]/60 border-rose-900/40 text-rose-100 placeholder:text-rose-900/50 focus:border-rose-700 focus:ring-2 focus:ring-rose-900/20"
                    : "bg-white/60 border-blue-100 text-slate-700 placeholder:text-slate-400 focus:border-blue-300 focus:ring-2 focus:ring-blue-100"
              )}
            />
          </div>
        </header>

        {/* Content Layout */}
        <div className="flex-1 overflow-hidden flex flex-col md:flex-row">
            
            {/* Sidebar Navigation */}
            <aside className={cn(
                "w-full md:w-64 lg:w-72 border-r backdrop-blur-sm overflow-y-auto p-4 flex-shrink-0 transition-colors",
                isNight ? "border-rose-900/30 bg-[#0d1117]/30" : "border-blue-100 bg-white/50"
            )}>
                
                <div className="mb-6">
                    <p className={cn("text-[10px] font-black uppercase tracking-widest mb-3 px-2", isNight ? "text-rose-900/70" : "text-slate-400")}>Knowledge Domains</p>
                    <div className="space-y-1">
                        {docs.map(doc => (
                            <button
                                key={doc.id}
                                onClick={() => setActiveDoc(doc.id)}
                                className={cn(
                                    "w-full text-left flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all group",
                                    activeDoc === doc.id 
                                        ? isNight 
                                            ? "bg-rose-500/10 text-rose-400 shadow-sm ring-1 ring-rose-900/40" 
                                            : "bg-white text-blue-600 shadow-sm ring-1 ring-blue-100" 
                                        : isNight
                                            ? "text-slate-400 hover:bg-rose-900/20 hover:text-rose-300"
                                            : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                                )}
                            >
                                <span className="flex items-center gap-2">
                                    {doc.category === 'guide' && <Book className="h-3.5 w-3.5 opacity-70" />}
                                    {doc.category === 'api' && <Code className="h-3.5 w-3.5 opacity-70" />}
                                    {doc.category === 'system' && <Terminal className="h-3.5 w-3.5 opacity-70" />}
                                    {doc.title}
                                </span>
                                {activeDoc === doc.id && (
                                    <motion.div layoutId="active-indicator" className={cn("h-1.5 w-1.5 rounded-full", isNight ? "bg-rose-500" : "bg-blue-500")} />
                                )}
                            </button>
                        ))}
                    </div>
                </div>

                <div className={cn(
                    "mt-8 rounded-xl p-5 text-white shadow-lg mx-2",
                    isNight ? "bg-gradient-to-br from-rose-900 to-red-950 shadow-rose-900/20" : "bg-gradient-to-br from-indigo-500 to-blue-600 shadow-blue-200"
                )}>
                    <h4 className="font-bold flex items-center gap-2 mb-2">
                        <Zap className="h-4 w-4" /> Pro Tip
                    </h4>
                    <p className="text-xs opacity-90 leading-relaxed">
                        You can access the global command palette by pressing <kbd className="bg-white/20 px-1 rounded font-mono">Cmd+K</kbd> anywhere in the system.
                    </p>
                </div>
            </aside>

            {/* Main Reading Area */}
            <main className="flex-1 overflow-y-auto p-6 lg:p-12 relative">
                {/* Background Decoration */}
                <div className={cn(
                    "absolute top-0 right-0 w-64 h-64 rounded-full blur-3xl pointer-events-none -z-10 transition-colors",
                    isNight ? "bg-rose-900/10" : "bg-blue-400/5"
                )} />
                
                <AnimatePresence mode="wait">
                    <motion.div
                        key={currentDoc.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.3 }}
                        className="max-w-3xl mx-auto"
                    >
                        {/* Article Header */}
                        <div className={cn("mb-8 border-b pb-8", isNight ? "border-rose-900/30" : "border-blue-100")}>
                            <div className="flex items-center gap-2 mb-4">
                                <span className={cn(
                                    "px-2.5 py-1 rounded text-[10px] font-black uppercase tracking-wider border",
                                    currentDoc.category === 'guide' ? (isNight ? "bg-blue-900/20 text-blue-300 border-blue-800/50" : "bg-blue-50 text-blue-600 border-blue-100") :
                                    currentDoc.category === 'api' ? (isNight ? "bg-purple-900/20 text-purple-300 border-purple-800/50" : "bg-purple-50 text-purple-600 border-purple-100") :
                                    (isNight ? "bg-slate-800 text-slate-300 border-slate-700" : "bg-slate-100 text-slate-600 border-slate-200")
                                )}>
                                    {currentDoc.category}
                                </span>
                                <span className={cn("text-xs font-medium flex items-center gap-1", isNight ? "text-slate-500" : "text-slate-400")}>
                                    <Bookmark className="h-3 w-3" />
                                    Read time: {currentDoc.readTime}
                                </span>
                            </div>
                            <h1 className={cn("text-3xl font-black tracking-tight mb-2", isNight ? "text-slate-100" : "text-slate-800")}>
                                {currentDoc.title}
                            </h1>
                            <div className="flex items-center gap-2 text-sm text-slate-500">
                                <span>Last updated: Feb 6, 2026</span>
                                <span className="h-1 w-1 rounded-full bg-slate-300" />
                                <span className="flex items-center gap-1 cursor-pointer hover:text-blue-500 transition-colors">
                                    Open in dedicated view <ExternalLink className="h-3 w-3" />
                                </span>
                            </div>
                        </div>

                        {/* Article Content */}
                        <div className={cn("prose prose-sm md:prose-base max-w-none", isNight ? "prose-invert" : "prose-slate")}>
                            {currentDoc.content(isNight)}
                        </div>

                        {/* Feedback Section */}
                        <div className={cn("mt-12 pt-8 border-t flex items-center justify-between", isNight ? "border-rose-900/30" : "border-blue-50")}>
                            <p className={cn("text-sm font-medium", isNight ? "text-slate-400" : "text-slate-500")}>Was this protocol helpful?</p>
                            <div className="flex gap-2">
                                <button className={cn(
                                    "px-4 py-2 rounded-lg border text-sm font-bold transition-all",
                                    isNight 
                                        ? "border-rose-900/40 bg-[#0d1117]/60 text-slate-300 hover:bg-rose-900/20 hover:border-rose-700" 
                                        : "border-blue-100 bg-white text-slate-600 hover:bg-blue-50 hover:border-blue-200"
                                )}>
                                    Yes, confirmed
                                </button>
                                <button className={cn(
                                    "px-4 py-2 rounded-lg border text-sm font-bold transition-all",
                                    isNight 
                                        ? "border-rose-900/40 bg-[#0d1117]/60 text-slate-300 hover:bg-red-900/20 hover:border-red-800" 
                                        : "border-blue-100 bg-white text-slate-600 hover:bg-red-50 hover:border-red-200"
                                )}>
                                    No, vague
                                </button>
                            </div>
                        </div>
                    </motion.div>
                </AnimatePresence>
            </main>
        </div>
      </PageTransition>
    </DashboardLayout>
  )
}
