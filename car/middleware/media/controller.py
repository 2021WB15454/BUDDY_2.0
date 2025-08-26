"""MediaController stub for media actions."""
from typing import Dict, Any

class MediaController:
    def __init__(self, config):
        self.config = config

    async def play_media(self, intent: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        return {"response": "Playing media", "spoken": "Playing your music."}
