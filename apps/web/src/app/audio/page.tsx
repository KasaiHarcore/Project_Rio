"use client"
import dynamic from 'next/dynamic'
const AudioView = dynamic(
  () => import('@/features/audio/components/AudioView').then((m) => m.AudioView),
)
export default function AudioPage() { return <AudioView /> }
