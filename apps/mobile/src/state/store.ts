import { useState } from 'react';

// Minimal placeholder store (can replace with Zustand/Recoil later)
export function useBoolean(initial = false): [boolean, () => void, () => void] {
  const [v, setV] = useState(initial);
  return [v, () => setV(true), () => setV(false)];
}
