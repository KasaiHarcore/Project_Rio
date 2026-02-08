"use client"

import React, { useState, useRef, useCallback } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { motion, AnimatePresence, Reorder } from 'framer-motion'
import { Calendar, CheckCircle2, ChevronRight, Filter, GripVertical, MoreHorizontal, Plus, Trophy } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useUIStore } from '@/store/ui-store'
import { useTheme } from '@/components/providers/theme-provider'
import { toast } from '@/hooks/use-toast'

interface Task {
    id: number
    title: string
    reward: string
    completed: boolean
}

const INITIAL_DAILY_TASKS: Task[] = [
    { id: 1, title: 'Complete 1 RAG query', reward: '50 Credits', completed: true },
    { id: 2, title: 'Read 2 Documentation pages', reward: '30 AP', completed: false },
    { id: 3, title: 'Login before 12:00', reward: '10 Pyroxene', completed: true },
]

const INITIAL_WEEKLY_TASKS: Task[] = [
    { id: 4, title: 'Finish SQL Module', reward: '500 Credits', completed: false },
    { id: 5, title: 'Create 3 Operations', reward: '100 AP', completed: false },
]

export default function MissionPage() {
    const { theme } = useTheme()
    const isNight = theme === 'dark'
    const isPlana = isNight 

    const [activeTab, setActiveTab] = useState<'daily' | 'weekly'>('daily')
    const [dailyTasks, setDailyTasks] = useState<Task[]>(INITIAL_DAILY_TASKS)
    const [weeklyTasks, setWeeklyTasks] = useState<Task[]>(INITIAL_WEEKLY_TASKS)

    const activeTasks = activeTab === 'daily' ? dailyTasks : weeklyTasks
    const setActiveTasks = activeTab === 'daily' ? setDailyTasks : setWeeklyTasks

    return (
        <DashboardLayout>
            <PageTransition className="flex-1 overflow-y-auto p-4 md:p-8">
                <header className="mb-8 flex flex-col md:flex-row md:items-end justify-between gap-4">
                    <div>
                        <h1 className={cn("text-3xl font-black tracking-tight mb-2", isPlana ? "text-slate-100" : "text-slate-800")}>
                            MISSION LIST
                        </h1>
                        <p className={cn("text-sm font-medium", isPlana ? "text-slate-400" : "text-slate-500")}>
                            Complete tasks to earn resources and increase Sensei Level.
                        </p>
                    </div>

                    {/* Tab Switcher */}
                    <div className={cn("p-1 rounded-xl flex", isPlana ? "bg-[#0d1117] border border-rose-900/40" : "bg-slate-100")}>
                        <TabButton active={activeTab === 'daily'} onClick={() => setActiveTab('daily')} label="Daily" isPlana={isPlana} />
                        <TabButton active={activeTab === 'weekly'} onClick={() => setActiveTab('weekly')} label="Weekly" isPlana={isPlana} />
                        <TabButton active={false} onClick={() => {}} label="Challenge" isPlana={isPlana} />
                    </div>
                </header>

                {/* Progress Card */}
                <div className={cn(
                    "mb-8 p-6 rounded-3xl text-white shadow-lg relative overflow-hidden transition-all",
                    isPlana 
                        ? "bg-gradient-to-r from-rose-600 to-red-800 shadow-rose-900/20" 
                        : "bg-gradient-to-r from-[#1289F4] to-[#0b5fab] shadow-blue-500/20"
                )}>
                    <div className="relative z-10 flex items-center justify-between">
                        <div>
                             <h3 className="text-sm font-bold opacity-80 mb-1">TOTAL PROGRESS</h3>
                             <div className="text-4xl font-black tracking-tighter">65%</div>
                        </div>
                        <div className="text-right">
                             <div className="text-xs font-bold bg-white/20 px-3 py-1 rounded-full mb-2 inline-block">
                                REMAINING: 12h 30m
                             </div>
                             <p className="text-xs opacity-70">Resets automatically at 04:00 AM</p>
                        </div>
                    </div>
                    {/* Decor */}
                    <Trophy className="absolute -bottom-6 -right-6 w-32 h-32 opacity-10 rotate-12" />
                </div>

                {/* Task List — Drag-and-Drop Reorderable */}
                <Reorder.Group
                  axis="y"
                  values={activeTasks}
                  onReorder={setActiveTasks}
                  className="space-y-4"
                >
                    {activeTasks.map((task) => (
                        <DraggableTaskCard key={task.id} task={task} isPlana={isPlana} />
                    ))}
                </Reorder.Group>

                    {/* Hint */}
                    <p className={cn("text-center text-[10px] font-bold uppercase tracking-wider mt-3 mb-4", isPlana ? "text-slate-600" : "text-slate-300")}>
                        Drag tasks to reorder priority
                    </p>
                    
                    {/* Add Task Button */}
                    <button className={cn(
                        "w-full py-4 border-2 border-dashed rounded-2xl font-bold flex items-center justify-center gap-2 transition-colors",
                        isPlana 
                            ? "border-rose-900/30 text-rose-500/50 hover:bg-rose-900/10 hover:border-rose-900/50" 
                            : "border-slate-300 text-slate-400 hover:bg-slate-50"
                    )}>
                        <Plus size={20} /> ADD CUSTOM MISSION
                    </button>
            </PageTransition>
        </DashboardLayout>
    )
}

