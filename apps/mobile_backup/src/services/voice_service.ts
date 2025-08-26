export interface STTResult { text: string; confidence?: number; }

export async function transcribeAudio(_pcm: ArrayBuffer): Promise<STTResult> {
  // Placeholder: integrate native module or on-device model
  return { text: 'transcribed placeholder', confidence: 0.8 };
}
