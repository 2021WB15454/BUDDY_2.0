"""
BUDDY Flow Persistence Manager

Handles conversation flow persistence, recovery, and seamless handoffs between devices.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import asyncio
import uuid

logger = logging.getLogger(__name__)


class FlowPersistenceManager:
    """Manages conversation flow persistence and recovery"""
    
    def __init__(self):
        # In-memory storage for demonstration - would use Redis/Database in production
        self.flow_snapshots = {}
        self.conversation_memory = {}
        self.user_sessions = {}
        
    async def create_flow_snapshot(self, session_id: str, context: Dict[str, Any], 
                                 reason: str = "periodic_backup") -> str:
        """Create a snapshot of current conversation flow"""
        snapshot_id = f"flow_snapshot_{session_id}_{int(datetime.now().timestamp())}"
        
        snapshot_data = {
            'snapshot_id': snapshot_id,
            'session_id': session_id,
            'user_id': context.get('user_id', 'unknown'),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'conversation_state': context.get('conversation_state', 'active'),
            'current_topic': context.get('current_topic'),
            'conversation_history': context.get('conversation_history', [])[-20:],  # Last 20 messages
            'user_intent': context.get('user_intent'),
            'entity_memory': context.get('entity_memory', {}),
            'emotional_state': context.get('emotional_state'),
            'unresolved_questions': context.get('unresolved_questions', []),
            'pending_actions': context.get('pending_actions', []),
            'device_context': context.get('device_context', {}),
            'conversation_depth': context.get('conversation_depth', 0),
            'flow_metadata': {
                'snapshot_reason': reason,
                'flow_quality_score': await self.calculate_flow_quality(context),
                'interruption_count': context.get('interruption_count', 0),
                'handoff_count': context.get('handoff_count', 0)
            }
        }
        
        # Store snapshot
        self.flow_snapshots[snapshot_id] = snapshot_data
        
        # Also store as latest for session
        self.conversation_memory[session_id] = snapshot_data
        
        logger.info(f"Created flow snapshot {snapshot_id} for session {session_id}")
        return snapshot_id
    
    async def restore_flow_from_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Restore conversation flow from snapshot"""
        snapshot_data = self.flow_snapshots.get(snapshot_id)
        
        if snapshot_data:
            logger.info(f"Restored flow from snapshot {snapshot_id}")
            return snapshot_data
        
        logger.warning(f"Snapshot {snapshot_id} not found")
        return None
    
    async def get_latest_conversation_snapshot(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent conversation snapshot for a session"""
        return self.conversation_memory.get(session_id)
    
    async def handle_flow_interruption(self, session_id: str, interruption_reason: str, 
                                     context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle conversation flow interruptions gracefully"""
        
        # Create emergency snapshot
        snapshot_id = await self.create_flow_snapshot(session_id, context, f"interruption_{interruption_reason}")
        
        # Determine recovery strategy
        recovery_strategy = await self.determine_recovery_strategy(context, interruption_reason)
        
        # Prepare recovery instructions
        recovery_instructions = {
            'snapshot_id': snapshot_id,
            'recovery_strategy': recovery_strategy,
            'interruption_reason': interruption_reason,
            'recovery_prompt': await self.generate_recovery_prompt(context, interruption_reason),
            'context_preservation_level': recovery_strategy.get('context_level', 'medium'),
            'recommended_action': recovery_strategy.get('action', 'continue')
        }
        
        logger.info(f"Handled flow interruption for session {session_id}: {interruption_reason}")
        return recovery_instructions
    
    async def seamless_flow_recovery(self, session_id: str, device_context: Dict[str, Any]) -> Dict[str, Any]:
        """Recover conversation flow seamlessly after interruption"""
        
        # Get the most recent snapshot
        recent_snapshot = await self.get_latest_conversation_snapshot(session_id)
        
        if recent_snapshot:
            # Calculate time since last interaction
            last_timestamp = datetime.fromisoformat(recent_snapshot['timestamp'].replace('Z', '+00:00'))
            time_gap = datetime.now(timezone.utc) - last_timestamp
            
            # Prepare recovery context
            recovery_context = {
                'session_id': session_id,
                'snapshot_found': True,
                'time_gap_minutes': int(time_gap.total_seconds() / 60),
                'previous_context': recent_snapshot,
                'continuation_message': await self.generate_continuation_message(recent_snapshot, device_context),
                'context_summary': await self.generate_context_summary(recent_snapshot),
                'recovery_confidence': await self.calculate_recovery_confidence(recent_snapshot, device_context, time_gap)
            }
            
            logger.info(f"Seamless recovery for session {session_id} after {recovery_context['time_gap_minutes']} minutes")
            return recovery_context
        
        # No previous context found
        return {
            'session_id': session_id,
            'snapshot_found': False,
            'continuation_message': "Hello! How can I help you today?",
            'context_summary': None,
            'recovery_confidence': 0.0
        }
    
    async def handle_device_handoff(self, session_id: str, from_device: str, 
                                  to_device: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle smooth device handoff"""
        
        # Create handoff snapshot
        snapshot_id = await self.create_flow_snapshot(session_id, context, f"device_handoff_{from_device}_to_{to_device}")
        
        # Prepare handoff data
        handoff_data = {
            'session_id': session_id,
            'handoff_id': f"handoff_{uuid.uuid4().hex[:8]}",
            'from_device': from_device,
            'to_device': to_device,
            'snapshot_id': snapshot_id,
            'handoff_timestamp': datetime.now(timezone.utc).isoformat(),
            'context_summary': await self.generate_context_summary(context),
            'handoff_message': await self.generate_handoff_message(from_device, to_device, context),
            'optimization_needed': await self.requires_device_optimization(from_device, to_device),
            'continuation_prompt': await self.generate_device_continuation_prompt(to_device, context)
        }
        
        # Update handoff count
        context['handoff_count'] = context.get('handoff_count', 0) + 1
        
        logger.info(f"Device handoff from {from_device} to {to_device} for session {session_id}")
        return handoff_data
    
    async def track_conversation_patterns(self, user_id: str, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track user conversation patterns for better flow management"""
        
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = []
        
        # Add current session data
        self.user_sessions[user_id].append({
            'session_id': session_data.get('session_id'),
            'start_time': session_data.get('start_time'),
            'end_time': datetime.now(timezone.utc).isoformat(),
            'message_count': len(session_data.get('conversation_history', [])),
            'topics_discussed': session_data.get('topics_discussed', []),
            'devices_used': session_data.get('devices_used', []),
            'primary_intent': session_data.get('primary_intent'),
            'satisfaction_score': session_data.get('satisfaction_score', 0.5)
        })
        
        # Keep only recent sessions (last 50)
        self.user_sessions[user_id] = self.user_sessions[user_id][-50:]
        
        # Analyze patterns
        patterns = await self.analyze_user_patterns(user_id)
        
        return patterns
    
    async def calculate_flow_quality(self, context: Dict[str, Any]) -> float:
        """Calculate conversation flow quality score"""
        score = 0.5  # Base score
        
        # Check conversation continuity
        history = context.get('conversation_history', [])
        if len(history) > 2:
            score += 0.1
        
        # Check for successful intent recognition
        if context.get('user_intent') and context['user_intent'] != 'unknown':
            score += 0.2
        
        # Check for emotional intelligence
        if context.get('emotional_state'):
            score += 0.1
        
        # Check for topic continuity
        if context.get('current_topic'):
            score += 0.1
        
        # Penalty for unresolved questions
        unresolved_count = len(context.get('unresolved_questions', []))
        score -= min(unresolved_count * 0.05, 0.2)
        
        return min(max(score, 0.0), 1.0)
    
    async def determine_recovery_strategy(self, context: Dict[str, Any], interruption_reason: str) -> Dict[str, Any]:
        """Determine the best recovery strategy based on context and interruption"""
        
        strategies = {
            'device_switch': {
                'context_level': 'high',
                'action': 'continue_with_handoff_message',
                'priority': 'maintain_continuity'
            },
            'timeout': {
                'context_level': 'medium',
                'action': 'gentle_reentry',
                'priority': 'user_comfort'
            },
            'error': {
                'context_level': 'medium',
                'action': 'apologize_and_continue',
                'priority': 'error_recovery'
            },
            'user_initiated': {
                'context_level': 'low',
                'action': 'fresh_start',
                'priority': 'user_intent'
            }
        }
        
        return strategies.get(interruption_reason, strategies['timeout'])
    
    async def generate_recovery_prompt(self, context: Dict[str, Any], interruption_reason: str) -> str:
        """Generate appropriate recovery prompt"""
        
        prompts = {
            'device_switch': "I see you've switched devices. Let me continue where we left off.",
            'timeout': "Welcome back! We were discussing {topic}. Would you like to continue?",
            'error': "I apologize for the interruption. Let me help you with what you were asking about.",
            'user_initiated': "Hello again! How can I help you today?"
        }
        
        prompt = prompts.get(interruption_reason, prompts['timeout'])
        
        # Substitute context variables
        if '{topic}' in prompt and context.get('current_topic'):
            prompt = prompt.replace('{topic}', context['current_topic'])
        
        return prompt
    
    async def generate_continuation_message(self, snapshot: Dict[str, Any], device_context: Dict[str, Any]) -> str:
        """Generate continuation message for seamless recovery"""
        
        current_topic = snapshot.get('current_topic')
        time_gap = datetime.now(timezone.utc) - datetime.fromisoformat(snapshot['timestamp'].replace('Z', '+00:00'))
        minutes_gap = int(time_gap.total_seconds() / 60)
        
        if minutes_gap < 5:
            if current_topic:
                return f"Continuing our conversation about {current_topic}."
            else:
                return "I'm here to continue helping you."
        elif minutes_gap < 60:
            if current_topic:
                return f"Welcome back! We were discussing {current_topic}. How can I continue helping?"
            else:
                return "Welcome back! How can I help you today?"
        else:
            return "Hello! How can I assist you today?"
    
    async def generate_context_summary(self, context: Dict[str, Any]) -> str:
        """Generate a brief summary of conversation context"""
        
        topic = context.get('current_topic', 'various topics')
        intent = context.get('user_intent', 'assistance')
        message_count = len(context.get('conversation_history', []))
        
        if message_count == 0:
            return "New conversation"
        elif message_count == 1:
            return f"Brief exchange about {topic}"
        else:
            return f"Ongoing conversation about {topic} ({message_count} exchanges)"
    
    async def generate_handoff_message(self, from_device: str, to_device: str, context: Dict[str, Any]) -> str:
        """Generate device handoff message"""
        
        device_transitions = {
            'mobile_to_desktop': "I see you've moved to your computer. I can provide more detailed responses here.",
            'desktop_to_mobile': "Continuing on your mobile device. I'll keep my responses more concise.",
            'mobile_to_watch': "Now on your watch. I'll be brief and voice-focused.",
            'watch_to_mobile': "Back to your phone - I can provide more detailed assistance now.",
            'any_to_car': "Now in your vehicle. I'll focus on voice responses and keep things simple for safety.",
            'car_to_mobile': "Out of the car and back on your phone. How can I continue helping?"
        }
        
        transition_key = f"{from_device}_to_{to_device}"
        message = device_transitions.get(transition_key, device_transitions.get(f"any_to_{to_device}"))
        
        if not message:
            message = f"Continuing our conversation on your {to_device}."
        
        # Add context if available
        if context.get('current_topic'):
            message += f" We were discussing {context['current_topic']}."
        
        return message
    
    async def requires_device_optimization(self, from_device: str, to_device: str) -> bool:
        """Check if device optimization is needed for handoff"""
        
        # Optimization needed when switching between very different device types
        optimization_pairs = [
            ('desktop', 'watch'),
            ('mobile', 'watch'),
            ('watch', 'desktop'),
            ('watch', 'tv'),
            ('car', 'desktop'),
            ('desktop', 'car')
        ]
        
        return (from_device, to_device) in optimization_pairs or (to_device, from_device) in optimization_pairs
    
    async def generate_device_continuation_prompt(self, device: str, context: Dict[str, Any]) -> str:
        """Generate device-specific continuation prompt"""
        
        device_prompts = {
            'watch': "Quick update or question?",
            'car': "What can I help with while you drive?",
            'tv': "What would you like to explore on the big screen?",
            'desktop': "How can I provide detailed assistance?",
            'mobile': "How can I help you today?"
        }
        
        return device_prompts.get(device, device_prompts['mobile'])
    
    async def analyze_user_patterns(self, user_id: str) -> Dict[str, Any]:
        """Analyze user conversation patterns"""
        
        sessions = self.user_sessions.get(user_id, [])
        
        if not sessions:
            return {
                'total_sessions': 0,
                'average_length': 0,
                'preferred_topics': [],
                'preferred_devices': [],
                'interaction_style': 'unknown'
            }
        
        # Calculate basic statistics
        total_sessions = len(sessions)
        avg_message_count = sum(s.get('message_count', 0) for s in sessions) / total_sessions
        
        # Find preferred topics
        all_topics = []
        for session in sessions:
            all_topics.extend(session.get('topics_discussed', []))
        
        topic_counts = {}
        for topic in all_topics:
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        preferred_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Find preferred devices
        all_devices = []
        for session in sessions:
            all_devices.extend(session.get('devices_used', []))
        
        device_counts = {}
        for device in all_devices:
            device_counts[device] = device_counts.get(device, 0) + 1
        
        preferred_devices = sorted(device_counts.items(), key=lambda x: x[1], reverse=True)[:2]
        
        return {
            'total_sessions': total_sessions,
            'average_message_count': avg_message_count,
            'preferred_topics': [topic for topic, count in preferred_topics],
            'preferred_devices': [device for device, count in preferred_devices],
            'interaction_style': 'conversational' if avg_message_count > 5 else 'brief',
            'average_satisfaction': sum(s.get('satisfaction_score', 0.5) for s in sessions) / total_sessions
        }
    
    async def calculate_recovery_confidence(self, snapshot: Dict[str, Any], 
                                         device_context: Dict[str, Any], time_gap: timedelta) -> float:
        """Calculate confidence in conversation recovery"""
        
        confidence = 0.5  # Base confidence
        
        # Time factor (more recent = higher confidence)
        if time_gap.total_seconds() < 300:  # < 5 minutes
            confidence += 0.3
        elif time_gap.total_seconds() < 3600:  # < 1 hour
            confidence += 0.2
        elif time_gap.total_seconds() < 86400:  # < 1 day
            confidence += 0.1
        
        # Context richness factor
        if snapshot.get('current_topic'):
            confidence += 0.1
        if snapshot.get('user_intent') and snapshot['user_intent'] != 'unknown':
            confidence += 0.1
        if len(snapshot.get('conversation_history', [])) > 3:
            confidence += 0.1
        
        # Device consistency factor
        if (snapshot.get('device_context', {}).get('device_type') == 
            device_context.get('device_type')):
            confidence += 0.1
        
        return min(max(confidence, 0.0), 1.0)
