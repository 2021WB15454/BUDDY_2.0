export interface VersionedRecord { id: string; updatedAt: number; deleted_at?: number; [k: string]: any; }

export function conflictResolve(local: VersionedRecord, incoming: VersionedRecord): VersionedRecord {
  // Deletion wins over non-deletion
  if (local.deleted_at && !incoming.deleted_at) return local;
  if (incoming.deleted_at && !local.deleted_at) return incoming;
  return (local.updatedAt >= incoming.updatedAt) ? local : incoming;
}
