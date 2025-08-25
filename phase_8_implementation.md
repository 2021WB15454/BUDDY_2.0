# BUDDY 2.0 Phase 8 Implementation Plan
## Voice Enablement & Speech Processing

### 🎯 Phase 8 Objectives
Building on the enhanced NLP foundation from Phase 7, Phase 8 focuses on enabling voice interaction capabilities across all BUDDY platforms.

### 📋 Implementation Timeline: 3-4 Weeks

---

## 🎤 Speech-to-Text (STT) Integration

### Week 1: Core STT Implementation

#### Primary STT Engine: Whisper (OpenAI)
```python
# whisper_stt.py
import whisper
import pyaudio
import wave
import threading

class WhisperSTT:
    def __init__(self, model_size="base"):
        self.model = whisper.load_model(model_size)
        self.is_listening = False
        
    async def transcribe_audio(self, audio_file):
        result = self.model.transcribe(audio_file)
        return result["text"]
        
    async def real_time_transcription(self, callback):
        # Real-time audio capture and transcription
        pass
```

#### Fallback STT Options:
1. **Vosk (Offline)**: For privacy-focused deployments
2. **Google Speech-to-Text**: For cloud-based accuracy
3. **Azure Speech Services**: For enterprise integration

#### Device-Specific Audio Capture:
- **Desktop**: PyAudio + microphone access
- **Mobile**: Platform-specific audio APIs
- **Watch**: Limited audio capture via Bluetooth
- **TV**: Remote microphone or TV built-in mic
- **Car**: Automotive audio system integration

---

## 🔊 Text-to-Speech (TTS) Integration

### Week 2: Multi-TTS Engine Implementation

#### Primary TTS Engine: Coqui TTS
```python
# coqui_tts.py
from TTS.api import TTS

class CoquiTTS:
    def __init__(self, model_name="tts_models/en/ljspeech/tacotron2-DDC"):
        self.tts = TTS(model_name)
        
    async def synthesize_speech(self, text, output_file):
        self.tts.tts_to_file(text=text, file_path=output_file)
        return output_file
        
    async def synthesize_to_stream(self, text):
        # Stream audio for real-time playback
        pass
```

#### TTS Engine Options:
1. **Coqui TTS**: High-quality, open-source, customizable voices
2. **gTTS (Google)**: Simple, cloud-based, multiple languages
3. **Azure Cognitive Services**: Enterprise-grade with SSML support
4. **Amazon Polly**: Neural voices with emotion control

#### Voice Personality Configuration:
```yaml
# voice_config.yml
buddy_voice:
  primary_engine: "coqui"
  voice_model: "ljspeech"
  personality:
    speed: 1.0
    pitch: 0.0
    emotion: "friendly"
  fallbacks:
    - "gtts"
    - "azure"
```

---

## 🎛️ Voice Pipeline Architecture

### Week 3: Unified Voice Processing

#### Voice Pipeline Flow:
```
Audio Input → STT → Enhanced NLP → TTS → Audio Output
     ↓         ↓         ↓         ↓         ↓
  Device    Intent   Context   Response  Platform
  Capture   Detection Manager  Generator  Output
```

#### Core Voice Engine:
```python
# voice_engine.py
class BuddyVoiceEngine:
    def __init__(self):
        self.stt_engine = WhisperSTT()
        self.tts_engine = CoquiTTS()
        self.nlp_engine = None  # From Phase 7
        
    async def process_voice_command(self, audio_input):
        # STT: Audio → Text
        text = await self.stt_engine.transcribe_audio(audio_input)
        
        # NLP: Enhanced processing from Phase 7
        response_data = await self.nlp_engine.process_message(
            session_id=session_id,
            user_id=user_id,
            message=text,
            metadata={"input_type": "voice"}
        )
        
        # TTS: Text → Audio
        audio_output = await self.tts_engine.synthesize_speech(
            response_data["response"]
        )
        
        return {
            "transcribed_text": text,
            "response_text": response_data["response"],
            "audio_output": audio_output,
            "intent": response_data["intent"],
            "confidence": response_data["confidence"]
        }
```

---

## 📱 Platform-Specific Voice Integration

### Week 4: Cross-Platform Voice Hooks

#### Desktop Voice Integration:
```python
# desktop_voice.py
import pyaudio
import keyboard

class DesktopVoiceInterface:
    def __init__(self):
        self.voice_engine = BuddyVoiceEngine()
        self.wake_word = "hey buddy"
        
    def setup_hotkey(self):
        keyboard.add_hotkey('ctrl+shift+v', self.start_voice_command)
        
    async def continuous_listening(self):
        # Always-on wake word detection
        pass
```

