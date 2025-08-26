import { voiceModule, VoiceTranscriptionResult } from './voice_module';

export interface STTResult { 
  text: string; 
  confidence?: number; 
  isFinal?: boolean;
}

export class VoiceService {
  private isListening = false;

  async startListening(locale: string = 'en-US'): Promise<void> {
    if (this.isListening) {
      throw new Error('Already listening');
    }

    if (!voiceModule.isReady()) {
      throw new Error('Voice module not ready');
    }

    try {
      await voiceModule.start(locale);
      this.isListening = true;
    } catch (error) {
      console.error('Failed to start voice recognition:', error);
      throw error;
    }
  }

  async stopListening(): Promise<void> {
    if (!this.isListening) {
      return;
    }

    try {
      await voiceModule.stop();
      this.isListening = false;
    } catch (error) {
      console.error('Failed to stop voice recognition:', error);
      throw error;
    }
  }

  async cancelListening(): Promise<void> {
    if (!this.isListening) {
      return;
    }

    try {
      await voiceModule.cancel();
      this.isListening = false;
    } catch (error) {
      console.error('Failed to cancel voice recognition:', error);
      throw error;
    }
  }

  // Set up event listeners for voice recognition
  onTranscription(callback: (result: STTResult) => void): () => void {
    const handler = (result: VoiceTranscriptionResult) => {
      callback({
        text: result.text,
        confidence: result.confidence,
        isFinal: result.isFinal
      });
    };

    voiceModule.on('transcription', handler);
    
    // Return cleanup function
    return () => voiceModule.off('transcription', handler);
  }

  onPartialTranscription(callback: (result: STTResult) => void): () => void {
    const handler = (result: VoiceTranscriptionResult) => {
      callback({
        text: result.text,
        confidence: result.confidence,
        isFinal: result.isFinal
      });
    };

    voiceModule.on('partialTranscription', handler);
    
    // Return cleanup function
    return () => voiceModule.off('partialTranscription', handler);
  }

  onError(callback: (error: any) => void): () => void {
    voiceModule.on('error', callback);
    return () => voiceModule.off('error', callback);
  }

  onStart(callback: () => void): () => void {
    voiceModule.on('start', callback);
    return () => voiceModule.off('start', callback);
  }

  onStop(callback: () => void): () => void {
    voiceModule.on('stop', callback);
    return () => voiceModule.off('stop', callback);
  }

  onVolumeChanged(callback: (volume: number) => void): () => void {
    voiceModule.on('volumeChanged', callback);
    return () => voiceModule.off('volumeChanged', callback);
  }

  // Utility methods
  isRecording(): boolean {
    return this.isListening && voiceModule.isRecording();
  }

  async isAvailable(): Promise<boolean> {
    return await voiceModule.isRecognitionAvailable();
  }

  async getSupportedLocales(): Promise<string[]> {
    return await voiceModule.getSupportedLocales();
  }
}

// Legacy function for backward compatibility
export async function transcribeAudio(_pcm: ArrayBuffer): Promise<STTResult> {
  // This function is deprecated - use VoiceService for real-time transcription
  console.warn('transcribeAudio is deprecated. Use VoiceService for real-time transcription.');
  return { text: 'Use VoiceService for real transcription', confidence: 0.8, isFinal: true };
}

// Export singleton instance
export const voiceService = new VoiceService();