function TabButton({ active, onClick, label, isPlana }: { active: boolean, onClick: () => void, label: string, isPlana: boolean }) {
    return (
        <button 
            onClick={onClick}
            className={cn(
                "px-6 py-2 rounded-lg text-sm font-bold transition-all",
                active 
                    ? (isPlana ? "bg-rose-600 text-white shadow-sm" : "bg-white text-slate-800 shadow-sm") 
                    : (isPlana ? "text-slate-500 hover:text-rose-400" : "text-slate-400 hover:text-slate-600")
            )}
        >
            {label}
        </button>
    )
}

function DraggableTaskCard({ task, isPlana }: { task: Task, isPlana: boolean }) {
    return (
        <Reorder.Item 
            value={task}
            id={String(task.id)}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            whileDrag={{
                scale: 1.03,
                boxShadow: isPlana
                  ? "0 8px 32px rgba(225,29,72,0.25)"
                  : "0 8px 32px rgba(18,137,244,0.2)",
                cursor: "grabbing",
            }}
            className={cn(
                "group p-4 rounded-2xl flex items-center gap-4 transition-all",
                isPlana 
                    ? "bg-[#0d1117]/60 border border-rose-900/20 hover:bg-[#0d1117] hover:border-rose-900/40" 
                    : "bg-white hover:shadow-md border border-slate-100"
            )}
        >
             {/* Drag Handle */}
             <div className={cn(
                 "cursor-grab active:cursor-grabbing p-1 rounded-lg transition-colors opacity-40 hover:opacity-100",
                 isPlana ? "text-rose-500 hover:bg-rose-900/20" : "text-slate-400 hover:bg-slate-100"
             )}>
                <GripVertical size={18} />
             </div>

             {/* Status Icon */}
             <div className={cn(
                 "w-12 h-12 rounded-full flex items-center justify-center shrink-0 transition-colors",
                 task.completed 
                    ? (isPlana ? "bg-rose-900/20 text-rose-500" : "bg-green-100 text-green-600")
                    : (isPlana ? "bg-slate-800 text-slate-600 group-hover:bg-rose-900/10 group-hover:text-rose-500" : "bg-slate-100 text-slate-300 group-hover:bg-[#1289F4]/10 group-hover:text-[#1289F4]")
             )}>
                {task.completed ? <CheckCircle2 size={24} /> : <div className="w-6 h-6 border-4 border-current rounded-full opacity-40" />}
             </div>

             {/* Content */}
             <div className="flex-1">
                 <h3 className={cn("font-bold text-lg", task.completed && "line-through opacity-50", isPlana ? "text-slate-200" : "text-slate-700")}>
                    {task.title}
                 </h3>
                 <div className="flex items-center gap-2 mt-1">
                     <span className={cn("text-[10px] uppercase font-bold px-2 py-0.5 rounded", isPlana ? "text-slate-400 bg-slate-800" : "text-slate-400 bg-slate-100")}>
                        REWARD
                     </span>
                     <span className={cn("text-xs font-bold", isPlana ? "text-rose-400" : "text-[#1289F4]")}>
                        {task.reward}
                     </span>
                 </div>
             </div>

             {/* Action Button */}
             {!task.completed && (
                 <button className={cn(
                     "px-4 py-2 rounded-lg font-bold text-sm transition-colors",
                     isPlana 
                        ? "bg-rose-600 hover:bg-rose-700 text-white shadow-lg shadow-rose-900/20" 
                        : "bg-[#1289F4] hover:bg-blue-600 text-white"
                 )}>
                    Claim
                 </button>
             )}
        </Reorder.Item>
    )
}
