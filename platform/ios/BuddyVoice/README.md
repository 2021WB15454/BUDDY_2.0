# iOS BUDDY Voice Implementation

This directory contains the complete iOS implementation of BUDDY's cross-platform voice system.

## Architecture Overview

The iOS voice implementation follows the cross-platform contracts defined in `buddy/core/voice/contracts/` and provides native iOS implementations using Swift and iOS frameworks.

## Components

### Core Voice Components

1. **WakeWordManager.swift**
   - Porcupine wake word detection integration
   - iOS-specific optimizations (background processing, app state handling)
   - Haptic feedback and iOS/watchOS support
   - Low-power continuous monitoring

2. **VoskStt.swift**
   - Vosk speech-to-text engine for iOS
   - AVAudioEngine integration for real-time audio processing
   - Automatic silence detection and session management
   - iOS audio session configuration

3. **TtsEngine.swift**
   - AVSpeechSynthesizer for system TTS
   - Priority queue with interruption handling
   - Cloud TTS integration (OpenAI) with offline fallback
   - Voice customization and rate control

4. **VoiceBus.swift**
   - Thread-safe event distribution system
   - Voice flow coordination between components
   - Session management and state tracking
   - iOS/watchOS platform integration

5. **BuddyBridge.swift**
   - Connection to BUDDY backend intelligence
   - Online/offline processing with local intent matching
   - Network monitoring and automatic fallback
   - Session management and conversation tracking

## Features

### Cross-Platform Compatibility
- Implements shared voice contracts from `VoiceContracts.md`
- Consistent behavior across Android and iOS
- Event-driven architecture with standardized messaging

### Offline-First Operation
- Local intent matching for basic queries
- Vosk offline speech recognition
- System TTS without network dependency
- Graceful degradation when offline

### iOS-Specific Optimizations
- Background processing support
- App state change handling
- AVAudioSession management
- Haptic feedback integration
- iOS notification system integration

### Performance Features
- Low-power wake word detection
- Streaming speech recognition
- Priority-based TTS queue
- Efficient memory management
- Background/foreground state optimization

## Audio Configuration

All components use standardized audio format:
- **Sample Rate**: 16kHz
- **Channels**: Mono
- **Bit Depth**: 16-bit PCM
- **Buffer Size**: 1600 samples (100ms at 16kHz)

## Dependencies

### Required iOS Frameworks
```swift
import AVFoundation      // Audio processing, TTS
import Speech           // iOS Speech framework (optional)
import CoreHaptics      // Haptic feedback
import Network          // Network monitoring
import Combine          // Reactive programming
```

### Third-Party Libraries
- **Porcupine**: Wake word detection
- **Vosk**: Offline speech recognition
- **OpenAI API**: Cloud TTS (optional)

## Integration

### Project Setup

1. **Add to Xcode Project**:
   ```
   platform/ios/BuddyVoice/
   ├── WakeWordManager.swift
   ├── VoskStt.swift
   ├── TtsEngine.swift
   ├── VoiceBus.swift
   └── BuddyBridge.swift
   ```

2. **Add Frameworks**:
   - AVFoundation.framework
   - Network.framework
   - CoreHaptics.framework

3. **Bundle Resources**:
   - Porcupine wake word models
   - Vosk speech recognition models
   - Local intents.json file

### Usage Example

```swift
import SwiftUI

struct ContentView: View {
    @StateObject private var voiceBus = VoiceBus.shared
    @StateObject private var ttsEngine = TtsEngine.shared
    
    var body: some View {
        VStack {
            Text("BUDDY Voice Status: \(voiceBus.currentState.rawValue)")
            
            Button("Start Voice") {
                voiceBus.startVoiceFlow()
            }
            
            Button("Stop Voice") {
                voiceBus.stopVoiceFlow()
            }
        }
        .onAppear {
            setupVoiceSystem()
        }
    }
    
    private func setupVoiceSystem() {
        // Configure components
        WakeWordManager.shared.configure(
            keywordPath: Bundle.main.path(forResource: "hey_buddy", ofType: "ppn")!,
            accessKey: "your_porcupine_access_key"
        )
        
        VoskStt.shared.configure(
            modelPath: Bundle.main.path(forResource: "vosk-model", ofType: nil)!
        )
        
        BuddyBridge.shared.configure(serverUrl: "https://your-buddy-server.com")
        
        // Start listening for wake word
        WakeWordManager.shared.startListening()
    }
}
```

## Voice Flow

1. **Wake Word Detection**: Continuous listening for "Hey BUDDY"
2. **STT Activation**: Start speech recognition after wake word
3. **Intent Processing**: Local or server-based intent recognition
4. **Response Generation**: Generate appropriate response
5. **TTS Output**: Speak response to user
6. **Session Management**: Handle conversation state

## Platform Variants

### iOS Standard
- Full feature set with background processing
- Complete Siri Shortcuts integration
- Rich haptic feedback

### watchOS
- Simplified UI and reduced features
- Optimized for quick interactions
- Battery-conscious implementation

### iOS Car Integration
- CarPlay compatibility
- Voice-only interaction mode
- Automotive audio session handling

## Testing

### Unit Tests
```swift
// Test voice component integration
func testVoiceFlow() {
    let expectation = XCTestExpectation(description: "Voice flow completion")
    
    VoiceBus.shared.subscribe("test") { event in
        if case .responseGenerated = event {
            expectation.fulfill()
        }
    }
    
    // Simulate wake word detection
    VoiceBus.shared.post(.wakeWordDetected(keyword: "hey_buddy"))
    
    wait(for: [expectation], timeout: 10.0)
}
```

### Integration Tests
- End-to-end voice processing
- Network failure scenarios
- Background/foreground transitions
- Audio interruption handling

## Performance Considerations

- **Memory Usage**: Efficient model loading and memory management
- **Battery Life**: Low-power wake word detection, background optimization
- **Latency**: Sub-500ms response times for voice interactions
- **Audio Quality**: 16kHz sampling for balance of quality and performance

## Troubleshooting

### Common Issues

1. **Wake Word Not Detected**:
   - Check microphone permissions
   - Verify Porcupine model path
   - Ensure audio session is active

2. **STT Not Working**:
   - Verify Vosk model installation
   - Check audio input configuration
   - Ensure sufficient storage space

3. **TTS Silent**:
   - Check audio output routing
   - Verify AVAudioSession configuration
   - Test with system speech settings

### Debug Information
```swift
VoiceBus.shared.printDebugInfo()
```

## File Structure
```
platform/ios/BuddyVoice/
├── README.md                 # This file
├── WakeWordManager.swift     # Porcupine wake word detection
├── VoskStt.swift            # Vosk speech-to-text
├── TtsEngine.swift          # AVSpeechSynthesizer + Cloud TTS
├── VoiceBus.swift           # Event coordination system
└── BuddyBridge.swift        # Backend integration
```

This implementation provides a complete, production-ready iOS voice system that integrates seamlessly with BUDDY's cross-platform architecture while leveraging iOS-specific capabilities for optimal user experience.
