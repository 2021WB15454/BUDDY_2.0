# Native React Native Project Generation

To generate the actual native Android/iOS projects (if not already created) run:

```
npx react-native init buddyNative --version 0.73.11 --template react-native-template-typescript
```

Then selectively copy the `/android` and `/ios` directories (or compare & merge) into `apps/mobile`.

Key merge considerations:
1. Keep existing `src/` TypeScript code.
2. Ensure `package.json` dependencies match (react, react-native, types, voice libraries).
3. Install native voice dependency:
```
npm install react-native-voice
npx pod-install
```
4. Add required iOS permissions to `Info.plist`:
```
<key>NSMicrophoneUsageDescription</key>
<string>Voice input for BUDDY assistant</string>
<key>NSSpeechRecognitionUsageDescription</key>
<string>Speech recognition for BUDDY</string>
```
5. Android `AndroidManifest.xml` add:
```
<uses-permission android:name="android.permission.RECORD_AUDIO" />
```
6. Update Metro config if monorepo symlinks used.

After merge build:
```
npm run android
# or	npm run ios
```

CI Note: Once `/android` exists, update GitHub Actions to run a Gradle assemble step using the new module.
