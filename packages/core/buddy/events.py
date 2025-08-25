"""
BUDDY Event Bus

A lightweight publish-subscribe event system for coordinating between
all BUDDY components. Handles event routing, filtering, and delivery
with support for async/await patterns.
"""

import asyncio
import logging
import json
from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Represents a single event in the BUDDY system."""
    
    topic: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "unknown"
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "topic": self.topic,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "event_id": self.event_id,
            "source": self.source,
            "correlation_id": self.correlation_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary."""
        return cls(
            topic=data["topic"],
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_id=data["event_id"],
            source=data["source"],
            correlation_id=data.get("correlation_id")
        )


class EventBus:
    """
    Central event bus for BUDDY system.
    
    Provides publish-subscribe messaging with topic-based routing,
    async/await support, and event persistence for debugging.
    """
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._running = False
        
    async def start(self):
        """Start the event bus."""
        self._running = True
        logger.info("Event bus started")
        
    async def stop(self):
        """Stop the event bus."""
        self._running = False
        logger.info("Event bus stopped")
        
    def subscribe(self, topic: str, handler: Callable):
        """
        Subscribe to events on a specific topic.
        
        Args:
            topic: Topic pattern to subscribe to (supports wildcards)
            handler: Async function to call when events match
        """
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)
        logger.debug(f"Subscribed to topic: {topic}")
        
    def unsubscribe(self, topic: str, handler: Callable):
        """
        Unsubscribe from a topic.
        
        Args:
            topic: Topic to unsubscribe from
            handler: Handler function to remove
        """
        if topic in self._subscribers:
            try:
                self._subscribers[topic].remove(handler)
                if not self._subscribers[topic]:
                    del self._subscribers[topic]
                logger.debug(f"Unsubscribed from topic: {topic}")
            except ValueError:
                logger.warning(f"Handler not found for topic: {topic}")
                
    async def publish(self, topic: str, payload: Dict[str, Any], 
                     source: str = "unknown", correlation_id: Optional[str] = None):
        """
        Publish an event to the bus.
        
        Args:
            topic: Event topic
            payload: Event data
            source: Source component name
            correlation_id: Optional correlation ID for tracking
        """
        if not self._running:
            logger.warning("Event bus not running, dropping event")
            return
            
        event = Event(
            topic=topic,
            payload=payload,
            source=source,
            correlation_id=correlation_id
        )
        
        # Store in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
            
        # Find matching subscribers
        matching_handlers = []
        for sub_topic, handlers in self._subscribers.items():
            if self._topic_matches(topic, sub_topic):
                matching_handlers.extend(handlers)
                
        # Deliver to subscribers
        if matching_handlers:
            logger.debug(f"Publishing event {event.event_id} to {len(matching_handlers)} handlers")
            await asyncio.gather(
                *[self._safe_call_handler(handler, event) for handler in matching_handlers],
                return_exceptions=True
            )
        else:
            logger.debug(f"No subscribers for topic: {topic}")
            
    def _topic_matches(self, event_topic: str, subscription_topic: str) -> bool:
        """
        Check if an event topic matches a subscription pattern.
        
        Supports wildcards:
        - * matches any single segment
        - ** matches any number of segments
        """
        if subscription_topic == event_topic:
            return True
            
        # Convert to regex-like matching
        if "*" in subscription_topic:
            import re
            pattern = subscription_topic.replace("**", ".*").replace("*", "[^.]*")
            return bool(re.match(f"^{pattern}$", event_topic))
            
        return False
        
    async def _safe_call_handler(self, handler: Callable, event: Event):
        """Safely call an event handler with error catching."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
        except Exception as e:
            logger.error(f"Error in event handler for {event.topic}: {e}")
            
    def get_recent_events(self, limit: int = 100, topic_filter: Optional[str] = None) -> List[Event]:
        """
        Get recent events from history.
        
        Args:
            limit: Maximum number of events to return
            topic_filter: Optional topic pattern to filter by
            
        Returns:
            List of recent events
        """
        events = self._event_history[-limit:]
        
        if topic_filter:
            events = [e for e in events if self._topic_matches(e.topic, topic_filter)]
            
        return events
        
    def clear_history(self):
        """Clear event history."""
        self._event_history.clear()
        logger.info("Event history cleared")


# Global event bus instance
_global_bus = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


async def publish(topic: str, payload: Dict[str, Any], source: str = "unknown"):
    """Convenience function to publish to global event bus."""
    bus = get_event_bus()
    await bus.publish(topic, payload, source)


def subscribe(topic: str):
    """Decorator for subscribing functions to events."""
    def decorator(func):
        bus = get_event_bus()
        bus.subscribe(topic, func)
        return func
    return decorator
