# BUDDY 2.0 Mobile Setup Guide

## Overview
This guide will help you set up the mobile development environment for testing the BUDDY 2.0 voice integration features we've implemented.

## Current Implementation Status ✅

### ✅ Completed Features
1. **Dynamic Configuration System**: Removed all hardcoded ports, using environment variables
2. **React Native Voice Integration**: Real voice recognition using @react-native-voice/voice
3. **Flutter Voice Integration**: Complete speech-to-text and text-to-speech implementation
4. **TFLite Model Framework**: Ready for AI model integration with placeholder models
5. **Native Project Structure**: Android project files created manually
6. **TypeScript Integration**: Full type definitions and enhanced development experience

### ✅ Created Files
- `apps/mobile/src/services/voice_module.ts`: Real voice recognition implementation
- `apps/mobile/src/services/voice_service.ts`: High-level voice service abstraction
- `apps/mobile/src/components/VoiceTestScreen.tsx`: Voice testing interface
- `apps/mobile_flutter/lib/src/services/voice_service.dart`: Flutter voice service
- `apps/mobile_flutter/lib/src/screens/voice_test_screen.dart`: Flutter voice test screen
- `generate_tflite_models.py`: TFLite model generation script
- Android native project structure with proper configuration

## Required Development Tools

### 1. Android Development Environment

#### Option A: Android Studio (Recommended)
1. Download and install Android Studio from: https://developer.android.com/studio
2. During installation, ensure these components are selected:
   - Android SDK
   - Android SDK Platform
   - Android Virtual Device (AVD)
   - Performance (Intel HAXM) - for Intel processors

#### Option B: Command Line Tools Only
1. Download Android SDK Command Line Tools: https://developer.android.com/studio#command-tools
2. Extract to a folder (e.g., `C:\Android\sdk`)
3. Add to PATH:
   - `C:\Android\sdk\platform-tools`
   - `C:\Android\sdk\tools`
   - `C:\Android\sdk\tools\bin`

### 2. Java Development Kit (JDK)
1. Install JDK 11 or later: https://www.oracle.com/java/technologies/downloads/
2. Set JAVA_HOME environment variable to JDK installation path

### 3. Flutter SDK (for Flutter app testing)
1. Download Flutter SDK: https://docs.flutter.dev/get-started/install/windows
2. Extract to a folder (e.g., `C:\flutter`)
3. Add `C:\flutter\bin` to PATH
4. Run `flutter doctor` to verify installation

## Setup Instructions

### 1. Environment Variables
Create or update these environment variables:

```bash
# Android
ANDROID_HOME=C:\Android\sdk
JAVA_HOME=C:\Program Files\Java\jdk-11.x.x

# BUDDY Configuration
BUDDY_HOST=localhost
BUDDY_PORT=3000

# PATH additions
PATH=%PATH%;%ANDROID_HOME%\platform-tools;%ANDROID_HOME%\tools;%JAVA_HOME%\bin;C:\flutter\bin
```

### 2. React Native Setup
```bash
# Navigate to mobile app directory
cd apps/mobile

# Install dependencies (already done)
npm install

# For iOS (macOS only)
cd ios && pod install && cd ..
```

### 3. Flutter Setup
```bash
# Navigate to Flutter app directory
cd apps/mobile_flutter

# Get Flutter dependencies
flutter pub get

# Check Flutter environment
flutter doctor
```

## Testing the Voice Features

### 1. React Native App

#### Start Metro Bundler
```bash
cd apps/mobile
npm start
```

#### Run on Android Device/Emulator
```bash
# Make sure an Android device is connected or emulator is running
npm run android
```

#### Run on iOS Device/Simulator (macOS only)
```bash
npm run ios
```

### 2. Flutter App

#### Run on Android
```bash
cd apps/mobile_flutter
flutter run
```

#### Run on iOS (macOS only)
```bash
flutter run
```

## Voice Testing Features

### Available Test Functions
1. **Start Voice Recognition**: Tap to begin listening
2. **Stop Recording**: End voice capture
3. **Volume Monitoring**: Real-time audio level display
4. **Transcription Display**: Shows both partial and final results
5. **Error Handling**: Displays any voice recognition errors
6. **Locale Selection**: Test different languages (en-US, en-GB, es-ES, etc.)

### Test Scenarios
1. **Basic Recording**: Say "Hello, this is a test"
2. **Long Speech**: Test with longer sentences
3. **Different Languages**: Test locale switching
4. **Background Noise**: Test in noisy environments
5. **Quick Commands**: Test rapid start/stop sequences

## Troubleshooting

### Common Issues

#### 1. "Android SDK not found"
- Ensure ANDROID_HOME is set correctly
- Verify Android SDK is installed
- Check PATH includes platform-tools

#### 2. "No connected devices"
- Enable USB debugging on Android device
- Start an Android emulator
- Run `adb devices` to verify connection

#### 3. "Gradle build failed"
- Check Java version (JDK 11+ required)
- Verify JAVA_HOME is set
- Clear gradle cache: `cd android && ./gradlew clean`

#### 4. "React Native Voice permission denied"
- Grant microphone permissions in device settings
- Check AndroidManifest.xml includes RECORD_AUDIO permission

#### 5. "Flutter doctor issues"
- Run `flutter doctor` and follow recommendations
- Install missing dependencies as indicated

### Voice Feature Debugging
1. Check device microphone permissions
2. Verify network connectivity for backend communication
3. Test with different languages/locales
4. Monitor console logs for detailed error messages

## Backend Integration

### Starting the Backend Server
```bash
# Start the main BUDDY server
cd ../../
python buddy_main.py

# Or start the enhanced backend
python enhanced_backend.py
```

### Testing Voice-to-Backend Communication
1. Start the backend server (default: http://localhost:3000)
2. Launch mobile app
3. Test voice recognition
4. Verify transcriptions are sent to backend
5. Check backend processes voice commands correctly

## Performance Optimization

### React Native
- Enable Hermes JavaScript engine (already configured)
- Use release builds for performance testing: `npm run android --variant=release`

### Flutter
- Test with profile builds: `flutter run --profile`
- Create release builds: `flutter build apk --release`

## Next Steps for Production

### 1. Real TFLite Models
- Train actual models using the framework in `generate_tflite_models.py`
- Replace placeholder models with trained versions
- Implement model download/update mechanisms

### 2. Advanced Voice Features
- Voice activity detection
- Custom wake words
- Noise reduction
- Echo cancellation

### 3. Cross-Platform Sync
- Real-time voice data synchronization
- Multi-device conversation context
- Cloud-based voice processing

### 4. Security & Privacy
- Local voice processing
- Encrypted voice data transmission
- User consent management
- GDPR compliance

## Support
If you encounter issues:
1. Check the troubleshooting section above
2. Run environment verification scripts
3. Review console logs for specific error messages
4. Ensure all required tools are properly installed and configured
