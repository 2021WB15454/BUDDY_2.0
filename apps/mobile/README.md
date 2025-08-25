# BUDDY Mobile App - Cross-Platform (iOS & Android)

## Overview
Cross-platform mobile application for BUDDY AI assistant supporting both iOS and Android platforms with offline-first capabilities and cloud synchronization.

## Architecture
- **Framework**: React Native / Flutter
- **Local Database**: SQLite + Realm for offline storage
- **Cloud Sync**: MongoDB Atlas via Realm Sync
- **Voice**: Native iOS/Android speech APIs
- **Security**: End-to-end encryption

## Platform-Specific Features

### iOS
- **Integration**: Siri Shortcuts, App Intents
- **Storage**: Core Data bridge
- **Voice**: Speech Framework, AVAudioEngine
- **Notifications**: APNs with rich notifications
- **Widgets**: WidgetKit support

### Android
- **Integration**: Google Assistant Actions
- **Storage**: Room database bridge
- **Voice**: Android Speech API, AudioRecord
- **Notifications**: FCM with custom layouts
- **Widgets**: App Widget support

## Development Setup

### React Native Version
```bash
# Install dependencies
npm install -g react-native-cli
npm install

# iOS setup
cd ios && pod install

# Android setup
# Ensure Android SDK is installed

# Run on iOS
npx react-native run-ios

# Run on Android
npx react-native run-android
```

### Flutter Version
```bash
# Install Flutter
flutter doctor

# Get dependencies
flutter pub get

# Run on iOS
flutter run -d ios

# Run on Android
flutter run -d android
```

## Features
- ✅ Voice interaction with BUDDY
- ✅ Offline conversation storage
- ✅ Real-time sync across devices
- ✅ Smart notifications and reminders
- ✅ Contextual suggestions
- ✅ Privacy-first encryption
- ✅ Platform-specific integrations

## Database Schema
Local SQLite database with tables for:
- User profiles and preferences
- Conversation history
- AI context and memory
- Sync metadata
- Offline operation queue

## API Integration
Connects to BUDDY Core via:
- WebSocket for real-time communication
- REST API for data operations
- GraphQL for complex queries (optional)

## Security
- End-to-end encryption for all user data
- Biometric authentication (Face ID, Touch ID, Fingerprint)
- Secure key storage in Keychain/Keystore
- Certificate pinning for API communication
