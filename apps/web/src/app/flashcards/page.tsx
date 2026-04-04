"use client"
import dynamic from 'next/dynamic'
const FlashcardsView = dynamic(
  () => import('@/features/flashcards/components/FlashcardsView').then((m) => m.FlashcardsView),
)
export default function FlashcardsPage() { return <FlashcardsView /> }
