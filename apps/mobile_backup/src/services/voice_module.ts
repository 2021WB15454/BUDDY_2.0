// Voice recording / transcription scaffold (placeholder)
// Replace with react-native-voice or custom native module.
import EventEmitter from 'eventemitter3';

export class VoiceModule extends EventEmitter {
  private recording = false;
  async start() {
    if (this.recording) return;
    this.recording = true;
    this.emit('start');
    // Simulate transcription after delay
    setTimeout(() => {
      if (!this.recording) return;
      this.emit('transcription', { text: 'simulated voice input', confidence: 0.9 });
      this.stop();
    }, 1500);
  }
  stop() {
    if (!this.recording) return;
    this.recording = false;
    this.emit('stop');
  }
  isRecording() { return this.recording; }
}

export const voiceModule = new VoiceModule();