#### Mobile Voice Integration:
```dart
// mobile_voice.dart (Flutter)
class MobileVoiceInterface {
  late SpeechToText _speechToText;
  late FlutterTts _flutterTts;
  
  Future<void> startListening() async {
    await _speechToText.listen(
      onResult: (result) => _processVoiceInput(result.recognizedWords),
    );
  }
  
  Future<void> _processVoiceInput(String text) async {
    // Send to BUDDY backend voice API
    final response = await BuddyAPI.processVoiceCommand(text);
    await _flutterTts.speak(response.responseText);
  }
}
```

#### Watch Voice Integration:
```swift
// WatchVoiceInterface.swift
import WatchKit
import Speech

class WatchVoiceInterface: NSObject, SFSpeechRecognizerDelegate {
    private let speechRecognizer = SFSpeechRecognizer(locale: Locale(identifier: "en-US"))
    
    func startVoiceRecognition() {
        // Quick voice commands for watch
        // "Remind me...", "What time...", "Weather..."
    }
}
```

#### TV Voice Integration:
```python
# tv_voice.py
class TVVoiceInterface:
    def __init__(self):
        self.remote_mic_active = False
        self.voice_engine = BuddyVoiceEngine()
        
    async def handle_remote_voice_button(self):
        # TV remote voice button integration
        pass
        
    async def process_tv_command(self, audio):
        # TV-specific commands: volume, channel, apps
        result = await self.voice_engine.process_voice_command(audio)
        
        # Execute TV actions
        if result["intent"] == "tv_control":
            await self.execute_tv_command(result["response"])
```

#### Automotive Voice Integration:
```python
# automotive_voice.py
class AutomotiveVoiceInterface:
    def __init__(self):
        self.voice_engine = BuddyVoiceEngine()
        self.hands_free_mode = True
        
    async def handle_steering_wheel_button(self):
        # Steering wheel voice button
        pass
        
    async def process_driving_command(self, audio):
        # Driving-safe voice commands
        result = await self.voice_engine.process_voice_command(audio)
        
        # Execute safe driving actions
        if result["intent"] in ["navigation", "music", "calls"]:
            await self.execute_safe_command(result)
```

---

## 🔧 Voice API Endpoints

### Backend Voice API Extension:
```python
# Enhanced backend voice routes
@app.post("/api/voice/process")
async def process_voice_command(
    audio_file: UploadFile,
    user_id: str,
    session_id: str,
    db: BuddyDatabase = Depends(get_database)
):
    # Save uploaded audio
    audio_path = await save_audio_file(audio_file)
    
    # Process with voice engine
    result = await voice_engine.process_voice_command(audio_path)
    
    # Store voice interaction in database
    await db.save_voice_interaction(
        session_id=session_id,
        user_id=user_id,
        audio_input=audio_path,
        transcribed_text=result["transcribed_text"],
        response_text=result["response_text"],
        intent=result["intent"],
        confidence=result["confidence"]
    )
    
    return {
        "success": True,
        "transcription": result["transcribed_text"],
        "response": result["response_text"],
        "audio_url": f"/api/voice/audio/{result['audio_output']}",
        "intent": result["intent"],
        "confidence": result["confidence"]
    }

@app.get("/api/voice/audio/{filename}")
async def get_voice_response_audio(filename: str):
    # Serve generated TTS audio files
    return FileResponse(f"./voice_outputs/{filename}")
```

---

## 🗃️ Database Schema Extensions

### Voice Interaction Storage:
```sql
-- Voice interactions table
CREATE TABLE voice_interactions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255),
    user_id VARCHAR(255),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    audio_input_path VARCHAR(500),
    transcribed_text TEXT,
    response_text TEXT,
    audio_output_path VARCHAR(500),
    intent VARCHAR(100),
    confidence FLOAT,
    processing_time_ms INT,
    stt_engine VARCHAR(50),
    tts_engine VARCHAR(50),
    platform VARCHAR(50)
);

-- Voice preferences table
CREATE TABLE voice_preferences (
    user_id VARCHAR(255) PRIMARY KEY,
    preferred_stt_engine VARCHAR(50),
    preferred_tts_engine VARCHAR(50),
    voice_model VARCHAR(100),
    speech_speed FLOAT DEFAULT 1.0,
    speech_pitch FLOAT DEFAULT 0.0,
    wake_word VARCHAR(100) DEFAULT 'hey buddy',
    auto_listen BOOLEAN DEFAULT FALSE,
    voice_feedback BOOLEAN DEFAULT TRUE
);
```

---

## 🧪 Testing & Validation

