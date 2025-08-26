import { bridgeRegistry } from './bridge_registry';
import { SafetyResult } from './safety_bridge';
import { applySafety } from './safety_bridge';

export interface IntentPayload { type: string; text: string; entities?: any; ts: number; }
export interface NLPRequest { text: string; context?: any; }
export interface NLPResult { intent: IntentPayload; safety: SafetyResult; blocked?: boolean; }

function simpleClassifier(text: string): string {
  const t = text.toLowerCase();
  if (/(navigate|route|drive)/.test(t)) return 'navigation.route';
  if (/(play|music|song)/.test(t)) return 'media.play';
  if (/(remind|reminder)/.test(t)) return 'reminder.create';
  return 'general.chat';
}

export async function detectIntent(req: NLPRequest): Promise<NLPResult> {
  const intent: IntentPayload = { type: simpleClassifier(req.text), text: req.text, ts: Date.now() };
  const safety = await applySafety(intent, req.context);
  return { intent, safety, blocked: !safety.allowed };
}

bridgeRegistry.register('nlp.detect', async (r: NLPRequest) => detectIntent(r), true);
