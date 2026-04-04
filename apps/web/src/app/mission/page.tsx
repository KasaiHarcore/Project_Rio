"use client"

import dynamic from 'next/dynamic'
const MissionView = dynamic(
  () => import('@/features/mission/components/MissionView').then((m) => m.MissionView),
)

export default function MissionPage() {
  return <MissionView />
}
