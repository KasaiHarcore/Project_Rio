"use client"

import React, { useState } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { Search, Book, FileText, ChevronRight, Shield, Zap, Code, Terminal, ExternalLink, Bookmark } from 'lucide-react'
import { cn } from "@/lib/utils"
import { motion, AnimatePresence } from "framer-motion"

// Mock Documentation Structure
type DocCategory = 'guide' | 'api' | 'system'

interface DocArticle {
  id: string
  title: string
  category: DocCategory
  readTime: string
  content: React.ReactNode
}

const docs: DocArticle[] = [
  {
    id: 'intro',
    title: 'System Orientation',
    category: 'guide',
    readTime: '2 min',
    content: (
      <div className="space-y-4">
        <div className="rounded-xl bg-blue-50 border border-blue-100 p-4 text-sm text-blue-800">
          <strong>Mission Statement:</strong> The Schale Agent System is designed to assist Sensei in managing daily operations, strategic analysis, and student data processing.
        </div>
        <p className="text-slate-600">
          Welcome to the <strong>Schale Operating System (OS_VER.3)</strong>. This platform integrates advanced Neural Network processing with a secure, highly intuitive interface for tactical command.
        </p>
        <h3 className="text-lg font-bold text-slate-800 mt-6">Core Capabilities</h3>
        <ul className="list-disc pl-5 space-y-2 text-slate-600">
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
    content: (
      <div className="space-y-4">
        <p className="text-slate-600">
          To establish a stable connection with external computation nodes (LLMs), valid security tokens are required.
        </p>
        <div className="relative rounded-xl bg-slate-900 p-4 font-mono text-xs text-blue-300 overflow-hidden group">
            <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                <button className="text-xs bg-white/10 hover:bg-white/20 px-2 py-1 rounded text-white icon-copy">Copy</button>
            </div>
            <span className="text-purple-400">export</span> SCHALE_API_KEY=<span className="text-green-400">"sk_live_..."</span><br/>
            <span className="text-purple-400">export</span> ARONA_ENDPOINT=<span className="text-green-400">"https://api.schale.gg/v1"</span>
        </div>
        <p className="text-xs text-slate-400 italic">
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
    content: (
      <div className="space-y-4">
        <p className="text-slate-600">
          In the event of a system crash or unexpected behavior (AI Hallucinations), follow these steps immediately.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
           <div className="border border-red-100 bg-red-50/50 rounded-xl p-4">
              <h4 className="font-bold text-red-600 flex items-center gap-2 mb-2">
                 <Shield className="h-4 w-4" /> Containment
              </h4>
              <p className="text-xs text-red-800">Immediately disconnect the active session via the "Abort" button in the Mission Control panel.</p>
           </div>
           <div className="border border-amber-100 bg-amber-50/50 rounded-xl p-4">
              <h4 className="font-bold text-amber-600 flex items-center gap-2 mb-2">
                 <Zap className="h-4 w-4" /> System Reset
              </h4>
              <p className="text-xs text-amber-800">Clear local cache and re-authenticate. Artifacts are safely stored in the cloud.</p>
           </div>
        </div>
      </div>
    )
  }
]

export default function DocsPage() {
  const [activeDoc, setActiveDoc] = useState<string>(docs[0].id)
  const [searchQuery, setSearchQuery] = useState('')
  
  const currentDoc = docs.find(d => d.id === activeDoc) || docs[0]

  return (
    <DashboardLayout>
      <PageTransition className="flex-1 flex flex-col overflow-hidden bg-[#F4F9FF]">
        {/* Header */}
        <header className="relative flex h-16 items-center justify-between border-b border-blue-100 bg-white/40 px-8 backdrop-blur-md flex-shrink-0">
          <div className="absolute bottom-0 left-0 h-[1px] w-full bg-gradient-to-r from-transparent via-blue-300 to-transparent opacity-50"></div>
          
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 shadow-lg shadow-indigo-500/20">
                <Book className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-black text-slate-800">Operational Manual</h1>
                <p className="text-[10px] font-bold tracking-wider text-slate-400 uppercase">Standard Procedures</p>
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
              className="w-full pl-10 pr-4 py-2 rounded-xl border border-blue-100 bg-white/60 text-sm text-slate-700 placeholder:text-slate-400 outline-none focus:border-blue-300 focus:ring-2 focus:ring-blue-100 transition-all"
            />
          </div>
        </header>

        {/* Content Layout */}
        <div className="flex-1 overflow-hidden flex flex-col md:flex-row">
            
            {/* Sidebar Navigation */}
            <aside className="w-full md:w-64 lg:w-72 border-r border-blue-100 bg-white/50 backdrop-blur-sm overflow-y-auto p-4 flex-shrink-0">
                
                <div className="mb-6">
                    <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-3 px-2">Knowledge Domains</p>
                    <div className="space-y-1">
                        {docs.map(doc => (
                            <button
                                key={doc.id}
                                onClick={() => setActiveDoc(doc.id)}
                                className={cn(
                                    "w-full text-left flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-all group",
                                    activeDoc === doc.id 
                                        ? "bg-white text-blue-600 shadow-sm ring-1 ring-blue-100" 
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
                                    <motion.div layoutId="active-indicator" className="h-1.5 w-1.5 rounded-full bg-blue-500" />
                                )}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="mt-8 rounded-xl bg-gradient-to-br from-indigo-500 to-blue-600 p-5 text-white shadow-lg shadow-blue-200 mx-2">
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
                <div className="absolute top-0 right-0 w-64 h-64 bg-blue-400/5 rounded-full blur-3xl pointer-events-none -z-10" />
                
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
                        <div className="mb-8 border-b border-blue-100 pb-8">
                            <div className="flex items-center gap-2 mb-4">
                                <span className={cn(
                                    "px-2.5 py-1 rounded text-[10px] font-black uppercase tracking-wider border",
                                    currentDoc.category === 'guide' ? "bg-blue-50 text-blue-600 border-blue-100" :
                                    currentDoc.category === 'api' ? "bg-purple-50 text-purple-600 border-purple-100" :
                                    "bg-slate-50 text-slate-600 border-slate-200"
                                )}>
                                    {currentDoc.category}
                                </span>
                                <span className="text-xs font-medium text-slate-400 flex items-center gap-1">
                                    <Bookmark className="h-3 w-3" />
                                    Read time: {currentDoc.readTime}
                                </span>
                            </div>
                            <h1 className="text-3xl font-black text-slate-800 tracking-tight mb-2">
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
                        <div className="prose prose-slate prose-sm md:prose-base max-w-none">
                            {currentDoc.content}
                        </div>

                        {/* Feedback Section */}
                        <div className="mt-12 pt-8 border-t border-blue-50 flex items-center justify-between">
                            <p className="text-sm text-slate-500 font-medium">Was this protocol helpful?</p>
                            <div className="flex gap-2">
                                <button className="px-4 py-2 rounded-lg border border-blue-100 bg-white hover:bg-blue-50 hover:border-blue-200 text-sm font-bold text-slate-600 transition-all">
                                    Yes, confirmed
                                </button>
                                <button className="px-4 py-2 rounded-lg border border-blue-100 bg-white hover:bg-red-50 hover:border-red-200 text-sm font-bold text-slate-600 transition-all">
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
