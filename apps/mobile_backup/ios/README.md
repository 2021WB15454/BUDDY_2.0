Placeholder iOS project directory.

Generate iOS native project (if not created) via:
```
cd apps/mobile
npx react-native init tempgen --version 0.73.0
```
Copy the resulting `ios/` contents here. Run `pod install` under `ios/` after dependency changes.

For voice features add pods for speech recognition as needed.