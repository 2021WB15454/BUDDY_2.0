// Type definitions for react-native-voice
declare module 'react-native-voice' {
  export interface SpeechResultsEvent {
    value?: string[];
  }

  export interface SpeechErrorEvent {
    error?: {
      code?: string;
      message?: string;
    };
  }

  export interface VoiceOptions {
    showPopup?: boolean;
    showPartial?: boolean;
    partialResults?: boolean;
    maximumSpeechInputDuration?: number;
    speechDetectionTimeoutMillis?: number;
    speechInputCompleteTimeoutMillis?: number;
  }

  export default class Voice {
    static onSpeechStart: (() => void) | null;
    static onSpeechRecognized: (() => void) | null;
    static onSpeechEnd: (() => void) | null;
    static onSpeechError: ((event: SpeechErrorEvent) => void) | null;
    static onSpeechResults: ((event: SpeechResultsEvent) => void) | null;
    static onSpeechPartialResults: ((event: SpeechResultsEvent) => void) | null;
    static onSpeechVolumeChanged: ((event: { value: number }) => void) | null;

    static isAvailable(): Promise<boolean>;
    static start(locale?: string, options?: VoiceOptions): Promise<void>;
    static stop(): Promise<void>;
    static cancel(): Promise<void>;
    static destroy(): Promise<void>;
    static getSupportedLocales(): Promise<string[]>;
  }

  export { SpeechResultsEvent, SpeechErrorEvent, VoiceOptions };
}
