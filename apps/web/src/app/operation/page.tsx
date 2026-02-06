"use client"

import React, { useState } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { motion, AnimatePresence } from 'framer-motion'
import { MessageSquare, Plus, Search, Video, Phone, MoreVertical, Archive, Trash2, Pin, CheckCheck, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { MissionControl } from "@/components/features/mission/MissionControl"
import { useTheme } from '@/components/providers/theme-provider'

// Mock Data for "Operations" (Chats)
const MOCK_OPERATIONS = [
    { id: '1', title: 'Python Basics Strategy', lastMsg: 'Explain List Comprehensions...', time: '10:42 AM', unread: 2, isPinned: true, status: 'online' },
    { id: '2', title: 'SQL Database Design', lastMsg: 'The schema looks solid, but...', time: 'Yesterday', unread: 0, isPinned: false, status: 'offline' },
    { id: '3', title: 'RAG Optimization', lastMsg: 'Vector store connection failed...', time: 'Mon', unread: 0, isPinned: false, status: 'busy' },
]

export default function OperationPage() {
    const [selectedOpId, setSelectedOpId] = useState<string | null>(null)
    const { theme } = useTheme()
    const isNight = theme === 'dark'
    const isPlana = isNight

    return (
        <DashboardLayout>
            <div className="flex h-full w-full overflow-hidden">
                {/* Left Panel: Operation List (MomoTalk Style) */}
                <aside className={cn(
                    "w-full md:w-[320px] lg:w-[380px] flex flex-col border-r backdrop-blur-xl z-20 transition-all absolute md:relative h-full",
                     selectedOpId ? "hidden md:flex" : "flex",
                     isPlana ? "border-rose-900/20 bg-[#0d1117]" : "border-blue-100 bg-white/60"
                )}>
                    {/* Header */}
                    <div className={cn("p-4 border-b flex flex-col gap-4", isPlana ? "border-rose-900/20" : "border-blue-100/50")}>
                        <div className="flex items-center justify-between">
                             <h1 className={cn("text-xl font-black tracking-widest", isPlana ? "text-slate-100" : "text-slate-700")}>
                                OPERATIONS
                             </h1>
                             <button className={cn(
                                "p-2 rounded-full transition-colors",
                                isPlana ? "bg-rose-600 hover:bg-rose-700 text-white shadow-lg shadow-rose-900/20" : "bg-[#1289F4] hover:bg-blue-600 text-white"
                             )}>
                                <Plus size={20} />
                             </button>
                        </div>
                        
                        {/* Search Bar */}
                        <div className="relative">
                            <Search className="absolute left-3 top-2.5 text-slate-400 w-4 h-4" />
                            <input 
                                placeholder="Search operations..." 
                                className={cn(
                                    "w-full pl-9 pr-4 py-2 rounded-xl text-sm font-bold focus:outline-none focus:ring-2 transition-all",
                                    isPlana 
                                        ? "bg-[#010409] border border-rose-900/30 text-slate-200 placeholder:text-slate-600 focus:ring-rose-500" 
                                        : "bg-slate-100 text-slate-700 placeholder:text-slate-400 focus:ring-[#1289F4]"
                                )}
                            />
                        </div>
                    </div>

                    {/* Chat List */}
                    <div className="flex-1 overflow-y-auto p-2 space-y-1 custom-scrollbar">
                        {MOCK_OPERATIONS.map((op) => (
                            <div 
                                key={op.id}
                                onClick={() => setSelectedOpId(op.id)}
                                className={cn(
                                    "group relative p-3 rounded-xl cursor-pointer transition-all flex items-center gap-3",
                                    selectedOpId === op.id 
                                        ? (isPlana ? "bg-rose-900/10 border border-rose-900/20" : "bg-white shadow-sm")
                                        : (isPlana ? "hover:bg-rose-900/5 border border-transparent" : "hover:bg-black/5"),
                                )}
                            >
                                {/* Avatar */}
                                <div className="relative">
                                    <div className={cn(
                                        "w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold text-white shadow-sm",
                                        isPlana ? "bg-gradient-to-br from-rose-500 to-red-700" : "bg-gradient-to-br from-blue-400 to-blue-600"
                                    )}>
                                        {op.title.substring(0, 2).toUpperCase()}
                                    </div>
                                    <span className={cn(
                                        "absolute bottom-0 right-0 w-3 h-3 border-2 rounded-full",
                                        isPlana ? "border-[#0d1117]" : "border-white",
                                        op.status === 'online' ? "bg-green-500" : "bg-slate-400"
                                    )} />
                                </div>

                                {/* Info */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex justify-between items-baseline mb-0.5">
                                        <h3 className={cn("font-bold text-sm truncate", isPlana ? "text-slate-200" : "text-slate-700")}>
                                            {op.title}
                                        </h3>
                                        <span className="text-[10px] font-bold text-slate-400">{op.time}</span>
                                    </div>
                                    <p className={cn("text-xs truncate font-medium", isPlana ? "text-slate-500" : "text-slate-500")}>
                                        {op.lastMsg}
                                    </p>
                                </div>

                                {/* Badges */}
                                {op.unread > 0 && (
                                    <div className="min-w-[20px] h-5 rounded-full bg-rose-500 text-white text-[10px] font-bold flex items-center justify-center px-1">
                                        {op.unread}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>

                    {/* Footer Stats similar to MomoTalk */}
                    <div className={cn(
                        "p-3 border-t flex justify-between items-center text-[10px] font-bold uppercase tracking-wider",
                        isPlana ? "bg-[#010409] border-rose-900/20 text-slate-600" : "bg-slate-50 border-slate-100 text-slate-400"
                    )}>
                         <span>3 Operations Active</span>
                         <span>Ver 2.0</span>
                    </div>
                </aside>

                {/* Right Panel: Active Chat Area */}
                <main className={cn(
                    "flex-1 relative flex flex-col transition-colors",
                     !selectedOpId ? "hidden md:flex" : "flex",
                     isPlana ? "bg-[#0d1117]/50" : "bg-white/40"
                )}>
                    {selectedOpId ? (
                        <MissionControl />
                    ) : (
                        <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
                             <div className={cn("w-32 h-32 rounded-full flex items-center justify-center mb-6", isPlana ? "bg-white/5" : "bg-slate-100")}>
                                <MessageSquare size={48} className="opacity-20" />
                             </div>
                             <p className="font-bold tracking-widest text-sm">SELECT AN OPERATION</p>
                        </div>
                    )}
                </main>
            </div>
        </DashboardLayout>
    )
}
