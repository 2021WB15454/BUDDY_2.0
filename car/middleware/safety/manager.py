"""SafetyManager stub enforcing distraction rules."""
from typing import Dict, Any
import os
import random

class SpeedSource:
    """Abstraction to fetch current speed (km/h). For now we simulate or read env."""
    def __init__(self):
        self.mode = os.getenv("BUDDY_SPEED_SOURCE", "sim")  # sim | env

    async def get_speed(self) -> float:
        if self.mode == "env":  # Pull from env var (updated externally)
            try:
                return float(os.getenv("BUDDY_VEHICLE_SPEED_KMH", "0"))
            except ValueError:
                return 0.0
        # Simulation: random gentle variation
        return max(0.0, random.gauss(35, 5))

class SafetyManager:
    def __init__(self, config):
        self.config = config
        self.speed_source = SpeedSource()

    async def validate_intent(self, intent: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        speed = context.get("speed_kmh")
        if speed is None:  # fetch fresh if context builder didn't supply
            speed = await self.speed_source.get_speed()
            context["speed_kmh"] = speed
            context["driving"] = speed > self.config.safe_speed_threshold_kmh
        driving = context.get("driving")
        itype = intent.get("type")
        # Disallow certain manual-text intents while moving
        restricted = {"general.chat"}
        if driving and itype in restricted:
            return {"allowed": False, "message": "Action blocked while vehicle moving. Use brief voice commands."}
        return {"allowed": True, "speed": speed}

