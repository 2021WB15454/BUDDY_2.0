// Voice recording / transcription implementation using react-native-voice
import EventEmitter from 'eventemitter3';
import Voice, {
  SpeechErrorEvent,
  SpeechResultsEvent,
  SpeechVolumeChangeEvent,
} from '@react-native-voice/voice';

export interface VoiceTranscriptionResult {
  text: string;
  confidence: number;
  isFinal: boolean;
}

export class VoiceModule extends EventEmitter {
  private recording = false;
  private isInitialized = false;

  constructor() {
    super();
    this.initializeVoice();
  }

  private async initializeVoice() {
    try {
      // Set up voice event listeners
      Voice.onSpeechStart = this.onSpeechStart.bind(this);
      Voice.onSpeechRecognized = this.onSpeechRecognized.bind(this);
      Voice.onSpeechEnd = this.onSpeechEnd.bind(this);
      Voice.onSpeechError = this.onSpeechError.bind(this);
      Voice.onSpeechResults = this.onSpeechResults.bind(this);
      Voice.onSpeechPartialResults = this.onSpeechPartialResults.bind(this);
      Voice.onSpeechVolumeChanged = this.onSpeechVolumeChanged.bind(this);

      this.isInitialized = true;
      this.emit('initialized');
    } catch (error) {
      console.error('Voice initialization failed:', error);
      this.emit('error', { type: 'initialization', error });
    }
  }

  async start(locale: string = 'en-US'): Promise<void> {
    if (!this.isInitialized) {
      throw new Error('Voice module not initialized');
    }

    if (this.recording) {
      console.warn('Voice recording already in progress');
      return;
    }

    try {
      // Check if speech recognition is available
      const isAvailable = await Voice.isAvailable();
      if (!isAvailable) {
        throw new Error('Speech recognition not available on this device');
      }

      // Start speech recognition
      await Voice.start(locale, {
        showPopup: false,
        showPartial: true,
        partialResults: true,
        maximumSpeechInputDuration: 30000, // 30 seconds max
        speechDetectionTimeoutMillis: 2000,
        speechInputCompleteTimeoutMillis: 2000,
      });

      this.recording = true;
      this.emit('start');
    } catch (error) {
      console.error('Failed to start voice recognition:', error);
      this.emit('error', { type: 'start', error });
      throw error;
    }
  }

  async stop(): Promise<void> {
    if (!this.recording) {
      return;
    }

    try {
      await Voice.stop();
      this.recording = false;
      this.emit('stop');
    } catch (error) {
      console.error('Failed to stop voice recognition:', error);
      this.emit('error', { type: 'stop', error });
    }
  }

  async cancel(): Promise<void> {
    if (!this.recording) {
      return;
    }

    try {
      await Voice.cancel();
      this.recording = false;
      this.emit('cancel');
    } catch (error) {
      console.error('Failed to cancel voice recognition:', error);
      this.emit('error', { type: 'cancel', error });
    }
  }

  async destroy(): Promise<void> {
    try {
      await Voice.destroy();
      this.recording = false;
      this.isInitialized = false;
      this.emit('destroyed');
    } catch (error) {
      console.error('Failed to destroy voice recognition:', error);
      this.emit('error', { type: 'destroy', error });
    }
  }

  // Check if voice recognition is currently recording
  isRecording(): boolean {
    return this.recording;
  }

  // Check if the voice module is properly initialized
  isReady(): boolean {
    return this.isInitialized;
  }

  // Event handlers for react-native-voice
  private onSpeechStart() {
    console.log('Speech recognition started');
    this.emit('speechStart');
  }

  private onSpeechRecognized() {
    console.log('Speech recognized');
    this.emit('speechRecognized');
  }

  private onSpeechEnd() {
    console.log('Speech recognition ended');
    this.recording = false;
    this.emit('speechEnd');
  }

  private onSpeechError(event: SpeechErrorEvent) {
    console.error('Speech recognition error:', event.error);
    this.recording = false;
    this.emit('error', { 
      type: 'recognition', 
      error: event.error,
      message: event.error?.message 
    });
  }

  private onSpeechResults(event: SpeechResultsEvent) {
    const results = event.value || [];
    if (results.length > 0) {
      const bestResult = results[0];
      const transcription: VoiceTranscriptionResult = {
        text: bestResult,
        confidence: 1.0, // react-native-voice doesn't provide confidence scores
        isFinal: true
      };
      
      console.log('Final speech result:', bestResult);
      this.emit('transcription', transcription);
      this.emit('results', { results, bestResult });
    }
  }

  private onSpeechPartialResults(event: SpeechResultsEvent) {
    const results = event.value || [];
    if (results.length > 0) {
      const partialResult = results[0];
      const transcription: VoiceTranscriptionResult = {
        text: partialResult,
        confidence: 0.8, // Lower confidence for partial results
        isFinal: false
      };
      
      console.log('Partial speech result:', partialResult);
      this.emit('partialTranscription', transcription);
      this.emit('partialResults', { results, partialResult });
    }
  }

  private onSpeechVolumeChanged(event: SpeechVolumeChangeEvent) {
    const value = event.value ?? 0;
    this.emit('volumeChanged', value);
  }

  // Utility methods
  async getSupportedLocales(): Promise<string[]> {
    try {
      // Note: getSupportedLocales may not be available in all versions
      return ['en-US', 'en-GB', 'es-ES', 'fr-FR', 'de-DE']; // Common locales
    } catch (error) {
      console.error('Failed to get supported locales:', error);
      return ['en-US']; // Fallback
    }
  }

  async isRecognitionAvailable(): Promise<boolean> {
    try {
      const available = await Voice.isAvailable();
      return typeof available === 'number' ? available === 1 : Boolean(available);
    } catch (error) {
      console.error('Failed to check recognition availability:', error);
      return false;
    }
  }
}

// Export singleton instance
export const voiceModule = new VoiceModule();