import { conflictResolve } from '@data/sync_conflict';

test('newer updatedAt wins when no deletions', () => {
  const a = { id: '1', updatedAt: 100 } as any;
  const b = { id: '1', updatedAt: 200 } as any;
  expect(conflictResolve(a, b)).toBe(b);
});

test('deletion preserved over non deletion', () => {
  const del = { id: '1', updatedAt: 100, deleted_at: 50 } as any;
  const normal = { id: '1', updatedAt: 200 } as any;
  expect(conflictResolve(del, normal)).toBe(del);
});
