"use client"

import dynamic from 'next/dynamic'
const KnowledgeView = dynamic(
  () => import('@/features/knowledge/components/KnowledgeView').then((m) => m.KnowledgeView),
)

export default function KnowledgePage() {
  return <KnowledgeView />
}
