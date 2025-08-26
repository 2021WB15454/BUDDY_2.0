# BUDDY Automotive Middleware

Shared core that powers all in-vehicle platform integrations (CarPlay, Android Auto, QNX, GENIVI, Tesla, custom OEM UIs).

## Goals
- Single source of truth for voice→NLP→context→safety→action pipeline
- Edge + cloud hybrid (low-latency safety on device, advanced reasoning in cloud)
- Extensible modules: plug in new intent handlers, vehicle APIs, or ML models
- Deterministic safety gating before any actuator command

## Module Overview
| Module | Responsibility |
|--------|----------------|
| `voice/` | Wake word, ASR, TTS abstraction (offline + cloud fallback) |
| `nlp/` | Intent detection, entity extraction, dialog policies |
| `context/` | Driving state, speed, location, temporal context aggregation |
| `safety/` | Policy + distraction gating, dynamic mode restrictions |
| `integration/` | Vehicle systems (climate, media hardware, phone, CAN/OBD-II) |
| `navigation/` | Routing, rerouting, charging/energy planning |
| `media/` | Playback orchestration (abstracts Spotify, Apple Music, local) |
| `diagnostics/` | Health, battery, fault code surfaces |
| `cloud_bridge/` | Pinecone memory, Firebase sync, external data providers |

## Core Orchestrator
`core.AutomotiveMiddlewareCore` wires modules and exposes:
- `initialize()` — warm up engines / caches
- `handle_user_input(audio|text, meta)` — full pipeline
- Intent routing to specialized managers

## Safety Model
1. Collect context (speed, mode, driver state)
2. Classify intent type
3. Evaluate safety policy (block or allow)
4. Execute only if allowed; otherwise return safe TTS rationale

## Extending
- Add new intent: implement handler, register in `_route_intent`
- Add model: augment `NLPProcessor.detect_intent`
- Add safety rule: extend `SafetyManager.validate_intent`

## Roadmap
- Pluggable ASR providers
- Local embedding memory + vector pruning
- Predictive pre-fetch (navigation + media) based on routine
- Multi-pass reasoning for complex voice tasks

## Testing
Use simulated meta inputs: `{ "speed_kmh": 80, "location": {...} }` to validate safety gating and latency.

