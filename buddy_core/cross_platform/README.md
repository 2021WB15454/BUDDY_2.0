# Cross-Platform Intelligence Core (Preview)

This directory contains early scaffolding for the unified BUDDY intelligence layer delivering a consistent JARVIS-like experience across devices (mobile, desktop, watch, tv, car, web).

## Components

- `intelligence_core.py`: Orchestrates personality, memory retrieval, platform adaptation, and voice/UI hints.
- `sync_engine.py`: Placeholder multi-device sync engine for broadcasting context updates.

## Next Steps

1. Integrate with existing FastAPI backend endpoint (e.g. `/chat/universal`).
2. Expand intent classification + plug in LLM when available.
3. Replace heuristic memory summary with semantic clustering/LLM compression.
4. Implement real pub/sub (Redis streams, NATS, or WebSocket hub) in `BUDDYSyncEngine.push_update`.
5. Add device registration & auth scoping by user/device tokens.
6. Provide platform SDK shims (React Native, Electron, watchOS, CarPlay, Smart TV) calling a universal endpoint.
7. Add cross-platform consistency tests (personality style, adaptation constraints per device).

## Usage Sketch

```python
from buddy_core.cross_platform.intelligence_core import intelligence_core_singleton, PlatformContext

ctx = PlatformContext(device_type='mobile', platform='android', user_id='user123', capabilities={'has_voice': True})
result = await intelligence_core_singleton.process_universal_input('Schedule a meeting tomorrow at 3pm', ctx)
print(result.response, result.ui_adaptations)
```

## Disclaimer
Experimental scaffolding – not production-ready. Functions marked as placeholders should be expanded with full logic, error handling, and observability.
