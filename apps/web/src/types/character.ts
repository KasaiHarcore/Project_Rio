export type CharacterId = 'arona' | 'plana' | 'kei';

export interface Character {
  id: CharacterId;
  name: string;
  role: string;
  themeColor: string; // Tailwind class prefix or hex
  accentColor: string;
  avatarUrl: string; // Path to asset
  greetings: string[];
  systemPromptId: string;
}

export const CHARACTERS: Character[] = [
  {
    id: 'arona',
    name: 'Arona',
    role: 'Schale Main AI',
    themeColor: 'blue',
    accentColor: '#4BA3F5',
    avatarUrl: '/assets/arona_avatar.png', // Placeholder
    greetings: ['Good morning, Sensei!', 'Arona is online!', 'How can I help you today?'],
    systemPromptId: 'sys-arona-v1'
  },
  {
    id: 'plana',
    name: 'Plana',
    role: 'Schale Support AI',
    themeColor: 'rose', // using 'rose' for red/pinkish red
    accentColor: '#FF3B3B',
    avatarUrl: '/assets/plana_avatar.png', // Placeholder
    greetings: ['System online.', 'Awaiting orders, Sensei.', 'I have optimized the schedule.'],
    systemPromptId: 'sys-plana-v1'
  }
];