### Voice Testing Framework:
```python
# voice_testing.py
class VoiceTestSuite:
    def __init__(self):
        self.test_audio_files = [
            "test_greeting.wav",
            "test_weather_query.wav", 
            "test_calculation.wav",
            "test_reminder.wav"
        ]
        
    async def test_stt_accuracy(self):
        # Test speech-to-text accuracy
        for audio_file in self.test_audio_files:
            result = await stt_engine.transcribe_audio(audio_file)
            accuracy = self.calculate_transcription_accuracy(result, expected_text)
            
    async def test_tts_quality(self):
        # Test text-to-speech output quality
        test_phrases = [
            "Hello, I'm BUDDY, your AI assistant.",
            "The weather today is sunny with a high of 75 degrees.",
            "I've set a reminder for 3 PM to call your doctor."
        ]
        
        for phrase in test_phrases:
            audio_output = await tts_engine.synthesize_speech(phrase)
            quality_score = self.evaluate_audio_quality(audio_output)
            
    async def test_end_to_end_voice(self):
        # Test complete voice pipeline
        audio_input = "test_voice_command.wav"
        result = await voice_engine.process_voice_command(audio_input)
        
        assert result["transcribed_text"] is not None
        assert result["response_text"] is not None
        assert result["audio_output"] is not None
```

---

## 📊 Performance Optimization

### Voice Processing Optimization:
1. **Audio Preprocessing**: Noise reduction, normalization
2. **Model Caching**: Keep STT/TTS models in memory
3. **Streaming Processing**: Real-time audio processing
4. **Compression**: Efficient audio file handling
5. **Parallel Processing**: Concurrent STT and NLP processing

### Resource Management:
```python
# voice_resource_manager.py
class VoiceResourceManager:
    def __init__(self):
        self.model_cache = {}
        self.audio_buffer_pool = []
        
    async def optimize_for_platform(self, platform):
        if platform == "mobile":
            # Use smaller models for mobile
            return {"stt": "whisper-tiny", "tts": "gtts"}
        elif platform == "desktop":
            # Use full models for desktop
            return {"stt": "whisper-base", "tts": "coqui"}
        elif platform == "watch":
            # Use cloud services for watch
            return {"stt": "google", "tts": "azure"}
```

---

## 🎯 Phase 8 Success Criteria

| Objective | Success Metric | Implementation |
|-----------|----------------|----------------|
| STT Integration | >90% transcription accuracy | Whisper + fallbacks |
| TTS Integration | Natural voice output | Coqui TTS + alternatives |
| Platform Support | Voice on all 6 platforms | Device-specific implementations |
| Real-time Processing | <3 second response time | Optimized pipeline |
| Voice API | RESTful endpoints | FastAPI integration |
| Context Integration | Voice uses Phase 7 NLP | Enhanced NLP pipeline |

---

## 🔮 Phase 8 Deliverables

### Core Components:
- ✅ **Voice Engine**: Unified STT + TTS processing
- ✅ **Platform Interfaces**: Device-specific voice hooks  
- ✅ **API Endpoints**: Voice command processing
- ✅ **Database Schema**: Voice interaction storage
- ✅ **Testing Framework**: Voice quality validation

### Integration Points:
- ✅ **Phase 7 NLP**: Enhanced voice command understanding
- ✅ **Existing Backend**: Voice API endpoints
- ✅ **Database**: Voice interaction logging
- ✅ **Cross-Platform**: Voice on all BUDDY platforms

---

## 🚀 Phase 8 → Phase 9 Transition

Upon completion of Phase 8, BUDDY will have:
- **Full Voice Capabilities** across all platforms
- **Intelligent Voice Processing** using Phase 7 NLP
- **Multi-Engine Support** with fallback mechanisms
- **Real-time Voice Interaction** with context awareness

**Next Phase 9 Focus**: Skills Ecosystem Development
- Custom skill creation framework
- Third-party skill integration
- Plugin architecture for extensibility
- Marketplace for BUDDY skills

---

## 📋 Phase 8 Implementation Checklist

### Week 1: STT Foundation
- [ ] Install and configure Whisper
- [ ] Implement audio capture for each platform
- [ ] Create STT fallback mechanisms
- [ ] Test transcription accuracy

### Week 2: TTS Implementation  
- [ ] Setup Coqui TTS engine
- [ ] Configure voice models and personalities
- [ ] Implement audio output for platforms
- [ ] Test speech quality and naturalness

### Week 3: Voice Pipeline
- [ ] Create unified voice processing engine
- [ ] Integrate with Phase 7 enhanced NLP
- [ ] Implement real-time voice processing
- [ ] Add voice session management

### Week 4: Platform Integration
- [ ] Desktop voice interface with hotkeys
- [ ] Mobile voice UI components
- [ ] Watch voice commands
- [ ] TV remote voice integration
- [ ] Automotive hands-free voice

### Validation & Testing:
- [ ] End-to-end voice command testing
- [ ] Performance optimization
- [ ] Platform-specific voice validation
- [ ] User experience testing
- [ ] Documentation and examples

**Status**: 📋 **PHASE 8 READY FOR IMPLEMENTATION**
