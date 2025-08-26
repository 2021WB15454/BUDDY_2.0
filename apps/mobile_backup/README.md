<!-- Unified Mobile Blueprint -->

# 📱 BUDDY Mobile 2.0 – Unified Blueprint

## Overview
Cross-platform mobile application for the BUDDY AI assistant supporting both iOS and Android with offline‑first capabilities and seamless cloud synchronization.

---

## Table of Contents
1. Overview  
2. Architecture  
3. Platform-Specific Features  
4. Development Setup (React Native / Flutter)  
5. Features  
6. Database Schema  
7. API Integration  
8. Security  
9. Phase-Wise Roadmap  
10. Visual Roadmap Summary  
11. High-Level Architecture Diagram  
12. Voice Command Flow  
13. Repository Folder Mapping  

---

## Architecture
* **Framework**: React Native / Flutter (final selection can remain dual during exploration; React Native primary)  
* **Local Database**: SQLite + Realm (offline-first, conflict resolution)  
* **Cloud Sync**: MongoDB Atlas via Realm Sync  
* **Voice**: Native iOS/Android speech APIs (abstracted)  
* **Security**: End-to-end encryption (content), secure key vault, certificate pinning  
* **Transport**: WebSocket (real-time) + REST (CRUD) + optional GraphQL  
* **Context Memory**: Local cache → Pinecone (vector) + MongoDB (structured)  

---

## Platform-Specific Features

### iOS
* **Integration**: Siri Shortcuts, App Intents
* **Storage**: Core Data bridge (legacy) / Realm primary
* **Voice**: Speech Framework, AVAudioEngine
* **Notifications**: APNs (rich + action categories)
* **Widgets**: WidgetKit (glance + quick actions)
* **Security**: Keychain + Secure Enclave (biometrics)

### Android
* **Integration**: Google Assistant Intents / App Actions
* **Storage**: Room bridge (legacy) / Realm primary
* **Voice**: Android Speech API + optional on-device models
* **Notifications**: FCM (action + heads-up)
* **Widgets**: App Widgets / Quick Settings Tile
* **Security**: Keystore + BiometricPrompt

---

## Development Setup

### React Native Version
```bash
# Install dependencies
npm install -g react-native-cli
npm install

# iOS setup
cd ios && pod install

# Android setup
# Ensure Android SDK + NDK installed (if needed)

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

---

## Features
* ✅ Voice interaction with BUDDY (PTT + wake UI)  
* ✅ Offline conversation storage  
* ✅ Real-time sync across devices  
* ✅ Smart notifications & reminders  
* ✅ Contextual suggestions  
* ✅ Privacy-first encryption  
* ✅ Platform-specific integrations  
* 🔄 Background sync & proactive prompts (Phase 2+)  
* 🔐 Privacy dashboard (Phase 3)  

---

## Database Schema (Conceptual)
Local (SQLite/Realm) logical groups:
* Users (profile, preferences, device tokens)
* Conversations (messages, roles, timestamps, vector ref IDs)
* LocalContext (recent intents, embeddings cache meta)
* SyncQueue (pending outbound ops: create/update/delete)
* Notifications (scheduled, delivered state)
* Settings / FeatureFlags

Derived indexes: last active session, unread state, vector association keys.

---

## API Integration
Connects to BUDDY Core via:
* **WebSocket**: streaming assistant responses, presence, live events
* **REST**: /chat, /reminders, /status, /car/voice (future cross-platform reuse)
* **Admin (optional)**: secure config where device authorized
* **GraphQL (optional)**: aggregated query for dashboard views

---

## Security
* End-to-end encryption (conversation payload before persistence optional toggle)  
* Biometric authentication (Face ID / Touch ID / Fingerprint)  
* Secure key storage (Keychain / Keystore)  
* Certificate pinning (static + TOFU fallback strategy)  
* Encrypted SQLite (SQLCipher or platform equivalent)  
* Realm encryption key managed via secure store  
* Privacy dashboard: export & delete personal data (Phase 3)  

---

## Phase-Wise Roadmap

### Phase 1 – MVP (Core Foundation)
🎯 Goal: Working cross-platform app with essential offline + online sync.
* Base project (React Native primary) & module scaffolding
* Voice input (native APIs) & mic UX
* Minimal chat UI (text + incoming message stream)
* SQLite for offline conversation history
* Realm Sync → MongoDB Atlas basic integration
* WebSocket bridge to Core backend
* Local DB encryption + secure key storage

✅ Outcome: Basic offline conversations + cloud sync + text/voice chat.

### Phase 2 – Beta (Cross-Device Intelligence)
🎯 Goal: Add intelligence, middleware alignment, proactive assistant features.
* Middleware alignment (NLPBridge / ContextBridge / SafetyBridge)
* Context storage & sync to Pinecone refs
* Session recall on app launch
* Notifications: APNs + FCM with interactive actions
* Background services (Headless JS / Isolate) for reminders & sync
* Siri Shortcuts & Android Assistant Actions
* Home/lock screen widgets
* Biometric auth gating sensitive history
* Certificate pinning enforcement

✅ Outcome: Context-aware, safe, proactive assistant.

### Phase 3 – Release (Polished, Enterprise-Ready)
🎯 Goal: Production-grade assistant with full UX, scalability, and distribution.
* Floating mic overlay (push-to-talk everywhere)
* Multi-modal input (voice + text + quick intents)
* Adaptive UI (dark mode, accessibility, reduced motion)
* Conflict resolution strategy (Realm merges / CRDT semantics)
* AI memory persistence (MongoDB + Pinecone synergy) & purge controls
* Offline operation queue with exponential retry & backoff
* Proactive nudges (travel time, reminders, daily brief)
* Cross-device state sync (phone ↔ tablet ↔ desktop ↔ car)
* E2E encryption hardening (Secure Enclave / TEE integration)
* Privacy dashboard (data control + transparency logs)
* CI/CD: TestFlight + Internal App Sharing + staged rollout
* Telemetry (privacy-first; local aggregation before upload)

✅ Outcome: Fully functional, secure, proactive BUDDY Mobile 2.0 ready for distribution.

---

## Visual Roadmap Summary
```
MVP     → Core chat + voice + offline DB + sync
Beta    → Middleware alignment + context + proactive features
Release → Advanced UX + secure memory + enterprise-ready app
```

---

## 📐 High-Level Mobile Architecture (BUDDY 2.0)
```
+------------------------------------------------------+
|                   📱 Mobile UI Layer                 |
|------------------------------------------------------|
| - Chat Interface (Text + Voice)                      |
| - Floating Mic Overlay (PTT)                         |
| - Notifications & Widgets                            |
| - Contextual Suggestions                             |
+------------------------------------------------------+
											|
											v
