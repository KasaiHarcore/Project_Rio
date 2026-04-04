"use client"

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { PageTransition } from "@/components/layout/page-transition"
import { AnimatePresence } from 'framer-motion'
import {
    Loader2,
    Plus,
    Target,
} from 'lucide-react'
import { cn } from '@/shared/lib/utils'
import { useMissionStore } from '@/features/mission/store'
import {
    type Mission,
    type MissionStatus,
    isOverdue,
} from '@/features/mission/types'
import { toast } from '@/shared/hooks/use-toast'
import { useAffinityTracker } from '@/features/emotional/hooks/use-affinity-tracker'

import { ViewSwitcher, TabButton, StatsBar, FilterBar } from './MissionStatBar'
import { MissionBoardView } from './MissionBoardView'
import { MissionTableView } from './MissionTableView'
import { MissionCalendarView } from './MissionCalendarView'
import { CreateMissionModal } from './CreateMissionModal'

/* ═══════════════════════════════════════════════════════════════════
 * Main Page
 * ═══════════════════════════════════════════════════════════════════ */
type TabFilter = 'active' | 'completed' | 'all'

export function MissionView() {
    const {
        missions, stats, loading,
        fetchMissions, fetchStats, createMission, updateMission, deleteMission, toggleStep,
        viewMode, setViewMode,
        filterCategory, setFilterCategory,
        filterPriority, setFilterPriority,
    } = useMissionStore()

    const { recordMissionStep } = useAffinityTracker()

    const [activeTab, setActiveTab] = useState<TabFilter>('active')
    const [showCreateForm, setShowCreateForm] = useState(false)
    const [expandedMission, setExpandedMission] = useState<string | null>(null)
    const [showFilters, setShowFilters] = useState(false)
    const [calendarDate, setCalendarDate] = useState(new Date())

    useEffect(() => {
        fetchMissions()
        fetchStats()
    }, [fetchMissions, fetchStats])

    // Filter missions by tab + filters
    const filteredMissions = useMemo(() => {
        let list = missions
        if (activeTab === 'active') list = list.filter((m) => m.status === 'active' || m.status === 'draft')
        else if (activeTab === 'completed') list = list.filter((m) => m.status === 'completed' || m.status === 'archived')
        if (filterCategory) list = list.filter((m) => m.category === filterCategory)
        if (filterPriority) list = list.filter((m) => m.priority === filterPriority)
        return list
    }, [missions, activeTab, filterCategory, filterPriority])

    // Stats
    const totalActive = stats?.active ?? missions.filter((m) => m.status === 'active').length
    const totalCompleted = stats?.completed ?? missions.filter((m) => m.status === 'completed').length
    const totalOverdue = stats?.overdue ?? missions.filter(isOverdue).length
    const categories = stats?.categories ?? []
    const overallProgress = missions.length > 0
        ? Math.round(missions.reduce((sum, m) => sum + m.progress, 0) / missions.length)
        : 0

    const handleStatusCycle = useCallback(async (mission: Mission) => {
        const nextStatus: Record<MissionStatus, MissionStatus> = {
            draft: 'active', active: 'completed', completed: 'archived', archived: 'active',
        }
        await updateMission(mission.id, { status: nextStatus[mission.status] })
        toast({ title: `Mission → ${nextStatus[mission.status].toUpperCase()}` })
    }, [updateMission])

    const handleDelete = useCallback(async (id: string) => {
        const ok = await deleteMission(id)
        if (ok) toast({ title: 'Mission deleted' })
    }, [deleteMission])

    const handleToggleStep = useCallback(async (missionId: string, stepIdx: number) => {
        const result = await toggleStep(missionId, stepIdx)
        // Award affinity if step was completed (not uncompleted)
        if (result && result.steps[stepIdx]?.done) {
            recordMissionStep()
        }
    }, [toggleStep, recordMissionStep])

    const handleInlineUpdate = useCallback(async (id: string, data: Partial<Mission>) => {
        await updateMission(id, data)
    }, [updateMission])

    return (
        <DashboardLayout>
            <PageTransition className="flex-1 overflow-y-auto p-4 md:p-8">
                {/* Header */}
                <header className="mb-6 flex flex-col lg:flex-row lg:items-end justify-between gap-4">
                    <div>
                        <h1 className="text-lg font-black tracking-widest mb-1 text-page-title">
                            MISSION CONTROL
                        </h1>
                        <p className="text-[10px] font-bold tracking-wider uppercase text-page-subtitle">
                            Plan, schedule, and track your goals — Notion-style.
                        </p>
                    </div>

                    <div className="flex items-center gap-3 flex-wrap">
                        {/* View Switcher */}
                        <ViewSwitcher viewMode={viewMode} setViewMode={setViewMode} />

                        {/* Tab Switcher */}
                        <div className={cn("p-1 rounded-xl flex", "bg-[#0d1117] border border-rose-900/40")}>
                            <TabButton active={activeTab === 'active'} onClick={() => setActiveTab('active')} label="Active" count={totalActive} />
                            <TabButton active={activeTab === 'completed'} onClick={() => setActiveTab('completed')} label="Done" count={totalCompleted} />
                            <TabButton active={activeTab === 'all'} onClick={() => setActiveTab('all')} label="All" count={missions.length} />
                        </div>
                    </div>
                </header>

                {/* Stats Bar */}
                <StatsBar
                    overallProgress={overallProgress}
                    totalActive={totalActive}
                    totalCompleted={totalCompleted}
                    totalOverdue={totalOverdue}
                    onCreateClick={() => setShowCreateForm(true)}
                />

                {/* Filter Bar */}
                <FilterBar
                    showFilters={showFilters}
                    setShowFilters={setShowFilters}
                    filterCategory={filterCategory}
                    setFilterCategory={setFilterCategory}
                    filterPriority={filterPriority}
                    setFilterPriority={setFilterPriority}
                    categories={categories}
                />

                {/* Loading state */}
                {loading && missions.length === 0 && (
                    <div className="flex items-center justify-center py-20">
                        <Loader2 className={cn("w-8 h-8 animate-spin", "text-rose-500")} />
                    </div>
                )}

                {/* Empty state */}
                {!loading && filteredMissions.length === 0 && (
                    <div className={cn("text-center py-16", "text-slate-500")}>
                        <Target className="w-16 h-16 mx-auto mb-4 opacity-30" />
                        <p className="text-lg font-bold mb-1">No missions yet</p>
                        <p className="text-sm mb-4">Create one or let the agent generate missions from your conversations.</p>
                        <button
                            onClick={() => setShowCreateForm(true)}
                            className={cn(
                                "px-6 py-2.5 rounded-xl font-bold text-sm inline-flex items-center gap-2",
                                "bg-rose-600 text-white hover:bg-rose-700"
                            )}
                        >
                            <Plus size={16} /> Create First Mission
                        </button>
                    </div>
                )}

                {/* ── VIEW RENDERER ── */}
                {filteredMissions.length > 0 && (
                    <>
                        {viewMode === 'board' && (
                            <MissionBoardView
                                missions={filteredMissions}
                                expandedMission={expandedMission}
                                setExpandedMission={setExpandedMission}
                                onStatusCycle={handleStatusCycle}
                                onDelete={handleDelete}
                                onToggleStep={handleToggleStep}
                                onUpdate={handleInlineUpdate}
                            />
                        )}
                        {viewMode === 'table' && (
                            <MissionTableView
                                missions={filteredMissions}
                                onStatusCycle={handleStatusCycle}
                                onDelete={handleDelete}
                                onUpdate={handleInlineUpdate}
                            />
                        )}
                        {viewMode === 'calendar' && (
                            <MissionCalendarView
                                missions={filteredMissions}
                                calendarDate={calendarDate}
                                setCalendarDate={setCalendarDate}
                                onStatusCycle={handleStatusCycle}
                            />
                        )}
                    </>
                )}

                {/* Create Mission Modal */}
                <AnimatePresence>
                    {showCreateForm && (
                        <CreateMissionModal
                            categories={categories}
                            onClose={() => setShowCreateForm(false)}
                            onCreate={async (data) => {
                                await createMission(data)
                                setShowCreateForm(false)
                                toast({ title: 'Mission created!' })
                            }}
                        />
                    )}
                </AnimatePresence>
            </PageTransition>
        </DashboardLayout>
    )
}
