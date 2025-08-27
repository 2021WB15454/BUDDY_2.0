"""Cross-Platform BUDDY Intelligence Core (Foundational Skeleton)

Provides a unified interface for platform-specific clients (mobile, desktop, watch, tv, car, web)
while sharing personality, memory, context, and response generation logic.

This is an initial scaffold; many functions are stubs intended to be expanded.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Iterable
from dataclasses import dataclass, field
from datetime import datetime
import time
from collections import deque

try:
    from buddy_core.personality.buddy_personality import personality_singleton as _personality
    from buddy_core.intelligence.buddy_intelligence import BUDDYIntelligenceEngine
    from buddy_core.voice.voice_processor import voice_processor_singleton as _voice
except Exception:  # fallback stubs
    _personality = None  # type: ignore
    _voice = None  # type: ignore
    BUDDYIntelligenceEngine = object  # type: ignore

try:
    from packages.core.buddy.memory.memory_service import memory_service as _memory_service
except Exception:
    _memory_service = None  # type: ignore

# Optional summarizer plugin
class AbstractMemorySummarizer:
    async def summarize(self, texts: List[str], max_len: int = 400) -> str:  # pragma: no cover - interface
        raise NotImplementedError

class HeuristicMemorySummarizer(AbstractMemorySummarizer):
    async def summarize(self, texts: List[str], max_len: int = 400) -> str:
        seen: set[str] = set()
        ordered: List[str] = []
        for t in texts:
            if not t:
                continue
            frag = ' '.join(t.strip().split())[:120]
            k = frag.lower()
            if k in seen:
                continue
            seen.add(k)
            ordered.append(frag)
            if len(ordered) >= 6:
                break
        return ' | '.join(ordered)[:max_len]

try:  # LLM-based optional summarizer (OpenAI) with thread offload
    import openai  # type: ignore
    class OpenAIMemorySummarizer(AbstractMemorySummarizer):  # pragma: no cover - network
        async def summarize(self, texts: List[str], max_len: int = 400) -> str:
            if not texts:
                return ''
            joined = '\n'.join(texts)[:2000]
            client = openai.OpenAI()
            import asyncio
            def _run():
                try:
                    resp = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": "Summarize user-specific memory snippets succinctly"},
                            {"role": "user", "content": joined}
                        ],
                        max_tokens=150
                    )
                    return resp.choices[0].message.content or ''
                except Exception:
                    return joined[:max_len]
            content = await asyncio.to_thread(_run)
            return content[:max_len]
    _default_summarizer: AbstractMemorySummarizer = OpenAIMemorySummarizer()
except Exception:
    _default_summarizer = HeuristicMemorySummarizer()

from .pubsub import pubsub

# ---------------------------------------------------------------------------
# Data Contracts
# ---------------------------------------------------------------------------
@dataclass
class PlatformContext:
    device_type: str
    platform: str
    capabilities: Dict[str, Any] = field(default_factory=dict)
    user_id: str = "default"
    locale: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class IntelligenceResult:
    response: str
    personality: str
    platform_optimized: bool
    sync_completed: bool
    voice_config: Optional[Dict[str, Any]] = None
    ui_adaptations: Optional[Dict[str, Any]] = None
    raw_intent: Optional[Dict[str, Any]] = None
    memory_summary: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

# ---------------------------------------------------------------------------
# Core Intelligence Engine Wrapper
# ---------------------------------------------------------------------------
class BUDDYIntelligenceCore:
    """Shared intelligence orchestration across platforms."""

    def __init__(self):
        self.personality = _personality
        self.voice_processor = _voice
        self.memory_summarizer = _default_summarizer
        # rolling latency metrics (thread-safe enough for asyncio single-thread usage)
        self._summary_latencies = deque(maxlen=500)
        self._publish_latencies = deque(maxlen=500)

    # Public API -------------------------------------------------------------
    async def process_universal_input(self, user_input: str, platform_ctx: PlatformContext) -> IntelligenceResult:
        intent = await self.analyze_cross_platform_intent(user_input, platform_ctx)
        base_response = await self.generate_platform_response(user_input, intent, platform_ctx)
        persona_response = await self.apply_universal_personality(base_response, platform_ctx, intent)
        memory_summary = intent.get('memory_summary') if isinstance(intent, dict) else None
        await self.sync_context_across_devices(platform_ctx.user_id, user_input, persona_response, intent, platform_ctx)
        voice_conf = await self.get_platform_voice_config(platform_ctx)
        ui_adapt = await self.get_ui_adaptations(platform_ctx, intent)
        return IntelligenceResult(
            response=persona_response,
            personality="buddy_jarvis_style",
            platform_optimized=True,
            sync_completed=True,
            voice_config=voice_conf,
            ui_adaptations=ui_adapt,
            raw_intent=intent,
            memory_summary=memory_summary
        )

    # Intent & Memory -------------------------------------------------------
    async def analyze_cross_platform_intent(self, text: str, platform_ctx: PlatformContext) -> Dict[str, Any]:
        intent: Dict[str, Any] = {"raw": text, "device_type": platform_ctx.device_type}
        lower = text.lower()
        # Category detection
        categories = {
            'reminder': ["remind", "schedule", "calendar", "meeting", "appointment"],
            'weather': ["weather", "temperature", "forecast"],
            'navigation': ["navigate", "route", "directions", "traffic"],
            'entertainment': ["play", "music", "song", "video", "movie"],
            'system': ["battery", "storage", "cpu", "memory usage"],
            'health': ["heart rate", "steps", "calories"]
        }
        for cat, keys in categories.items():
            if any(k in lower for k in keys):
                intent['category'] = cat
                break
        intent.setdefault('category', 'general')
        # Flags
        if any(k in lower for k in ("video", "image", "graph")):
            intent['visual_requirement'] = True
        if platform_ctx.device_type == 'car' and intent.get('visual_requirement'):
            intent['restricted_visual'] = True
        # Memory retrieval + summarization
        if _memory_service:
            try:
                ranked = await _memory_service.retrieve(platform_ctx.user_id, text, top_k=8)
                if ranked:
                    intent['memories'] = ranked
                    texts = [r.get('text','') for r in ranked]
                    t0 = time.perf_counter()
                    summary = await self.memory_summarizer.summarize(texts, max_len=400)
                    elapsed_ms = int((time.perf_counter() - t0)*1000)
                    intent['memory_summary'] = summary
                    intent['memory_summary_ms'] = elapsed_ms
                    self._summary_latencies.append(elapsed_ms)
            except Exception:
                pass
        return intent

    # Response Generation ---------------------------------------------------
    async def generate_platform_response(self, user_input: str, intent: Dict[str, Any], platform_ctx: PlatformContext) -> str:
        base = await self._base_response(user_input, intent, platform_ctx)
        adapter = BUDDYPlatformAdapter()
        dt = platform_ctx.device_type
        caps = platform_ctx.capabilities
        if dt == 'mobile':
            return await adapter.adapt_for_mobile(base, caps)
        if dt == 'desktop':
            return await adapter.adapt_for_desktop(base, caps)
        if dt == 'watch':
            return await adapter.adapt_for_watch(base, caps)
        if dt == 'tv':
            return await adapter.adapt_for_tv(base, caps)
        if dt == 'car':
            return await adapter.adapt_for_car(base, caps)
        if dt == 'web':
            return await adapter.adapt_for_web(base, caps)
        return base

    async def _base_response(self, user_input: str, intent: Dict[str, Any], platform_ctx: PlatformContext) -> str:
        # Use personality engine if available
        if BUDDYIntelligenceEngine != object and self.personality:
            try:
                engine = BUDDYIntelligenceEngine()  # type: ignore
                if hasattr(engine, 'generate_buddy_response'):
                    return await engine.generate_buddy_response(user_input, {"intent": intent})  # type: ignore
            except Exception:
                pass
        # fallback simple echo
        return f"You said: {user_input}"[:500]

    # Personality Application -----------------------------------------------
    async def apply_universal_personality(self, response: str, platform_ctx: PlatformContext, intent: Dict[str, Any]) -> str:
        if not self.personality:
            return response
        # Simple augmentation pattern
        traits = ["precision", "proactivity"]
        tagged = f"{response}\n\n[BUDDY:{','.join(traits)};device={platform_ctx.device_type}]"
        if intent.get('memory_summary'):
            tagged += f"\nContext: {intent['memory_summary']}"
        if platform_ctx.device_type == 'car':
            # Safety disclaimers and trimming
            tagged = tagged.split('\n')[0][:180]
            tagged += "\n(Driving mode: focusing on essentials.)"
            if intent.get('restricted_visual'):
                tagged += " Visual content deferred until safe."  # no images while driving
        return tagged[:1000]

    # Cross-Device Sync -----------------------------------------------------
    async def sync_context_across_devices(self, user_id: str, user_input: str, response: str, intent: Dict[str, Any], platform_ctx: PlatformContext) -> None:
        # Publish lightweight sync event via in-process pubsub (extend to external broker later)
        payload = {
            'user_id': user_id,
            'device_type': platform_ctx.device_type,
            'snippet': response[:160],
            'category': intent.get('category'),
            'ts': datetime.utcnow().isoformat()
        }
        t0 = time.perf_counter()
        await pubsub.publish(user_id, payload)
        pub_ms = int((time.perf_counter() - t0)*1000)
        intent['publish_latency_ms'] = pub_ms
        self._publish_latencies.append(pub_ms)
        return

    # Metrics exposure -----------------------------------------------------
    def metrics_snapshot(self) -> Dict[str, Any]:
        def _stats(data: deque) -> Dict[str, Any]:
            if not data:
                return {"count": 0, "avg_ms": 0, "p95_ms": 0, "max_ms": 0}
            arr = list(data)
            arr_sorted = sorted(arr)
            p95 = arr_sorted[int(0.95 * (len(arr_sorted)-1))]
            return {
                "count": len(arr),
                "avg_ms": sum(arr)/len(arr),
                "p95_ms": p95,
                "max_ms": max(arr)
            }
        return {
            "memory_summary_latency": _stats(self._summary_latencies),
            "publish_latency": _stats(self._publish_latencies),
            "timestamp": datetime.utcnow().isoformat()
        }

    # Voice Config ----------------------------------------------------------
    async def get_platform_voice_config(self, platform_ctx: PlatformContext) -> Optional[Dict[str, Any]]:
        if not self.voice_processor:
            return None
        base = {"voice": "buddy_neutral", "pace": 1.0, "tone": "confident_helpful"}
        dt = platform_ctx.device_type
        if dt == 'watch':
            base.update({"pace": 0.9, "projection": "close"})
        elif dt == 'car':
            base.update({"pace": 0.85, "clarity": "max", "safety_filtered": True})
        elif dt == 'tv':
            base.update({"projection": "room"})
        return base

    # UI Adaptations --------------------------------------------------------
    async def get_ui_adaptations(self, platform_ctx: PlatformContext, intent: Dict[str, Any]) -> Dict[str, Any]:
        dt = platform_ctx.device_type
        adapts: Dict[str, Any] = {}
        if dt == 'watch':
            adapts['enable_ultra_brief'] = True
            adapts['use_haptic'] = True
        elif dt == 'tv':
            adapts['enable_large_text'] = True
            adapts['show_visual_elements'] = True
        elif dt == 'car':
            adapts['audio_only'] = True
            adapts['safety_mode'] = True
        elif dt == 'desktop':
            adapts['enable_rich_formatting'] = True
        elif dt == 'mobile':
            adapts['concise_mode'] = True
        return adapts

# ---------------------------------------------------------------------------
# Platform Adapter (response shaping per device)
# ---------------------------------------------------------------------------
class BUDDYPlatformAdapter:
    async def adapt_for_mobile(self, response: str, capabilities: Dict[str, Any]) -> str:
        if len(response) > 220:
            summary = response[:160] + '…'
            return f"{summary}\n\nSay 'details' for more."
        return response

    async def adapt_for_desktop(self, response: str, capabilities: Dict[str, Any]) -> str:
        return response  # desktop can show full detail

    async def adapt_for_watch(self, response: str, capabilities: Dict[str, Any]) -> str:
        if len(response) > 60:
            return response[:55] + '…'
        return response

    async def adapt_for_tv(self, response: str, capabilities: Dict[str, Any]) -> str:
        return response + "\n[TV Mode: Visual enhancements available]"

    async def adapt_for_car(self, response: str, capabilities: Dict[str, Any]) -> str:
        # Emphasize brevity and safety
        safe = response.split('\n')[0]
        return (safe[:120] + '…') if len(safe) > 120 else safe

    async def adapt_for_web(self, response: str, capabilities: Dict[str, Any]) -> str:
        return response

# Singleton helper
intelligence_core_singleton = BUDDYIntelligenceCore()
