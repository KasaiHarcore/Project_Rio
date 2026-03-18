export type ResponseContext = {
  mood: unknown
  energy: number
  affinity: unknown
  relationshipTier: unknown
  streakDays: number
  sessionDuration: number
  idleTime: number
  isLateNight: boolean
  isWeekend: boolean
  eventCount: number
  situationType:
    | "intervention_45min"
    | "intervention_90min"
    | "intervention_120min"
    | "idle_check"
    | "late_night_warning"
    | "deadline_pressure"
    | "re_engagement"
  additionalInfo?: unknown
}

const RESPONSES: Record<ResponseContext["situationType"], string[]> = {
  intervention_45min: [
    "You've been working for 45 minutes. Maybe take a short break?",
    "Hey, stretch a bit! You've been at it for a while.",
  ],
  intervention_90min: [
    "90 minutes already! Your focus is impressive, but rest is important too.",
    "Time for a proper break — you've earned it after 90 minutes.",
  ],
  intervention_120min: [
    "Two hours straight... Please take a break, okay?",
    "Working for 2 hours without a break isn't great for you. Let's pause.",
  ],
  idle_check: [
    "Still there? Let me know if you need anything!",
    "Seems like you've been away. Welcome back whenever you're ready!",
  ],
  late_night_warning: [
    "It's getting late... don't forget to rest!",
    "Burning the midnight oil? Take care of yourself.",
  ],
  deadline_pressure: [
    "Deadline approaching — you've got this! Stay focused.",
    "Crunch time! Let me know how I can help.",
  ],
  re_engagement: [
    "Welcome back! Ready to pick up where we left off?",
    "Good to see you again. Let's get back to work!",
  ],
}

/**
 * Generates a contextual Rio response based on the intervention situation.
 */
export async function generateRioResponse(
  context: ResponseContext
): Promise<{ message: string }> {
  const pool = RESPONSES[context.situationType] ?? RESPONSES.idle_check
  const message = pool[Math.floor(Math.random() * pool.length)]
  return { message }
}