+------------------------------------------------------+
|              🧩 Middleware Layer (Shared)             |
|------------------------------------------------------|
| - NLPBridge       → Routes speech/text → Core NLP     |
| - ContextBridge   → Stores + fetches AI memory        |
| - SafetyBridge    → Filters unsafe/duplicate actions  |
| - SyncManager     → Handles offline → cloud sync      |
| - AuthManager     → Biometric + Token security        |
+------------------------------------------------------+
											|
											v
+------------------------------------------------------+
|                💾 Local Storage Layer                 |
|------------------------------------------------------|
| - SQLite (Conversations, Preferences)                |
| - Realm (Offline-first DB + Sync Queue)              |
| - Secure Storage (Keychain / Keystore)               |
+------------------------------------------------------+
											|
											v
+------------------------------------------------------+
|                🧠 Core Runtime Layer                  |
|------------------------------------------------------|
| - Voice Engine (STT/TTS native)                      |
| - WebSocket Manager (Real-time BUDDY link)           |
| - REST/GraphQL Client (Data operations)              |
| - Encryption Engine (E2E Secure Messaging)           |
+------------------------------------------------------+
											|
											v
+------------------------------------------------------+
|                   ☁ Cloud / Backend                  |
|------------------------------------------------------|
| - BUDDY Core Brain (AI + Middleware API)             |
| - MongoDB Atlas (Global DB + Realm Sync)             |
| - Pinecone (Context/Vector Memory Store)             |
| - Firebase (Notifications, Presence)                 |
| - Analytics + Monitoring                             |
+------------------------------------------------------+
```

---

## 🔄 Flow Example (Voice Command → Action → Response)
1. User speaks → captured by UI mic overlay.  
2. Audio → Middleware (NLPBridge + SafetyBridge).  
3. Middleware logs + stores locally (SQLite / Realm) & queues sync.  
4. Request → Core Runtime (WebSocket) → BUDDY Core.  
5. Core queries MongoDB + Pinecone for enriched context.  
6. Response streams back → Middleware (context update) → UI.  
7. UI renders text + triggers TTS playback.  
8. Presence + sync updates propagate (Firebase + Realm).  

---

## Repository Folder Mapping (Proposed Mobile Structure)
```
apps/mobile/
	ui/                # React Native screens, components
	middleware/        # Bridges (NLPBridge, ContextBridge, SafetyBridge, SyncManager)
	db/                # Realm models, SQLite schema, migrations
	core/              # WebSocket client, REST client, voice abstraction
	security/          # Key management, encryption helpers
	services/          # Notifications, widgets, background tasks
	state/             # Recoil/Zustand/Redux store modules
	tests/             # Jest / Detox tests
	scripts/           # Build, release, codegen
