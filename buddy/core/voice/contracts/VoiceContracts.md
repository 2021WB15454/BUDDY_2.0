# BUDDY Voice Stack Contracts

This document defines the unified interfaces and message schema for BUDDY's cross-platform voice system.

## 🎯 Core Principles

- **Offline First**: Wake word + STT work without internet
- **Cross-Platform**: Same logic across Android, iOS, Wear OS, watchOS, Car
- **Low Power**: Efficient wake word detection
- **Privacy**: Local processing by default
- **Unified API**: Common interface across all platforms

## 📡 Voice Event Bus

All platforms implement a unified event bus for voice pipeline coordination:

### Event Types

```typescript
enum VoiceEventType {
  // Wake word events
  WAKE_WORD_DETECTED = "wake_word_detected",
  WAKE_WORD_LISTENING = "wake_word_listening",
  WAKE_WORD_STOPPED = "wake_word_stopped",
  
  // STT events  
  STT_STARTED = "stt_started",
  STT_PARTIAL_RESULT = "stt_partial_result",
  STT_FINAL_RESULT = "stt_final_result",
  STT_STOPPED = "stt_stopped",
  STT_ERROR = "stt_error",
  
  // TTS events
  TTS_STARTED = "tts_started",
  TTS_FINISHED = "tts_finished",
  TTS_ERROR = "tts_error",
  
  // Session events
  VOICE_SESSION_STARTED = "voice_session_started",
  VOICE_SESSION_ENDED = "voice_session_ended",
  SILENCE_DETECTED = "silence_detected",
  
  // Bridge events
  BUDDY_REQUEST = "buddy_request",
  BUDDY_RESPONSE = "buddy_response",
  BUDDY_ERROR = "buddy_error"
}
```

### Event Payloads

```typescript
interface VoiceEvent {
  type: VoiceEventType;
  timestamp: number;
  sessionId?: string;
  payload?: any;
}

interface WakeWordEvent extends VoiceEvent {
  type: VoiceEventType.WAKE_WORD_DETECTED;
  payload: {
    keywordIndex: number;
    confidence: number;
  };
}

interface SttResultEvent extends VoiceEvent {
  type: VoiceEventType.STT_FINAL_RESULT;
  payload: {
    text: string;
    confidence: number;
    language: string;
  };
}

interface BuddyRequestEvent extends VoiceEvent {
  type: VoiceEventType.BUDDY_REQUEST;
  payload: {
    text: string;
    context?: any;
    metadata?: any;
  };
}

interface BuddyResponseEvent extends VoiceEvent {
  type: VoiceEventType.BUDDY_RESPONSE;
  payload: {
    text: string;
    intent?: string;
    actions?: any[];
    metadata?: any;
  };
}
```

## 🎤 Interface Definitions

### IWakeWordDetector

```typescript
interface IWakeWordDetector {
  // Lifecycle
  start(): Promise<void>;
  stop(): Promise<void>;
  isListening(): boolean;
  
  // Configuration
  setSensitivity(value: number): void; // 0.0 - 1.0
  setKeywordPath(path: string): void;
  
  // Events
  onWakeWordDetected(callback: (event: WakeWordEvent) => void): void;
  onError(callback: (error: Error) => void): void;
}
```

### ISpeechToText

```typescript
interface ISpeechToText {
  // Lifecycle
  startSession(sessionId: string): Promise<void>;
  stopSession(): Promise<void>;
  isActive(): boolean;
  
  // Configuration
  setModel(modelPath: string): void;
  setLanguage(language: string): void;
  setSilenceTimeout(ms: number): void; // Auto-stop after silence
  
  // Events
  onPartialResult(callback: (text: string) => void): void;
  onFinalResult(callback: (event: SttResultEvent) => void): void;
  onSilenceDetected(callback: () => void): void;
  onError(callback: (error: Error) => void): void;
}
```

### ITextToSpeech

```typescript
interface ITextToSpeech {
  // Lifecycle
  speak(text: string, options?: TtsOptions): Promise<void>;
  stop(): Promise<void>;
  isSpeaking(): boolean;
  
  // Configuration
  setVoice(voice: string): void;
  setRate(rate: number): void; // 0.1 - 2.0
  setPitch(pitch: number): void; // 0.5 - 2.0
  
  // Events
  onSpeechStarted(callback: () => void): void;
  onSpeechFinished(callback: () => void): void;
  onError(callback: (error: Error) => void): void;
}

interface TtsOptions {
  voice?: string;
  rate?: number;
  pitch?: number;
  priority?: 'low' | 'normal' | 'high';
  interruptible?: boolean;
}
```

