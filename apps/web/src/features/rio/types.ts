export type { InterventionType, InterventionMessage, InterventionAction, InterventionPreferences } from './store'

/* ── Character definitions ───────────────────────────────────────── */

export type CharacterId = 'rio'

export interface Character {
  id: CharacterId
  name: string
  role: string
  themeColor: string
  accentColor: string
  avatarUrl: string
  greetings: string[]
  systemPromptId: string
}

export const CHARACTERS: Character[] = [
  {
    id: 'rio',
    name: 'Rio Tsukatsuki',
    role: 'Schale System AI',
    themeColor: 'rose',
    accentColor: '#FF3B3B',
    avatarUrl: '/images/avatar.png',
    greetings: ['System online.', 'Awaiting orders, Sensei.', 'I have optimized the schedule.'],
    systemPromptId: 'sys-rio-v1',
  },
]
