"use client"

import dynamic from 'next/dynamic'
const ArtifactsView = dynamic(
  () => import('@/features/artifacts/components/ArtifactsView').then((m) => m.ArtifactsView),
)

export default function ArtifactsPage() {
  return <ArtifactsView />
}
