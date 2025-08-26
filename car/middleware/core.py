"""Automotive Middleware Core Orchestrator.
Coordinates voice -> NLP -> context -> safety -> action -> cloud.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any

from .voice.engine import VoiceEngine
from .nlp.processor import NLPProcessor
from .context.manager import ContextManager
from .safety.manager import SafetyManager
from .integration.vehicle import VehicleIntegrationHub
from .navigation.manager import NavigationManager
from .media.controller import MediaController
from .diagnostics.manager import DiagnosticsManager
from .cloud_bridge.bridge import CloudBridge
from .plugins import registry as plugin_registry

@dataclass
class MiddlewareConfig:
    enable_wake_word: bool = True
    safe_speed_threshold_kmh: float = 5.0
    offline_mode: bool = False
    allow_experimental: bool = False

class AutomotiveMiddlewareCore:
    def __init__(self, config: MiddlewareConfig | None = None):
        self.config = config or MiddlewareConfig()
        self.voiceEngine = VoiceEngine(self.config)
        self.contextManager = ContextManager(self.config)
        self.nlpProcessor = NLPProcessor(self.config)
        self.safetyManager = SafetyManager(self.config)
        self.integrationHub = VehicleIntegrationHub(self.config)
        self.navigationManager = NavigationManager(self.config)
        self.mediaController = MediaController(self.config)
        self.diagnosticsManager = DiagnosticsManager(self.config)
        self.cloudBridge = CloudBridge(self.config)

    async def initialize(self):
        await self.voiceEngine.initialize()
        await self.contextManager.initialize()
        await self.cloudBridge.initialize()

    async def handle_user_input(self, audio: bytes | None = None, text: str | None = None, meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
        meta = meta or {}
        if audio and not text:
            text = await self.voiceEngine.speech_to_text(audio)
        if not text:
            return {"error": "no_input"}
        ctx = await self.contextManager.build_context(meta)
        intent = await self.nlpProcessor.detect_intent(text, ctx)
        safety = await self.safetyManager.validate_intent(intent, ctx)
        if not safety.get("allowed", True):
            response = safety.get("message", "Action blocked for safety.")
            tts = await self.voiceEngine.text_to_speech(response)
            return {"blocked": True, "response": response, "tts": tts, "intent": intent}
        action_result = await self._route_intent(intent, ctx)
        await self.cloudBridge.sync_interaction(intent, action_result, ctx)
        if isinstance(action_result, dict) and 'spoken' in action_result:
            tts_text = action_result['spoken']
        else:
            tts_text = action_result.get('response', 'Done.') if isinstance(action_result, dict) else str(action_result)
        tts_audio = await self.voiceEngine.text_to_speech(tts_text)
        return {"intent": intent, "result": action_result, "tts": tts_audio}

    async def _route_intent(self, intent: Dict[str, Any], ctx: Dict[str, Any]):
        itype = intent.get('type')
        if itype == 'navigation.route':
            return await self.navigationManager.get_route(intent, ctx)
        if itype == 'media.play':
            return await self.mediaController.play_media(intent, ctx)
        if itype == 'vehicle.climate':
            return await self.integrationHub.set_climate(intent, ctx)
        if itype == 'vehicle.diagnostics':
            return await self.diagnosticsManager.read_status(intent, ctx)
        # Plugin override path
        if not isinstance(itype, str):
            return {"response": "Invalid intent type", "type": itype}
        plugin = plugin_registry.get(itype)
        if plugin:
            return await plugin(intent, ctx)
        return {"response": "Intent not implemented", "type": itype}

    def register_plugin(self, intent_type: str, handler, override: bool = False):
        """Convenience passthrough to shared registry."""
        plugin_registry.register(intent_type, handler, override=override)

