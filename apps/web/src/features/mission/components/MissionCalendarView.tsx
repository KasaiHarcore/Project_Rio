"use client"

import React, { useMemo } from 'react'
import {
    ChevronLeft,
    ChevronRight,
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import {
    type Mission,
    isOverdue,
    parseDeadline,
} from '@/features/mission/types'

/* ═══════════════════════════════════════════════════════════════════
 * CALENDAR VIEW — Month grid showing missions by deadline
 * (inline calendar used in the MissionView shell, distinct from
 *  the standalone CalendarView.tsx)
 * ═══════════════════════════════════════════════════════════════════ */

interface MissionCalendarViewProps {
    missions: Mission[]
    calendarDate: Date
    setCalendarDate: (d: Date) => void
    onStatusCycle: (m: Mission) => void
}

export function MissionCalendarView({ missions, calendarDate, setCalendarDate, onStatusCycle }: MissionCalendarViewProps) {
    const year = calendarDate.getFullYear()
    const month = calendarDate.getMonth()
    const firstDay = new Date(year, month, 1).getDay()
    const daysInMonth = new Date(year, month + 1, 0).getDate()
    const today = new Date()
    const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`

    const monthName = calendarDate.toLocaleString('en-US', { month: 'long', year: 'numeric' })

    // Group missions by deadline day
    const missionsByDay = useMemo(() => {
        const map: Record<string, Mission[]> = {}
        for (const m of missions) {
            if (!m.deadline) continue
            const d = parseDeadline(m.deadline)
            if (d.getFullYear() === year && d.getMonth() === month) {
                const key = String(d.getDate())
                if (!map[key]) map[key] = []
                map[key].push(m)
            }
        }
        return map
    }, [missions, year, month])

    const prevMonth = () => setCalendarDate(new Date(year, month - 1, 1))
    const nextMonth = () => setCalendarDate(new Date(year, month + 1, 1))

    const days: (number | null)[] = []
    for (let i = 0; i < firstDay; i++) days.push(null)
    for (let d = 1; d <= daysInMonth; d++) days.push(d)

    return (
        <div className={cn("rounded-2xl border overflow-hidden mb-6", "border-rose-900/20 bg-[#0d1117]/60")}>
            {/* Month nav */}
            <div className={cn("flex items-center justify-between px-5 py-3", "bg-slate-900")}>
                <button onClick={prevMonth} className={cn("p-1.5 rounded-lg transition-colors", "text-slate-400 hover:bg-slate-800")}>
                    <ChevronLeft size={18} />
                </button>
                <h3 className={cn("text-sm font-black uppercase tracking-wider", "text-slate-300")}>
                    {monthName}
                </h3>
                <button onClick={nextMonth} className={cn("p-1.5 rounded-lg transition-colors", "text-slate-400 hover:bg-slate-800")}>
                    <ChevronRight size={18} />
                </button>
            </div>

            {/* Weekday headers */}
            <div className="grid grid-cols-7 text-center">
                {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
                    <div key={d} className={cn("text-[10px] font-bold uppercase py-2", "text-slate-600")}>
                        {d}
                    </div>
                ))}
            </div>

            {/* Day cells */}
            <div className="grid grid-cols-7">
                {days.map((day, i) => {
                    if (day === null) return <div key={`empty-${i}`} className={cn("min-h-[90px] border-t", "border-slate-800")} />
                    const dayStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
                    const isToday = dayStr === todayStr
                    const dayMissions = missionsByDay[String(day)] || []
                    return (
                        <div
                            key={day}
                            className={cn(
                                "min-h-[90px] border-t p-1.5 transition-colors",
                                "border-slate-800",
                                isToday && "bg-rose-900/10"
                            )}
                        >
                            <span className={cn(
                                "text-xs font-bold block mb-1",
                                isToday
                                    ? "text-rose-400"
                                    : "text-slate-500"
                            )}>
                                {day}
                            </span>
                            {dayMissions.slice(0, 3).map((m) => {
                                const overdue = isOverdue(m)
                                return (
                                    <button
                                        key={m.id}
                                        onClick={() => onStatusCycle(m)}
                                        className={cn(
                                            "block w-full text-left text-[10px] font-semibold px-1.5 py-0.5 rounded mb-0.5 truncate transition-colors",
                                            overdue
                                                ? "bg-red-900/30 text-red-400"
                                                : m.status === 'completed'
                                                    ? "bg-emerald-900/30 text-emerald-400 line-through opacity-60"
                                                    : "bg-rose-900/20 text-rose-400 hover:bg-rose-900/30"
                                        )}
                                    >
                                        {m.title}
                                    </button>
                                )
                            })}
                            {dayMissions.length > 3 && (
                                <span className={cn("text-[9px] font-bold", "text-slate-600")}>
                                    +{dayMissions.length - 3} more
                                </span>
                            )}
                        </div>
                    )
                })}
            </div>

            {/* Missions without deadlines note */}
            {missions.some((m) => !m.deadline) && (
                <div className={cn("px-5 py-3 text-xs border-t", "border-slate-800 text-slate-600")}>
                    {missions.filter((m) => !m.deadline).length} mission(s) without deadlines — assign dates to see them on the calendar.
                </div>
            )}
        </div>
    )
}
