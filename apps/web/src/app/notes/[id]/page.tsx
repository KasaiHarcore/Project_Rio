"use client"

import React, { Suspense } from 'react'
import { DashboardLayout } from "@/components/layout/dashboard-layout"
import { Loader2 } from 'lucide-react'
import { NotesPageContent } from '../page'

export default function NoteDetailPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = React.use(params)
    return (
        <Suspense fallback={
            <DashboardLayout>
                <div className="flex-1 flex items-center justify-center">
                    <Loader2 className="h-6 w-6 animate-spin text-rose-500" />
                </div>
            </DashboardLayout>
        }>
            <NotesPageContent initialNoteId={id} />
        </Suspense>
    )
}
