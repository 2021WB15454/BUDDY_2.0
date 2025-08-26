"""Example usage of the AutomotiveMiddlewareCore."""
import asyncio
from .core import AutomotiveMiddlewareCore, MiddlewareConfig

async def demo():
    core = AutomotiveMiddlewareCore(MiddlewareConfig())
    await core.initialize()
    result = await core.handle_user_input(text="navigate to central park", meta={"speed_kmh": 0})
    print(result)

if __name__ == "__main__":
    asyncio.run(demo())
