"use client"

import React, { useState } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { motion } from 'framer-motion'
import { Calendar, CheckCircle2, ChevronRight, Filter, MoreHorizontal, Plus, Trophy } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useUIStore } from '@/store/ui-store'

const DAILY_TASKS = [
    { id: 1, title: 'Complete 1 RAG query', reward: '50 Credits', completed: true },
    { id: 2, title: 'Read 2 Documentation pages', reward: '30 AP', completed: false },
    { id: 3, title: 'Login before 12:00', reward: '10 Pyroxene', completed: true },
]

const WEEKLY_TASKS = [
    { id: 4, title: 'Finish SQL Module', reward: '500 Credits', completed: false },
    { id: 5, title: 'Create 3 Operations', reward: '100 AP', completed: false },
]

export default function MissionPage() {
    const activeCharacterId = useUIStore(s => s.activeCharacterId)
    const isPlana = activeCharacterId === 'plana'
    const [activeTab, setActiveTab] = useState<'daily' | 'weekly'>('daily')

    return (
        <DashboardLayout>
            <div className="flex-1 overflow-y-auto p-4 md:p-8">
                <header className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div>
                        <h1 className={cn("text-3xl font-black tracking-tight mb-2", isPlana ? "text-white" : "text-slate-800")}>
                            MISSION LIST
                        </h1>
                        <p className={cn("text-sm font-medium", isPlana ? "text-slate-400" : "text-slate-500")}>
                            Complete tasks to earn resources and increase Sensei Level.
                        </p>
                    </div>

                    {/* Tab Switcher */}
                    <div className="bg-slate-100 p-1 rounded-xl flex">
                        <TabButton active={activeTab === 'daily'} onClick={() => setActiveTab('daily')} label="Daily" />
                        <TabButton active={activeTab === 'weekly'} onClick={() => setActiveTab('weekly')} label="Weekly" />
                        <TabButton active={false} onClick={() => {}} label="Challenge" />
                    </div>
                </header>

                {/* Progress Card */}
                <div className="mb-8 p-6 rounded-3xl bg-gradient-to-r from-[#1289F4] to-[#0b5fab] text-white shadow-lg shadow-blue-500/20 relative overflow-hidden">
                    <div className="relative z-10 flex items-center justify-between">
                        <div>
                             <h3 className="text-sm font-bold opacity-80 mb-1">TOTAL PROGRESS</h3>
                             <div className="text-4xl font-black tracking-tighter">65%</div>
                        </div>
                        <div className="text-right">
                             <div className="text-xs font-bold bg-white/20 px-3 py-1 rounded-full mb-2 inline-block">
                                REAMING: 12h 30m
                             </div>
                             <p className="text-xs opacity-70">Resets automatically at 04:00 AM</p>
                        </div>
                    </div>
                    {/* Decor */}
                    <Trophy className="absolute -bottom-6 -right-6 w-32 h-32 opacity-10 rotate-12" />
                </div>

                {/* Task List */}
                <div className="space-y-4">
                    {(activeTab === 'daily' ? DAILY_TASKS : WEEKLY_TASKS).map((task) => (
                        <TaskCard key={task.id} task={task} isPlana={isPlana} />
                    ))}
                    
                    {/* Add Task Button */}
                    <button className="w-full py-4 border-2 border-dashed border-slate-300 rounded-2xl text-slate-400 font-bold flex items-center justify-center gap-2 hover:bg-slate-50 transition-colors">
                        <Plus size={20} /> ADD CUSTOM MISSION
                    </button>
                </div>
            </div>
        </DashboardLayout>
    )
}

function TabButton({ active, onClick, label }: { active: boolean, onClick: () => void, label: string }) {
    return (
        <button 
            onClick={onClick}
            className={cn(
                "px-6 py-2 rounded-lg text-sm font-bold transition-all",
                active ? "bg-white text-slate-800 shadow-sm" : "text-slate-400 hover:text-slate-600"
            )}
        >
            {label}
        </button>
    )
}

function TaskCard({ task, isPlana }: { task: any, isPlana: boolean }) {
    return (
        <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className={cn(
                "group p-4 rounded-2xl flex items-center gap-4 transition-all hover:scale-[1.01]",
                isPlana ? "bg-[#2d253a]/60 hover:bg-[#2d253a]" : "bg-white hover:shadow-md border border-slate-100"
            )}
        >
             {/* Status Icon */}
             <div className={cn(
                 "w-12 h-12 rounded-full flex items-center justify-center shrink-0",
                 task.completed 
                    ? "bg-green-100 text-green-600" 
                    : "bg-slate-100 text-slate-300 group-hover:bg-[#1289F4]/10 group-hover:text-[#1289F4]"
             )}>
                {task.completed ? <CheckCircle2 size={24} /> : <div className="w-6 h-6 border-4 border-current rounded-full opacity-40" />}
             </div>

             {/* Content */}
             <div className="flex-1">
                 <h3 className={cn("font-bold text-lg", task.completed && "line-through opacity-50", isPlana ? "text-slate-200" : "text-slate-700")}>
                    {task.title}
                 </h3>
                 <div className="flex items-center gap-2 mt-1">
                     <span className="text-[10px] uppercase font-bold text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                        REWARD
                     </span>
                     <span className="text-xs font-bold text-[#1289F4]">
                        {task.reward}
                     </span>
                 </div>
             </div>

             {/* Action Button */}
             {!task.completed && (
                 <button className={cn(
                     "px-4 py-2 rounded-lg font-bold text-sm transition-colors",
                     isPlana 
                        ? "bg-rose-500 hover:bg-rose-600 text-white" 
                        : "bg-[#1289F4] hover:bg-blue-600 text-white"
                 )}>
                    Claim
                 </button>
             )}
        </motion.div>
    )
}
