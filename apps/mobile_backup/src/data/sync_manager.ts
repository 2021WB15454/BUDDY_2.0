import { conflictResolve, VersionedRecord } from './sync_conflict';

export interface SyncItem { id: string; type: string; payload: any; updatedAt: number; tombstone?: boolean; }

export class SyncManager {
  private queue: SyncItem[] = [];
  private flushing = false;
  constructor(private endpointBase: string) {}

  enqueue(item: SyncItem) {
    // merge if existing
    const existingIdx = this.queue.findIndex(q => q.id === item.id && q.type === item.type);
    if (existingIdx >= 0) {
      const merged = conflictResolve(this.queue[existingIdx] as unknown as VersionedRecord, item as unknown as VersionedRecord);
      this.queue[existingIdx] = { ...(merged as any), type: item.type, payload: item.payload };
    } else {
      this.queue.push(item);
    }
  }

  get length() { return this.queue.length; }

  async flush() {
    if (this.flushing || !this.queue.length) return;
    this.flushing = true;
    try {
      // batch by simple grouping
      const batch = this.queue.splice(0, 25);
      await fakeNetworkSend(this.endpointBase + '/sync', batch);
    } finally {
      this.flushing = false;
    }
  }
}

async function fakeNetworkSend(_url: string, _body: any) { /* placeholder */ }

export const syncManager = new SyncManager('https://api.example.com');