```

---

## Next Implementation Priorities
1. Scaffold folder structure + baseline TypeScript config.  
2. Establish WebSocket + minimal chat screen (text only).  
3. Add voice capture & streaming hook.  
4. Integrate Realm models + basic sync events.  
5. Introduce middleware bridges (feature toggled).  

---

## Gap → Solution → Benefit Matrix

| Gap / Missing | How to Implement | Benefit |
| ------------- | ---------------- | ------- |
| Middleware alignment | `middleware/` bridges mirroring automotive core (NLP, Context, Safety) | Consistent intent & safety rules across phone/car/desktop |
| Offline-first sync strategy | Conflict resolver (LWV + semantic merge); CRDT-style tombstones for deletes | Prevents data loss, deterministic merges |
| Push-to-talk UX | Floating mic overlay (RN native module / Flutter overlay) + gesture (press, hold, slide cancel) | Frictionless voice access |
| Background service | Headless JS (Android), iOS BGTasks + silent pushes; task scheduler wrapper | Proactive reminders & sync when app closed |
| Cross-device state sync | Session/context bootstrap endpoint + Pinecone vector pull + incremental diff tokens | Seamless multi-device continuity |
| Advanced notifications | Action buttons (reply, snooze), deep links, inline quick intents | Higher engagement, faster actions |
| Analytics & telemetry | Local event buffer → privacy filter → batched encrypted upload | Insight without raw PII leakage |
| Security deepening | Secure Enclave / TEE key ops, per-record envelope encryption, attestation | Strong defense for memory & prefs |
| App store deploy pipeline | GitHub Actions + Fastlane + Gradle Play Publisher + automated screenshots | Faster, reliable releases |

---

## Detailed Implementation Specs

### 1. Middleware Bridges
Files (proposed):
```
middleware/
	nlp_bridge.ts        // Handles text/voice intent dispatch → backend / local rules
	context_bridge.ts    // Local context aggregation + vector references
	safety_bridge.ts     // Applies safety policies (driving, distraction, rate limits)
	bridge_registry.ts   // Extensible hook registration
```
Contract (TypeScript):
```ts
export interface IntentPayload { type: string; text: string; entities?: any; ts: number; }
export interface ContextSnapshot { recentMessages: string[]; driving?: boolean; speedKmh?: number; location?: any; }
export interface BridgeResult { intent: IntentPayload; blocked?: boolean; reason?: string; enriched?: any; }
```
Flow: UI → voice_service (STT) → nlp_bridge.detectIntent → safety_bridge.guard → context_bridge.attach → dispatch.

### 2. Conflict Resolution Strategy
Levels:
* Field-level LWW (timestamp) for simple scalar fields.
* List merges: union by deterministic key; preserve order using vector clock or hybrid logical timestamp (HLT).
* Conversation messages: immutable append; conflicts only on edits (rare) → keep both with edit lineage.
* Deletions: tombstone with `deleted_at`; garbage collect after T(gc) when fully synced to cloud.
Pseudo:
```ts
function resolve(local, remote){
	if(local.deleted_at && !remote.deleted_at) return local; // preserve deletion
	if(remote.deleted_at && !local.deleted_at) return remote;
	return (local.updated_at >= remote.updated_at) ? local : remote;
}
```

### 3. Push‑to‑Talk Overlay
Native module exposing always-on bubble:
* Android: Foreground service + System Alert Window (if needed) or in-app overlay.
* iOS: Use window scene overlay; restrict background mic (policy compliance).
States: Idle → Armed (press) → Capturing → Releasing (transcribe) → Result.
Accessibility: Haptic on start/stop; color contrast; voice guidance optional.

### 4. Background Services
Tasks:
* Reminder check (every 15 min or push-triggered)
* Sync flush (on connectivity regained)
* Vector prefetch (low-power & Wi‑Fi only)
Scheduling abstraction:
```ts
interface BackgroundTask { id: string; run(ctx: TaskContext): Promise<void>; constraints?: ConstraintSet }
```
iOS: BGAppRefreshTask + silent push topics.
Android: WorkManager wrapper + Headless JS entry point.

### 5. Cross-Device State Sync
Bootstrap sequence:
1. Auth handshake → acquire session token.
2. Fetch `/status` & `/admin/semantic-memory/config` (if authorized) to tune client memory.
3. Pull `since=<last_sync_ts>` conversation diff.
4. Pull vector IDs → fetch top-K embeddings metadata (lazy load vectors when needed).
5. Rehydrate context cache; schedule prefetch for frequently accessed threads.

### 6. Advanced Notifications
* Categories: REMINDER, SUGGESTION, CONTEXT_RESUME.
* Actions: REPLY (inline), SNOOZE (5/15/60), DISMISS.
* Deep link URIs: `buddy://chat?session=abc`.
* Rate limiting: Max N proactive suggestions per 6h window.
* Personalization: Local scoring model (lightweight logistic) selects candidate reminders.

