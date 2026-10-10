export type Outcome = 'accepted' | 'merged' | 'conflict' | 'rejected' | 'resolved' | 'idempotent_replay';

export type MergeStrategy = 'diff3' | 'server_wins' | 'client_wins' | 'manual';

export interface DocumentOut {
  id: number;
  collection: string;
  title: string;
  body: string;
  tags: string[];
  meta: Record<string, any>;
  version: number;
  deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface VersionOut {
  version: number;
  title: string;
  body: string;
  tags: string[];
  meta: Record<string, any>;
  deleted: boolean;
  device_id: string;
  strategy: string;
  outcome: string;
  created_at: string;
}

export interface DeviceOut {
  device_id: string;
  name: string;
  registered_at?: string;
  last_seen?: string;
}

export interface SyncOp {
  device_id: string;
  document_id: number;
  base_version: number;
  title?: string | null;
  body?: string | null;
  tags?: string[] | null;
  meta?: Record<string, any> | null;
  deleted?: boolean | null;
  strategy?: MergeStrategy;
}

export interface SyncResult {
  outcome: Outcome;
  strategy?: string;
  base_version: number;
  current_version: number;
  target_version?: number;
  merged_fields?: string[];
  resolution?: string;
  document?: DocumentOut | null;
  conflicts?: any[] | null;
}
