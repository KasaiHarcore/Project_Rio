"use client"

import React, { useState, useMemo, useEffect, useRef } from 'react'
import {
    ChevronLeft,
    ChevronRight,
    Search,
    Calendar as CalendarIcon,
    Clock,
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useMissionStore, type Mission } from '@/features/mission/store'
import { PRIORITY_CONFIG, STATUS_CONFIG, formatDuration } from '@/types/mission'
import { ExternalLink } from 'lucide-react'

/**
 * Premium Weekly Calendar View designed based on ideas/calendar.webp template.
 * Matches Schale / Blue Archive dark mode aesthetics.
 */
export function CalendarView() {
    const { missions, fetchMissions } = useMissionStore()

    const [currentDate, setCurrentDate] = useState(new Date())
    const [selectedDate, setSelectedDate] = useState(new Date())
    const [viewMode, setViewMode] = useState<'monthly' | 'weekly'>('monthly')

    const [now, setNow] = useState(new Date())

    useEffect(() => {
        fetchMissions()
        const timer = setInterval(() => setNow(new Date()), 60000)
        return () => clearInterval(timer)
    }, [fetchMissions])

    const year = currentDate.getFullYear()
    const month = currentDate.getMonth()

    const monthName = currentDate.toLocaleString('en-US', { month: 'long', year: 'numeric' })
    const monthOnlyName = selectedDate.toLocaleString('en-US', { month: 'short' })

    const daysInMonth = new Date(year, month + 1, 0).getDate()
    const firstDayOfMonth = new Date(year, month, 1).getDay()

    // Map missions by day in current month
    const missionsByDay = useMemo(() => {
        const map: Record<string, Mission[]> = {}
        for (const m of missions) {
            if (!m.deadline) continue
            const d = new Date(m.deadline)
            if (d.getFullYear() === year && d.getMonth() === month) {
                const key = String(d.getDate())
                if (!map[key]) map[key] = []
                map[key].push(m)
            }
        }
        return map
    }, [missions, year, month])

    const missionsForSelectedDate = useMemo(() => {
        const d = selectedDate
        return missions.filter(m => {
            if (!m.deadline) return false
            const md = new Date(m.deadline)
            return md.getFullYear() === d.getFullYear() && md.getMonth() === d.getMonth() && md.getDate() === d.getDate()
        })
    }, [missions, selectedDate])

    const handlePrevMonth = () => setCurrentDate(new Date(year, month - 1, 1))
    const handleNextMonth = () => setCurrentDate(new Date(year, month + 1, 1))
    const handleToday = () => {
        const today = new Date()
        setCurrentDate(new Date(today.getFullYear(), today.getMonth(), 1))
        setSelectedDate(today)
    }

    const isToday = (d: number, m: number = month, y: number = year) => {
        const today = new Date()
        return today.getFullYear() === y && today.getMonth() === m && today.getDate() === d
    }
    const isSelected = (d: number, m: number = month, y: number = year) => {
        return selectedDate.getFullYear() === y && selectedDate.getMonth() === m && selectedDate.getDate() === d
    }

    // Prepare grid cells for the mini calendar
    const gridCells = []
    const prevMonthDays = new Date(year, month, 0).getDate()

    for (let i = firstDayOfMonth - 1; i >= 0; i--) {
        gridCells.push({ d: prevMonthDays - i, m: month - 1, y: year, isCurrentMonth: false, isPrevMonth: true })
    }
    for (let i = 1; i <= daysInMonth; i++) {
        gridCells.push({ d: i, m: month, y: year, isCurrentMonth: true, isPrevMonth: false })
    }
    let nextMonthDay = 1
    while (gridCells.length % 7 !== 0 || gridCells.length < 35) {
        gridCells.push({ d: nextMonthDay++, m: month + 1, y: year, isCurrentMonth: false, isPrevMonth: false })
    }

    // Weekly View Calculations
    const startOfWeek = new Date(selectedDate)
    startOfWeek.setDate(selectedDate.getDate() - selectedDate.getDay()) // Sunday

    const weekDays = Array.from({ length: 7 }).map((_, i) => {
        const d = new Date(startOfWeek)
        d.setDate(startOfWeek.getDate() + i)
        return d
    })

    const hours = Array.from({ length: 24 }).map((_, i) => i)

    // Current time indicator position
    const currentHour = now.getHours()
    const currentMinute = now.getMinutes()
    const timeSliderTop = (currentHour * 60 + currentMinute) * (100 / (24 * 60)) // Percentage of total height (24h)

    const timeGridRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        if (timeGridRef.current) {
            const hourHeight = 80 // We set each hour block to 80px min
            timeGridRef.current.scrollTop = Math.max(0, currentHour * hourHeight - 200)
        }
    }, [currentHour])

    return (
        <div className="flex flex-col h-full bg-[#05080f]">
            {/* Top Toolbar */}
            <header className="flex-shrink-0 flex items-center justify-between px-6 py-4 border-b border-[#2a2e37]">
                <div className="flex items-center gap-4">
                    <h1 className="text-xl font-bold tracking-wide text-gray-100 flex items-center gap-2">
                        <CalendarIcon className="w-5 h-5 text-cyan-400" />
                        Calendar
                    </h1>
                </div>

                <div className="flex items-center gap-4">
                    {/* Search */}
                    <div className="relative hidden md:block">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                        <input
                            type="text"
                            placeholder="Search anything"
                            className="bg-[#121620] border border-[#2a2e37] rounded-lg pl-9 pr-4 py-2 text-sm text-gray-200 outline-none focus:border-cyan-500/50 transition-colors w-64"
                        />
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center">
                            <span className="text-[10px] font-mono bg-[#2a2e37] text-gray-400 px-1.5 py-0.5 rounded">⌘K</span>
                        </div>
                    </div>

                    {/* Filter Tabs */}
                    <div className="hidden lg:flex items-center bg-[#121620] rounded-lg p-1 border border-[#2a2e37]">
                        {['All Event', 'Shared', 'Public', 'Archived'].map((tab, i) => (
                            <button key={tab} className={cn(
                                "px-3 py-1.5 text-xs font-medium rounded-md transition-colors",
                                i === 0 ? "bg-[#2a2e37] text-white" : "text-gray-400 hover:text-gray-200"
                            )}>
                                {tab}
                            </button>
                        ))}
                    </div>
                </div>
            </header>

            <div className="flex flex-1 overflow-hidden">
                {/* Left Sidebar Pane (Mini Calendar matching image) */}
                <aside className="w-[320px] flex-shrink-0 border-r border-[#2a2e37] bg-[var(--sidebar-chrome-bg)] overflow-y-auto hidden md:block p-6 custom-scrollbar">
                    {/* Date Callout */}
                    <div className="flex items-start gap-4 mb-8">
                        <div className="bg-cyan-500/10 border border-cyan-500/20 rounded-xl overflow-hidden flex flex-col items-center min-w-[60px]">
                            <div className="bg-cyan-500 text-[10px] uppercase font-black tracking-widest text-[#05080f] w-full text-center py-1">
                                {monthOnlyName}
                            </div>
                            <div className="text-2xl font-black text-cyan-400 py-1 bg-[#0d1117] w-full text-center border-t border-cyan-500/20">
                                {selectedDate.getDate()}
                            </div>
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-gray-100">
                                {selectedDate.toLocaleString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                            </h2>
                            <p className="text-sm text-gray-500 font-medium">
                                {selectedDate.toLocaleString('en-US', { weekday: 'long' })}
                            </p>
                        </div>
                    </div>

                    {/* Mini Calendar Monthly View */}
                    <div className="mb-10 bg-[#0d1117]/80 rounded-xl p-4 border border-[#2a2e37]/50 shadow-lg">
                        <div className="flex items-center justify-between mb-4">
                            <button onClick={handlePrevMonth} className="text-gray-500 hover:text-cyan-400"><ChevronLeft className="w-4 h-4" /></button>
                            <span className="text-sm font-bold text-gray-200 uppercase tracking-widest">{monthName}</span>
                            <button onClick={handleNextMonth} className="text-gray-500 hover:text-cyan-400"><ChevronRight className="w-4 h-4" /></button>
                        </div>
                        <div className="grid grid-cols-7 mb-2">
                            {['SU', 'MO', 'TU', 'WE', 'TH', 'FR', 'SA'].map(d => (
                                <div key={d} className="text-[9px] font-bold text-gray-500 text-center uppercase tracking-wider">{d}</div>
                            ))}
                        </div>
                        <div className="grid grid-cols-7 gap-y-2">
                            {gridCells.map((cell, idx) => (
                                <div key={idx} className="flex justify-center">
                                    <button
                                        onClick={() => setSelectedDate(new Date(cell.y, cell.m, cell.d))}
                                        className={cn(
                                            "w-7 h-7 flex items-center justify-center rounded-full text-xs font-semibold transition-all hover:bg-cyan-500/20",
                                            cell.isCurrentMonth ? "text-gray-300" : "text-gray-600 hover:text-gray-400",
                                            isToday(cell.d, cell.m, cell.y) && !isSelected(cell.d, cell.m, cell.y) && "ring-1 ring-cyan-500 text-cyan-400",
                                            isSelected(cell.d, cell.m, cell.y) && "bg-cyan-500 text-[#05080f] shadow-[0_0_10px_rgba(34,211,238,0.3)]",
                                            cell.isCurrentMonth && missionsByDay[cell.d]?.length > 0 && !isSelected(cell.d, cell.m, cell.y) && "relative after:content-[''] after:absolute after:bottom-0.5 after:left-1/2 after:-translate-x-1/2 after:w-1 after:h-1 after:rounded-full after:bg-cyan-500/60"
                                        )}
                                    >
                                        {cell.d}
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Missions for selected date */}
                    <div>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-sm font-bold text-gray-200 uppercase tracking-wider">Scheduled Missions</h3>
                            {missionsForSelectedDate.length > 0 && (
                                <span className="text-[10px] text-cyan-400 font-bold bg-cyan-500/10 px-2 py-0.5 rounded-full ring-1 ring-cyan-500/20">
                                    {missionsForSelectedDate.length} Active
                                </span>
                            )}
                        </div>

                        <div className="space-y-3">
                            {missionsForSelectedDate.length === 0 ? (
                                <div className="text-center py-6 border border-dashed border-[#2a2e37] rounded-xl text-gray-600 text-xs shadow-inner bg-[#0d1117]/30">
                                    No missions scheduled for this date.
                                </div>
                            ) : (
                                missionsForSelectedDate.map(mission => {
                                    const prio = PRIORITY_CONFIG[mission.priority]
                                    const stat = STATUS_CONFIG[mission.status]
                                    return (
                                        <div key={mission.id} className="bg-[#0d1117] border border-[#2a2e37] rounded-xl p-3 hover:border-cyan-500/30 transition-colors group cursor-pointer shadow-sm">
                                            <div className="flex items-center gap-2 mb-2">
                                                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: prio.accent }}></div>
                                                <span className="text-xs font-bold text-gray-300 line-clamp-1 flex-1">{mission.title}</span>
                                            </div>
                                            <p className="text-[10px] text-gray-500 line-clamp-2 mb-3">
                                                {mission.description || "No description provided."}
                                            </p>
                                            <div className="flex items-center justify-between text-[10px] border-t border-[#2a2e37]/50 pt-2 relative">
                                                <div className="flex items-center gap-1.5 text-gray-400">
                                                    <Clock className="w-3 h-3" />
                                                    {formatDuration(mission.estimated_minutes) || "TBD"}
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    {mission.meet_url && (
                                                        <a
                                                            href={mission.meet_url}
                                                            target="_blank"
                                                            rel="noreferrer"
                                                            className="text-cyan-400 hover:text-cyan-300 bg-cyan-500/10 p-1 rounded-md transition-colors"
                                                            onClick={(e) => e.stopPropagation()}
                                                            title="Meeting Link"
                                                        >
                                                            <ExternalLink className="w-3 h-3" />
                                                        </a>
                                                    )}
                                                    <div className={cn("px-1.5 py-0.5 rounded uppercase font-bold text-[9px]", stat.darkColor)}>
                                                        {stat.label}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    )
                                })
                            )}
                        </div>
                    </div>
                </aside>

                {/* Right Main Column (Weekly Grid) */}
                <main className="flex-1 flex flex-col bg-[#05080f] overflow-hidden">
                    {/* Header Controls */}
                    <div className="px-6 py-4 flex items-center justify-between border-b border-[#2a2e37]">
                        <div className="flex items-center gap-3">
                            <button
                                onClick={handleToday}
                                className="px-3 py-1.5 bg-[#121620] border border-[#2a2e37] rounded-lg text-xs font-bold text-gray-300 hover:text-cyan-400 hover:border-cyan-500/30 transition-all"
                            >
                                Today
                            </button>
                            <div className="flex items-center bg-[#121620] border border-[#2a2e37] rounded-lg p-0.5">
                                <button onClick={() => {
                                    const d = new Date(selectedDate)
                                    d.setDate(d.getDate() - 7)
                                    setSelectedDate(d)
                                }} className="p-1.5 text-gray-500 hover:text-cyan-400 transition-colors rounded-md hover:bg-[#2a2e37]/50">
                                    <ChevronLeft className="w-4 h-4" />
                                </button>
                                <button onClick={() => {
                                    const d = new Date(selectedDate)
                                    d.setDate(d.getDate() + 7)
                                    setSelectedDate(d)
                                }} className="p-1.5 text-gray-500 hover:text-cyan-400 transition-colors rounded-md hover:bg-[#2a2e37]/50">
                                    <ChevronRight className="w-4 h-4" />
                                </button>
                            </div>
                            <h2 className="text-lg font-black text-gray-100 ml-2 tracking-wide">
                                {startOfWeek.toLocaleString('en-US', { month: 'long', year: 'numeric' })}
                            </h2>
                        </div>

                        <div className="flex items-center gap-3">
                            <div className="hidden sm:flex bg-[#121620] border border-[#2a2e37] rounded-lg p-1 text-xs font-medium">
                                <button
                                    onClick={() => setViewMode('monthly')}
                                    className={cn("px-3 py-1.5 rounded-md transition-colors", viewMode === 'monthly' ? "bg-[#2a2e37] text-white" : "text-gray-500 hover:text-gray-300")}
                                >
                                    Monthly View
                                </button>
                                <button
                                    onClick={() => setViewMode('weekly')}
                                    className={cn("px-3 py-1.5 rounded-md transition-colors", viewMode === 'weekly' ? "bg-[#2a2e37] text-white" : "text-gray-500 hover:text-gray-300")}
                                >
                                    Weekly View
                                </button>
                            </div>
                        </div>
                    </div>

                    {viewMode === 'monthly' ? (
                        <>
                            {/* Monthly Headers */}
                            <div className="grid grid-cols-7 border-y border-[#2a2e37] bg-[var(--sidebar-chrome-bg)] flex-shrink-0">
                                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
                                    <div key={d} className="py-2.5 text-center text-[10px] font-bold text-gray-500 uppercase tracking-widest border-r border-[#2a2e37]/50 last:border-0">
                                        {d}
                                    </div>
                                ))}
                            </div>

                            {/* Monthly Grid */}
                            <div className="flex-1 overflow-y-auto custom-scrollbar bg-[#05080f]">
                                <div className="grid grid-cols-7 auto-rows-[minmax(120px,1fr)]">
                                    {gridCells.map((cell, idx) => {
                                        const isSelectedDay = isSelected(cell.d, cell.m, cell.y) && cell.isCurrentMonth
                                        const isTodayDay = isToday(cell.d, cell.m, cell.y) && cell.isCurrentMonth
                                        const cellMissions = cell.isCurrentMonth ? (missionsByDay[cell.d] || []) : []

                                        return (
                                            <div
                                                key={idx}
                                                onClick={() => cell.isCurrentMonth && setSelectedDate(new Date(cell.y, cell.m, cell.d))}
                                                className={cn(
                                                    "border-r border-b border-[#2a2e37]/60 p-2 flex flex-col gap-1 transition-colors relative group",
                                                    !cell.isCurrentMonth && "bg-[#090b14]/40 opacity-50",
                                                    cell.isCurrentMonth && "cursor-pointer hover:bg-[#121620]/40",
                                                    isSelectedDay && "bg-cyan-500/5 hover:bg-cyan-500/10"
                                                )}
                                            >
                                                <div className="flex items-center justify-between mb-1">
                                                    <span className={cn(
                                                        "text-xs font-bold w-6 h-6 flex items-center justify-center rounded-full transition-all",
                                                        isTodayDay
                                                            ? "bg-cyan-500 text-[#05080f] shadow-[0_0_10px_rgba(34,211,238,0.4)]"
                                                            : cell.isCurrentMonth ? "text-gray-300" : "text-gray-600"
                                                    )}>
                                                        {cell.d}
                                                    </span>
                                                    {cellMissions.length > 0 && (
                                                        <span className="text-[9px] font-bold text-gray-500 bg-[#121620] px-1.5 py-0.5 rounded border border-[#2a2e37]">
                                                            {cellMissions.length}
                                                        </span>
                                                    )}
                                                </div>

                                                <div className="flex flex-col gap-1.5 overflow-hidden">
                                                    {cellMissions.slice(0, 4).map(mission => {
                                                        const prio = PRIORITY_CONFIG[mission.priority]
                                                        const isCompleted = mission.status === 'completed' || mission.status === 'archived'

                                                        return (
                                                            <div
                                                                key={mission.id}
                                                                className={cn(
                                                                    "px-2 py-1 rounded text-[10px] font-bold truncate transition-all relative border-l-2",
                                                                    isCompleted ? "opacity-40 line-through bg-[#121620] text-gray-400 border-gray-600"
                                                                        : "bg-[#121620] text-gray-200 hover:bg-[#1c2233] border-cyan-500/50"
                                                                )}
                                                                style={{
                                                                    borderLeftColor: !isCompleted ? prio.accent : undefined
                                                                }}
                                                            >
                                                                {mission.title}
                                                            </div>
                                                        )
                                                    })}
                                                    {cellMissions.length > 4 && (
                                                        <div className="text-[10px] font-bold text-gray-500 pl-1 mt-0.5">
                                                            + {cellMissions.length - 4} more
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>
                        </>
                    ) : (
                        <>
                            {/* Weekly Headers */}
                            <div className="flex border-b border-[#2a2e37] bg-[var(--sidebar-chrome-bg)] flex-shrink-0">
                                <div className="w-16 flex-shrink-0 border-r border-[#2a2e37]/50"></div>
                                <div className="flex-1 grid grid-cols-7">
                                    {weekDays.map((d, i) => {
                                        const isCurrentDay = isToday(d.getDate(), d.getMonth(), d.getFullYear())
                                        const isSelDay = isSelected(d.getDate(), d.getMonth(), d.getFullYear())
                                        return (
                                            <div
                                                key={i}
                                                onClick={() => setSelectedDate(d)}
                                                className={cn(
                                                    "py-3 flex flex-col items-center justify-center border-r border-[#2a2e37]/50 last:border-0 cursor-pointer transition-colors",
                                                    isSelDay ? "bg-[#121620]/80" : "hover:bg-[#121620]/40"
                                                )}
                                            >
                                                <span className={cn(
                                                    "text-[10px] font-bold uppercase tracking-widest mb-1",
                                                    isCurrentDay ? "text-cyan-400" : "text-gray-500"
                                                )}>
                                                    {d.toLocaleString('en-US', { weekday: 'short' })}
                                                </span>
                                                <span className={cn(
                                                    "text-lg font-black w-8 h-8 flex items-center justify-center rounded-full transition-all",
                                                    isCurrentDay ? "bg-cyan-500 text-[#05080f] shadow-[0_0_10px_rgba(34,211,238,0.4)]" : "text-gray-200"
                                                )}>
                                                    {d.getDate()}
                                                </span>
                                            </div>
                                        )
                                    })}
                                </div>
                            </div>

                            {/* Calendar Grid (Weekly Timeline) */}
                            <div className="flex-1 overflow-y-auto custom-scrollbar relative" ref={timeGridRef}>
                                <div className="flex relative" style={{ height: '1440px' }}> {/* 24 hours * 60px per hour */}

                                    {/* Time Axis (Left) */}
                                    <div className="w-16 flex-shrink-0 border-r border-[#2a2e37]/50 bg-[#090b14]/30 relative z-10 flex flex-col">
                                        {hours.map(hour => (
                                            <div
                                                key={hour}
                                                className="h-[60px] border-b border-[#2a2e37]/30 flex justify-center -mt-3 relative"
                                            >
                                                {/* Don't show strictly 12 AM for index 0 to avoid crowding the top border, or show it slightly lower */}
                                                <span className="text-[10px] font-bold text-gray-500 bg-[#090b14]/30 px-1 absolute -top-1">
                                                    {hour === 0 ? '' : hour < 12 ? `${hour} AM` : hour === 12 ? '12 PM' : `${hour - 12} PM`}
                                                </span>
                                            </div>
                                        ))}
                                    </div>

                                    {/* Main Grid area */}
                                    <div className="flex-1 grid grid-cols-7 relative">
                                        {/* Horizontal Grid Lines */}
                                        <div className="absolute inset-0 flex flex-col pointer-events-none z-0">
                                            {hours.map(hour => (
                                                <div key={hour} className="h-[60px] border-b border-[#2a2e37]/30 border-dashed w-full" />
                                            ))}
                                        </div>

                                        {/* Current Time Slider */}
                                        <div
                                            className="absolute left-0 right-0 h-[2px] bg-cyan-500 shadow-[0_0_8px_rgba(34,211,238,0.8)] z-20 pointer-events-none transition-all duration-1000"
                                            style={{ top: `${timeSliderTop}%` }}
                                        >
                                            <div className="absolute -left-1.5 -top-1 w-2.5 h-2.5 rounded-full bg-cyan-400 shadow-[0_0_8px_rgba(34,211,238,1)]"></div>
                                        </div>

                                        {/* Day Columns */}
                                        {weekDays.map((day, dayIndex) => {
                                            const dayMissions = missions.filter(m => {
                                                if (!m.deadline) return false
                                                const md = new Date(m.deadline)
                                                return md.getFullYear() === day.getFullYear() && md.getMonth() === day.getMonth() && md.getDate() === day.getDate()
                                            })

                                            return (
                                                <div key={dayIndex} className="border-r border-[#2a2e37]/50 relative flex flex-col z-10 hover:bg-[#121620]/10 transition-colors">
                                                    {dayMissions.map((mission, idx) => {
                                                        const md = new Date(mission.deadline!)
                                                        const hasTime = mission.deadline!.includes('T') || mission.deadline!.includes(' ')
                                                        const h = hasTime ? md.getHours() : 9 + (idx % 8) // default to 9AM spread out if no time
                                                        const min = hasTime ? md.getMinutes() : 0

                                                        const duration = mission.estimated_minutes || 60
                                                        const topPercent = ((h * 60 + min) / (24 * 60)) * 100
                                                        const heightPercent = (duration / (24 * 60)) * 100

                                                        const prio = PRIORITY_CONFIG[mission.priority]
                                                        const isCompleted = mission.status === 'completed' || mission.status === 'archived'

                                                        return (
                                                            <div
                                                                key={mission.id}
                                                                className={cn(
                                                                    "absolute left-1 right-1 rounded-md border p-1.5 overflow-hidden hover:z-30 hover:shadow-lg transition-all cursor-pointer backdrop-blur-sm",
                                                                    isCompleted ? "bg-[#121620]/60 border-gray-700/50" : "bg-[#121620]/90 border-cyan-500/30 hover:border-cyan-400 shadow-[0_4px_12px_rgba(0,0,0,0.5)]"
                                                                )}
                                                                style={{
                                                                    top: `${topPercent}%`,
                                                                    height: `${Math.max(4, heightPercent)}%`, // min height to be readable
                                                                    minHeight: '40px',
                                                                    borderLeftWidth: '3px',
                                                                    borderLeftColor: isCompleted ? '#4b5563' : prio.accent
                                                                }}
                                                            >
                                                                <div className={cn(
                                                                    "text-xs font-bold leading-tight line-clamp-2",
                                                                    isCompleted ? "line-through text-gray-500" : "text-gray-200"
                                                                )}>
                                                                    {mission.title}
                                                                </div>
                                                                <div className="flex items-center justify-between mt-1">
                                                                    <div className="text-[9px] text-gray-500 flex items-center gap-1">
                                                                        <Clock size={10} />
                                                                        {h === 0 ? '12:00 AM' : h < 12 ? `${h}:${min.toString().padStart(2, '0')} AM` : h === 12 ? `12:${min.toString().padStart(2, '0')} PM` : `${h - 12}:${min.toString().padStart(2, '0')} PM`} ({duration}m)
                                                                    </div>
                                                                    {mission.meet_url && (
                                                                        <a
                                                                            href={mission.meet_url}
                                                                            target="_blank"
                                                                            rel="noreferrer"
                                                                            className="text-cyan-400 hover:text-cyan-300 bg-cyan-500/10 p-0.5 rounded transition-colors"
                                                                            onClick={(e) => e.stopPropagation()}
                                                                            title="Join Meeting"
                                                                        >
                                                                            <ExternalLink size={10} />
                                                                        </a>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        )
                                                    })}
                                                </div>
                                            )
                                        })}
                                    </div>
                                </div>
                            </div>
                        </>
                    )}
                </main>
            </div>
        </div>
    )
}
