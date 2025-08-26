"""NLPProcessor stub for intent + entity extraction."""
from typing import Dict, Any

class NLPProcessor:
    def __init__(self, config):
        self.config = config

    async def detect_intent(self, text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        # Simple rule-based placeholder
        if any(k in text.lower() for k in ["route", "navigate", "go to"]):
            return {"type": "navigation.route", "raw": text}
        if any(k in text.lower() for k in ["play", "music", "song"]):
            return {"type": "media.play", "raw": text}
        if "temperature" in text.lower():
            return {"type": "vehicle.climate", "raw": text}
        if "diagnostic" in text.lower() or "engine" in text.lower():
            return {"type": "vehicle.diagnostics", "raw": text}
        return {"type": "general.chat", "raw": text}
