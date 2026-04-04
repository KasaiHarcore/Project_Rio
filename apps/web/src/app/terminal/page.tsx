"use client"

import dynamic from 'next/dynamic'
const OSControlView = dynamic(
  () => import("@/features/os-control/components/OSControlView").then((m) => m.OSControlView),
)

export default function TerminalPage() {
  return <OSControlView />
}
