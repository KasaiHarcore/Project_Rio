"use client"
import dynamic from 'next/dynamic'
const AutomationsView = dynamic(
  () => import('@/features/automations/components/AutomationsView').then((m) => m.AutomationsView),
)
export default function AutomationsPage() { return <AutomationsView /> }