### 7. Analytics & Telemetry (Privacy-First)
Event pipeline:
```
UI → event_bus → local_ring_buffer (encrypted) → batch(60s or 25 events) → privacy_filter(redact PII) → encrypt(session_key) → upload
```
Core events: `voice.start`, `voice.end`, `intent.detected`, `intent.blocked`, `sync.flush`, `notif.delivered`, `notif.action`.
Config flags: `ANALYTICS_ENABLED`, `PII_STRIP_MODE`.

### 8. Security Hardening
Key hierarchy:
* Root device key (Secure Enclave / TEE) → wraps data encryption key (DEK).
* DEK → encrypts local DB pages + message payloads.
* Per-conversation ephemeral key (rotated weekly) optional.
Metadata separation: Sensitive payload separated from indexes to reduce attack surface.
Attestation: On startup send signed nonce (TEE signature) to backend for device trust scoring.

### 9. CI/CD Pipeline
GitHub Actions jobs:
* `lint_test` (ESLint / TypeCheck / Jest)
* `build_ios` (Fastlane gym + artifact)
* `build_android` (Gradle assemble + bundle)
* `e2e` (Detox headless / Firebase Test Lab)
* `deploy_beta` (Fastlane pilot + Play internal track)
Cache: Node, Pods, Gradle wrappers.
Secrets: Stored in GitHub OIDC -> cloud secret manager.

### 10. Data Models (Simplified)
```ts
type Message = { id: string; session_id: string; role: 'user'|'assistant'; text: string; ts: number; vector_ref?: string; deleted_at?: number };
type Reminder = { id: string; title: string; due_ts: number; completed_ts?: number; deleted_at?: number; updated_at: number };
type SyncCursor = { last_conversation_ts: number; last_vector_pull: number };
```

### 11. Offline Sync State Machine
States: `IDLE` → `QUEUEING` → `FLUSHING` → (`PARTIAL_FAIL`|`SUCCESS`) → `IDLE`.
Retry backoff: 2^n seconds capped at 15m.
Failure categories: transient (network), permanent (auth), conflict (resolve then retry).

### 12. Testing Strategy
Pyramid:
* Unit: bridges, conflict resolver, encryption wrapper.
* Integration: WebSocket session handshake, sync flush, notification action flows.
* E2E: Detox (RN) scenario scripts (voice mock → intent → UI assertion).
* Security tests: key storage, tamper attempt (simulated), encryption correctness.
Coverage goals: ≥80% lines bridges & sync.

### 13. Performance Budgets
* Cold start (RN): < 2.5s (mid-tier device)
* Voice capture latency to intent display: < 1200ms (local STT), < 2500ms (cloud)
* Sync flush batch size: ≤ 50 messages or 128KB
* Battery: background tasks ≤ 1% / hour while active sync window.

### 14. Observability
Local log levels: INFO default, DEBUG behind dev flag.
Crash reporting: Platform Crash + optional Sentry (PII off).
Health beacons: periodic lightweight ping if user opted-in.

### 15. Privacy Considerations
* User can purge conversation (secure erase) → key shredding.
* Data minimization: Only hashed device ID sent for analytics linking.
* Transparent log: Local privacy dashboard enumerates stored categories.

### 16. Future Extensions
* Federated on-device fine-tuning (opt-in)
* Adaptive acoustic model personalization
* Multi-modal (image & sensor context) augmentation
* Car handoff continuity (session resume from `/car/voice`).

---

## Notes
This blueprint is a living document; update as backend endpoints (/car/voice, semantic memory enhancements) evolve. Align with automotive middleware for future cross-device continuity.

---

## Changelog
* Added unified roadmap & architecture diagram (2025-08-26)
* Original README content merged & restructured

