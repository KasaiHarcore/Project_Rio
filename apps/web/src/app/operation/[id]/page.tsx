"use client"

import React from 'react'
import { OperationView } from '@/features/chat/components/OperationView'

export default function OperationThreadPage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = React.use(params)
    return <OperationView initialThreadId={id} />
}
