export interface SafetyResult { allowed: boolean; message?: string; speedKmh?: number; }

export async function applySafety(intent: { type: string }, ctx?: any): Promise<SafetyResult> {
  const speed = ctx?.speedKmh ?? 0;
  if (speed > 5 && intent.type === 'general.chat') {
    return { allowed: false, message: 'Action blocked while moving. Use concise commands.', speedKmh: speed };
  }
  return { allowed: true, speedKmh: speed };
}