### IBuddyBridge

```typescript
interface IBuddyBridge {
  // Core processing
  processText(text: string, context?: any): Promise<BuddyResponse>;
  
  // Configuration
  setEndpoint(url: string): void;
  setApiKey(key: string): void;
  setTimeout(ms: number): void;
  
  // Offline fallback
  setOfflineMode(enabled: boolean): void;
  addOfflineResponse(pattern: string, response: string): void;
  
  // Events
  onResponse(callback: (event: BuddyResponseEvent) => void): void;
  onError(callback: (error: Error) => void): void;
}

interface BuddyResponse {
  text: string;
  intent?: string;
  confidence?: number;
  actions?: BuddyAction[];
  metadata?: any;
}

interface BuddyAction {
  type: string;
  payload: any;
}
```

### IVoiceOrchestrator

```typescript
interface IVoiceOrchestrator {
  // Lifecycle
  initialize(): Promise<void>;
  start(): Promise<void>;
  stop(): Promise<void>;
  
  // Components
  getWakeWordDetector(): IWakeWordDetector;
  getSpeechToText(): ISpeechToText;
  getTextToSpeech(): ITextToSpeech;
  getBridge(): IBuddyBridge;
  
  // State
  getCurrentState(): VoiceState;
  getSessionId(): string;
  
  // Events
  onStateChanged(callback: (state: VoiceState) => void): void;
  onEvent(callback: (event: VoiceEvent) => void): void;
}

enum VoiceState {
  IDLE = "idle",
  LISTENING_FOR_WAKE = "listening_for_wake",
  WAKE_DETECTED = "wake_detected", 
  STT_ACTIVE = "stt_active",
  PROCESSING = "processing",
  TTS_SPEAKING = "tts_speaking",
  ERROR = "error"
}
```

## 🔄 Standard Voice Flow

```
1. IDLE → LISTENING_FOR_WAKE
   - Wake word detector starts
   - Low power monitoring

2. LISTENING_FOR_WAKE → WAKE_DETECTED
   - "Hey Buddy" detected
   - Optional confirmation sound/haptic

3. WAKE_DETECTED → STT_ACTIVE  
   - Start speech recognition session
   - Begin audio capture

4. STT_ACTIVE → PROCESSING
   - Final text result received
   - Send to BUDDY brain

5. PROCESSING → TTS_SPEAKING
   - Response received from BUDDY
   - Begin text-to-speech

6. TTS_SPEAKING → LISTENING_FOR_WAKE
   - Speech finished
   - Return to wake detection

Error states:
- Any state → ERROR (with recovery)
- STT_ACTIVE → LISTENING_FOR_WAKE (timeout/silence)
```

## 📱 Platform-Specific Requirements

### Android
- Use foreground service for wake word detection
- Implement AudioRecord for STT pipeline
- Support Android Auto (background service)
- Handle audio focus changes
- Wear OS: shorter sessions, tile integration

### iOS  
- Background audio processing capabilities
- AVAudioEngine for STT pipeline
- Support CarPlay (limited UI)
- watchOS: complication/shortcut triggers
- Handle audio session interruptions

### Audio Specifications

```
Sample Rate: 16 kHz
Channels: Mono (1 channel)
Bit Depth: 16-bit signed PCM
Buffer Size: 2048 samples (128ms @ 16kHz)
Format: Little-endian byte order
```

## 🔐 Security & Privacy

### Data Handling
- Audio never stored permanently
- STT processing local by default  
- Optional cloud processing with user consent
- Wake word patterns stored locally only

### Permissions
- Microphone access required
- Network access optional (cloud features)
- Storage access for models
- Background processing permissions

## 🧪 Testing Requirements

### Wake Word
- False positive rate < 1/hour ambient
- True positive rate > 95% clean speech
- Latency < 500ms detection to action

### STT
- Word error rate < 10% clean speech
- Silence detection within 2-4 seconds
- Session timeout handling

### TTS
- Natural speech output
- Configurable rate/pitch
- Interrupt handling

### Integration
- Full pipeline latency < 3 seconds
- Reliable state transitions
- Error recovery mechanisms
- Battery optimization

## 📦 Model Requirements

### Wake Word (Porcupine)
- Custom "Hey Buddy" .ppn file
- Sensitivity tunable 0.3-0.8
- Multiple language support
- < 1MB memory footprint

### STT (Vosk)
- Mobile-optimized models
- English: ~50MB compressed
- Real-time streaming capable
- Offline operation

### TTS
- System TTS engines by default
- Optional neural voices
- SSML support preferred
- < 200ms startup latency
