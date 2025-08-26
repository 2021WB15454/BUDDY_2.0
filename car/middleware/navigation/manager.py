"""NavigationManager stub for route planning."""
from typing import Dict, Any

class NavigationManager:
    def __init__(self, config):
        self.config = config

    async def get_route(self, intent: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {"response": "Calculating route...", "spoken": "Starting navigation."}
