export type MissionStatus = 'DRAFT' | 'ACTIVE' | 'COMPLETED' | 'ARCHIVED';

export type MissionPriority = 'LOW' | 'NORMAL' | 'CRITICAL';

export interface Mission {
  id: string;
  title: string;
  description: string;
  status: MissionStatus;
  priority: MissionPriority;
  createdAt: Date;
  updatedAt: Date;
  tags: string[];
  progress?: number; // 0-100
}

export const MOCK_MISSIONS: Mission[] = [
  {
    id: 'm-001',
    title: 'Daily Report Analysis',
    description: 'Compile and analyze the daily activity logs from the Schale Database.',
    status: 'ACTIVE',
    priority: 'NORMAL',
    createdAt: new Date(),
    updatedAt: new Date(),
    tags: ['Routine', 'Data'],
    progress: 45
  },
  {
    id: 'm-002',
    title: 'System Optimization Protocol',
    description: 'Review and optimize the RAG retrieval pipeline for better latency.',
    status: 'DRAFT',
    priority: 'CRITICAL',
    createdAt: new Date(),
    updatedAt: new Date(),
    tags: ['Dev', 'Backend'],
    progress: 0
  },
  {
    id: 'm-003',
    title: 'Archive Organization',
    description: 'Sort and tag the recent uploaded artifacts for easier retrieval.',
    status: 'COMPLETED',
    priority: 'LOW',
    createdAt: new Date(),
    updatedAt: new Date(),
    tags: ['Maintenance'],
    progress: 100
  }
];
