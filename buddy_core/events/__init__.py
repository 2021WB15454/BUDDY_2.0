"""
Event Bus - Central Pub/Sub System for BUDDY Core

Handles all internal communication between modules and external device events.
Supports both in-process and distributed modes (Redis/NATS).
"""

import asyncio
import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class EventPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Event:
    """Core event structure for all BUDDY communications"""
    topic: str
    data: Dict[str, Any]
    device_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    priority: EventPriority = EventPriority.NORMAL
    timestamp: float = None
    event_id: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.event_id is None:
            self.event_id = str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        result = asdict(self)
        result['priority'] = self.priority.value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary"""
        if 'priority' in data and isinstance(data['priority'], int):
            data['priority'] = EventPriority(data['priority'])
        return cls(**data)

class EventBus:
    """
    Central event bus for BUDDY Core
    
    Handles:
    - Message routing between modules
    - Device event coordination
    - Cross-device synchronization events
    - Skill-to-skill communication
    """
    
    def __init__(self, max_queue_size: int = 1000):
        self.max_queue_size = max_queue_size
        self.subscribers: Dict[str, List[Callable]] = {}
        self.event_queue = asyncio.Queue(maxsize=max_queue_size)
        self.running = False
        self.stats = {
            'events_published': 0,
            'events_processed': 0,
            'events_failed': 0,
            'subscribers_count': 0
        }
        
        # Event topics (organized by category)
        self.TOPICS = {
            # UI Events
            'ui.message.in': 'User input message',
            'ui.message.out': 'System response message',
            'ui.voice.start': 'Voice input started',
            'ui.voice.stop': 'Voice input stopped',
            'ui.notification.show': 'Show notification to user',
            
            # Dialogue Events
            'dialogue.intent.detected': 'Intent classification complete',
            'dialogue.context.update': 'Conversation context updated',
            'dialogue.turn.complete': 'Dialogue turn finished',
            
            # Skills Events
            'skill.execute.start': 'Skill execution started',
            'skill.execute.complete': 'Skill execution finished',
            'skill.execute.error': 'Skill execution failed',
            'skill.reminder.create': 'Create new reminder',
            'skill.reminder.fire': 'Reminder triggered',
            'skill.task.create': 'Create new task',
            'skill.task.complete': 'Task completed',
            
            # Memory Events
            'memory.read': 'Memory read operation',
            'memory.write': 'Memory write operation',
            'memory.fact.store': 'Store new fact',
            'memory.fact.recall': 'Recall facts',
            
            # Voice Events
            'voice.asr.start': 'ASR processing started',
            'voice.asr.partial': 'Partial ASR result',
            'voice.asr.complete': 'Final ASR result',
            'voice.tts.request': 'TTS generation requested',
            'voice.tts.complete': 'TTS audio ready',
            
            # Device Events
            'device.connected': 'Device connected',
            'device.disconnected': 'Device disconnected',
            'device.presence.update': 'Device presence changed',
            'device.capability.update': 'Device capabilities changed',
            
            # Sync Events
            'sync.push': 'Push data to sync',
            'sync.pull': 'Pull data from sync',
            'sync.conflict': 'Sync conflict detected',
            'sync.complete': 'Sync operation complete',
            
            # System Events
            'system.startup': 'System starting up',
            'system.shutdown': 'System shutting down',
            'system.error': 'System error occurred',
            'system.health.check': 'Health check requested'
        }
    
    async def start(self):
        """Start the event processing loop"""
        self.running = True
        logger.info("Event bus started")
        
        # Start the event processing task
        asyncio.create_task(self._process_events())
        
        # Emit startup event
        await self.publish('system.startup', {'timestamp': time.time()})
    
    async def stop(self):
        """Stop the event bus"""
        self.running = False
        await self.publish('system.shutdown', {'timestamp': time.time()})
        logger.info("Event bus stopped")
    
    def subscribe(self, topic: str, handler: Callable[[Event], Any]) -> str:
        """
        Subscribe to an event topic
        
        Args:
            topic: Event topic to subscribe to (supports wildcards)
            handler: Async function to handle events
            
        Returns:
            Subscription ID for unsubscribing
        """
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        
        self.subscribers[topic].append(handler)
        self.stats['subscribers_count'] = sum(len(handlers) for handlers in self.subscribers.values())
        
        logger.debug(f"Subscribed to topic '{topic}', total subscribers: {self.stats['subscribers_count']}")
        return f"{topic}:{len(self.subscribers[topic])-1}"
    
    def unsubscribe(self, subscription_id: str):
        """Unsubscribe from an event topic"""
        topic, index = subscription_id.split(':')
        if topic in self.subscribers:
            try:
                del self.subscribers[topic][int(index)]
                self.stats['subscribers_count'] = sum(len(handlers) for handlers in self.subscribers.values())
                logger.debug(f"Unsubscribed from topic '{topic}'")
            except (IndexError, ValueError):
                logger.warning(f"Invalid subscription ID: {subscription_id}")
    
    async def publish(self, topic: str, data: Dict[str, Any], 
                     device_id: Optional[str] = None,
                     user_id: Optional[str] = None,
                     session_id: Optional[str] = None,
                     priority: EventPriority = EventPriority.NORMAL) -> str:
        """
        Publish an event to the bus
        
        Args:
            topic: Event topic
            data: Event data payload
            device_id: Source device ID
            user_id: User ID
            session_id: Session ID
            priority: Event priority
            
        Returns:
            Event ID
        """
        event = Event(
            topic=topic,
            data=data,
            device_id=device_id,
            user_id=user_id,
            session_id=session_id,
            priority=priority
        )
        
        try:
            await self.event_queue.put(event)
            self.stats['events_published'] += 1
            logger.debug(f"Published event {event.event_id} to topic '{topic}'")
            return event.event_id
        except asyncio.QueueFull:
            logger.error(f"Event queue full, dropping event for topic '{topic}'")
            self.stats['events_failed'] += 1
            raise
    
    async def _process_events(self):
        """Main event processing loop"""
        while self.running:
            try:
                # Get event from queue with timeout
                event = await asyncio.wait_for(self.event_queue.get(), timeout=1.0)
                
                # Find matching subscribers
                handlers = self._find_handlers(event.topic)
                
                if handlers:
                    # Process handlers concurrently
                    tasks = []
                    for handler in handlers:
                        if asyncio.iscoroutinefunction(handler):
                            tasks.append(asyncio.create_task(handler(event)))
                        else:
                            # Wrap sync functions
                            tasks.append(asyncio.create_task(self._run_sync_handler(handler, event)))
                    
                    # Wait for all handlers to complete
                    if tasks:
                        try:
                            await asyncio.gather(*tasks, return_exceptions=True)
                            self.stats['events_processed'] += 1
                        except Exception as e:
                            logger.error(f"Error processing event {event.event_id}: {e}")
                            self.stats['events_failed'] += 1
                else:
                    logger.debug(f"No subscribers for topic '{event.topic}'")
                    self.stats['events_processed'] += 1
                
            except asyncio.TimeoutError:
                # No events to process, continue
                continue
            except Exception as e:
                logger.error(f"Event processing error: {e}")
                self.stats['events_failed'] += 1
    
    def _find_handlers(self, topic: str) -> List[Callable]:
        """Find all handlers that match the given topic"""
        handlers = []
        
        # Exact match
        if topic in self.subscribers:
            handlers.extend(self.subscribers[topic])
        
        # Wildcard matching
        for sub_topic, sub_handlers in self.subscribers.items():
            if self._topic_matches(topic, sub_topic):
                handlers.extend(sub_handlers)
        
        return handlers
    
    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """Check if topic matches a pattern (supports * wildcards)"""
        if pattern == topic:
            return True
        
        if '*' not in pattern:
            return False
        
        # Simple wildcard matching
        pattern_parts = pattern.split('*')
        if len(pattern_parts) == 2:
            prefix, suffix = pattern_parts
            return topic.startswith(prefix) and topic.endswith(suffix)
        
        return False
    
    async def _run_sync_handler(self, handler: Callable, event: Event):
        """Run a synchronous handler in a thread pool"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, handler, event)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        return {
            **self.stats,
            'queue_size': self.event_queue.qsize(),
            'topics': list(self.subscribers.keys()),
            'total_topics': len(self.TOPICS)
        }
    
    def list_topics(self) -> Dict[str, str]:
        """List all available event topics"""
        return self.TOPICS.copy()

# Global event bus instance
_event_bus = None

def get_event_bus() -> EventBus:
    """Get the global event bus instance"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus

# Convenience functions
async def publish(topic: str, data: Dict[str, Any], **kwargs) -> str:
    """Publish an event to the global event bus"""
    bus = get_event_bus()
    return await bus.publish(topic, data, **kwargs)

def subscribe(topic: str, handler: Callable[[Event], Any]) -> str:
    """Subscribe to the global event bus"""
    bus = get_event_bus()
    return bus.subscribe(topic, handler)

async def emit_ui_message(content: str, device_id: str = None, message_type: str = 'response'):
    """Convenience function to emit UI messages"""
    await publish('ui.message.out', {
        'content': content,
        'type': message_type,
        'timestamp': time.time()
    }, device_id=device_id)

async def emit_notification(title: str, message: str, device_id: str = None, priority: str = 'normal'):
    """Convenience function to emit notifications"""
    await publish('ui.notification.show', {
        'title': title,
        'message': message,
        'priority': priority,
        'timestamp': time.time()
    }, device_id=device_id)
