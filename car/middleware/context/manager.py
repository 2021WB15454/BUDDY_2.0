"""ContextManager stub collects driving state, location, time."""
from datetime import datetime
from typing import Dict, Any

class ContextManager:
    def __init__(self, config):
        self.config = config

    async def initialize(self):
        return True

    async def build_context(self, meta: Dict[str, Any]) -> Dict[str, Any]:
        speed = meta.get("speed_kmh", 0.0)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "speed_kmh": speed,
            "driving": speed > self.config.safe_speed_threshold_kmh,
            "location": meta.get("location"),
            "source": meta.get("source", "api"),
        }

