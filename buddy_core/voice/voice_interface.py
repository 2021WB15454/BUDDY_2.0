"""
BUDDY 2.0 Voice Interface - High-Level Voice Interaction API
==========================================================

This module provides a simple, high-level interface for voice interactions
that integrates seamlessly with the Phase 1 Advanced AI capabilities.

Features:
- One-line voice command processing
- Continuous conversation mode
- Voice-activated assistant mode
- Custom voice responses
- Multi-language support
- Voice personality customization
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from dataclasses import dataclass

from .voice_engine import (
    VoiceEngine, VoiceConfig, VoiceInteractionEvent, 
    get_voice_engine, speak, listen_and_respond
)

logger = logging.getLogger(__name__)

@dataclass
class VoicePersonality:
    """Voice personality configuration"""
    name: str = "BUDDY"
    voice_style: str = "friendly"
    speaking_pace: str = "normal"  # slow, normal, fast
    formality: str = "casual"     # formal, casual, friendly
    enthusiasm: str = "moderate"  # low, moderate, high
    
    # Response patterns
    greeting_phrases: List[str] = None
    acknowledgment_phrases: List[str] = None
    thinking_phrases: List[str] = None
    
    def __post_init__(self):
        if self.greeting_phrases is None:
            self.greeting_phrases = [
                "Hello! I'm BUDDY, your AI assistant.",
                "Hi there! How can I help you today?",
                "Hey! I'm here and ready to assist you."
            ]
        
        if self.acknowledgment_phrases is None:
            self.acknowledgment_phrases = [
                "Got it!",
                "I understand.",
                "Absolutely!",
                "Sure thing!",
                "Of course!"
            ]
        
        if self.thinking_phrases is None:
            self.thinking_phrases = [
                "Let me think about that...",
                "Processing that for you...",
                "One moment while I work on that...",
                "I'm analyzing that request..."
            ]

class VoiceConversationManager:
    """Manages ongoing voice conversations with context"""
    
    def __init__(self, personality: VoicePersonality = None):
        self.personality = personality or VoicePersonality()
        self.voice_engine = None
        self.conversation_active = False
        self.session_context = {}
        self.user_preferences = {}
        
    async def initialize(self, config: VoiceConfig = None) -> bool:
        """Initialize the voice conversation system"""
        try:
            self.voice_engine = await get_voice_engine(config)
            
            # Set up event handlers
            self.voice_engine.events.on_speech_recognized = self._on_speech_recognized
            self.voice_engine.events.on_response_generated = self._on_response_generated
            self.voice_engine.events.on_error = self._on_error
            
            logger.info("Voice conversation manager initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize voice conversation manager: {e}")
            return False
    
    async def start_conversation(self, greeting: str = None) -> bool:
        """Start a voice conversation session"""
        if not self.voice_engine:
            await self.initialize()
        
        try:
            # Start voice interaction system
            success = await self.voice_engine.start_voice_interaction()
            if not success:
                return False
            
            self.conversation_active = True
            self.session_context = {
                'start_time': datetime.now(),
                'interaction_count': 0,
                'topics_discussed': []
            }
            
            # Speak greeting
            greeting_text = greeting or self._get_random_phrase(self.personality.greeting_phrases)
            await self.voice_engine._speak_response(greeting_text)
            
            logger.info("Voice conversation started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start conversation: {e}")
            return False
    
    async def end_conversation(self, farewell: str = None) -> bool:
        """End the voice conversation session"""
        if not self.conversation_active:
            return True
        
        try:
            # Speak farewell
            farewell_text = farewell or "Goodbye! Feel free to talk to me anytime."
            await self.voice_engine._speak_response(farewell_text)
            
            # Stop voice interaction
            await self.voice_engine.stop_voice_interaction()
            
            self.conversation_active = False
            
            # Log session summary
            if self.session_context:
                duration = (datetime.now() - self.session_context['start_time']).total_seconds()
                logger.info(
                    f"Conversation ended. Duration: {duration:.1f}s, "
                    f"Interactions: {self.session_context['interaction_count']}"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to end conversation: {e}")
            return False
    
    async def process_single_command(self, audio_data: bytes = None) -> Dict[str, Any]:
        """Process a single voice command"""
        if not self.voice_engine:
            await self.initialize()
        
        if not self.voice_engine.is_active:
            await self.voice_engine.start_voice_interaction()
        
        # Process the voice command
        result = await self.voice_engine.process_voice_command(audio_data)
        
        # Update session context
        if self.conversation_active:
            self.session_context['interaction_count'] += 1
            
            # Extract topics from recognized text
            if 'stt_result' in result and result['stt_result']['text']:
                self._update_topics(result['stt_result']['text'])
        
        return result
    
    async def continuous_conversation_mode(self, duration_minutes: float = 30.0) -> List[Dict[str, Any]]:
        """Run continuous conversation mode for specified duration"""
        if not await self.start_conversation():
            return []
        
        interactions = []
        start_time = datetime.now()
        max_duration = duration_minutes * 60  # Convert to seconds
        
        try:
            logger.info(f"Starting continuous conversation mode for {duration_minutes} minutes")
            
            while self.conversation_active:
                # Check duration limit
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > max_duration:
                    logger.info("Conversation duration limit reached")
                    break
                
                try:
                    # Wait for voice input (simulated for now)
                    await asyncio.sleep(1.0)
                    
                    # In a real implementation, this would detect actual voice input
                    # For now, we'll simulate some interactions
                    if len(interactions) < 3:  # Simulate a few interactions
                        result = await self.process_single_command()
                        interactions.append(result)
                    else:
                        break
                        
                except KeyboardInterrupt:
                    logger.info("Conversation interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Error in continuous conversation: {e}")
                    break
            
        finally:
            await self.end_conversation()
        
        return interactions
    
    async def wake_word_mode(self, wake_words: List[str] = None) -> bool:
        """Enable wake word activation mode"""
        if not self.voice_engine:
            await self.initialize()
        
        # Configure wake words
        if wake_words:
            self.voice_engine.config.wake_words = wake_words
        
        # Start wake word detection
        success = self.voice_engine.wake_word_detector.start_listening()
        
        if success:
            logger.info(f"Wake word mode active. Listening for: {self.voice_engine.config.wake_words}")
        
        return success
    
    def _get_random_phrase(self, phrases: List[str]) -> str:
        """Get a random phrase from a list"""
        import random
        return random.choice(phrases)
    
    def _update_topics(self, text: str):
        """Update conversation topics based on recognized text"""
        # Simple topic extraction (could be enhanced with NLP)
        topics = []
        
        topic_keywords = {
            'weather': ['weather', 'temperature', 'rain', 'sunny', 'forecast'],
            'schedule': ['meeting', 'appointment', 'schedule', 'calendar', 'time'],
            'email': ['email', 'message', 'send', 'reply', 'mail'],
            'music': ['music', 'song', 'play', 'album', 'artist'],
            'news': ['news', 'headlines', 'current', 'events', 'today'],
            'smart_home': ['lights', 'temperature', 'thermostat', 'security', 'home']
        }
        
        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
        
        # Add new topics to session context
        for topic in topics:
            if topic not in self.session_context['topics_discussed']:
                self.session_context['topics_discussed'].append(topic)
    
    async def _on_speech_recognized(self, text: str, confidence: float):
        """Handle speech recognition events"""
        logger.info(f"Speech recognized: '{text}' (confidence: {confidence:.2f})")
        
        # Could add user preference learning here
        if confidence > 0.9:
            # High confidence speech - could learn user speech patterns
            pass
    
    async def _on_response_generated(self, response: str):
        """Handle response generation events"""
        logger.info(f"Response generated: '{response[:50]}...'")
    
    async def _on_error(self, error: str):
        """Handle voice interaction errors"""
        logger.error(f"Voice interaction error: {error}")
        
        # Speak error message to user
        if self.voice_engine and self.conversation_active:
            error_response = "I'm having some technical difficulties. Please try again."
            await self.voice_engine._speak_response(error_response)

class VoiceAssistant:
    """High-level voice assistant interface"""
    
    def __init__(self, personality: VoicePersonality = None, config: VoiceConfig = None):
        self.personality = personality or VoicePersonality()
        self.config = config or VoiceConfig()
        self.conversation_manager = VoiceConversationManager(self.personality)
        self.is_initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the voice assistant"""
        if self.is_initialized:
            return True
        
        success = await self.conversation_manager.initialize(self.config)
        self.is_initialized = success
        
        if success:
            logger.info("Voice Assistant initialized successfully")
        else:
            logger.error("Voice Assistant initialization failed")
        
        return success
    
    async def say(self, text: str, emotion: str = "neutral") -> bool:
        """Make the assistant speak text"""
        try:
            return await speak(text, emotion)
        except Exception as e:
            logger.error(f"Say failed: {e}")
            return False
    
    async def listen(self) -> str:
        """Listen for voice input and return transcribed text"""
        try:
            if not self.is_initialized:
                await self.initialize()
            
            result = await self.conversation_manager.process_single_command()
            return result.get('stt_result', {}).get('text', '')
        except Exception as e:
            logger.error(f"Listen failed: {e}")
            return ""
    
    async def chat(self, audio_data: bytes = None) -> str:
        """Complete voice interaction: listen, process, and respond"""
        try:
            result = await listen_and_respond()
            return result
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return f"Sorry, I encountered an error: {e}"
    
    async def start_conversation_mode(self, duration_minutes: float = 30.0) -> List[Dict[str, Any]]:
        """Start continuous conversation mode"""
        if not self.is_initialized:
            await self.initialize()
        
        return await self.conversation_manager.continuous_conversation_mode(duration_minutes)
    
    async def enable_wake_word(self, wake_words: List[str] = None) -> bool:
        """Enable wake word activation"""
        if not self.is_initialized:
            await self.initialize()
        
        return await self.conversation_manager.wake_word_mode(wake_words)
    
    async def test_voice_system(self) -> Dict[str, Any]:
        """Test the voice system capabilities"""
        if not self.is_initialized:
            await self.initialize()
        
        test_results = await self.conversation_manager.voice_engine.test_voice_capabilities()
        
        # Add assistant-level tests
        test_results['assistant_tests'] = {}
        
        # Test say function
        try:
            say_success = await self.say("Testing voice assistant speech capabilities")
            test_results['assistant_tests']['say'] = {
                'status': 'working' if say_success else 'failed'
            }
        except Exception as e:
            test_results['assistant_tests']['say'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        # Test listen function (simulated)
        try:
            transcribed = await self.listen()
            test_results['assistant_tests']['listen'] = {
                'status': 'working' if transcribed else 'failed',
                'result': transcribed
            }
        except Exception as e:
            test_results['assistant_tests']['listen'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        # Test complete chat interaction
        try:
            chat_response = await self.chat()
            test_results['assistant_tests']['chat'] = {
                'status': 'working' if chat_response else 'failed',
                'response': chat_response[:100] + "..." if len(chat_response) > 100 else chat_response
            }
        except Exception as e:
            test_results['assistant_tests']['chat'] = {
                'status': 'failed',
                'error': str(e)
            }
        
        return test_results

# Convenience functions for easy voice interaction

async def quick_voice_test() -> Dict[str, Any]:
    """Quick test of voice capabilities"""
    assistant = VoiceAssistant()
    return await assistant.test_voice_system()

async def voice_chat(message: str = None) -> str:
    """Quick voice chat function"""
    assistant = VoiceAssistant()
    await assistant.initialize()
    
    if message:
        # If message provided, speak it first then listen for response
        await assistant.say(message)
    
    return await assistant.chat()

async def start_voice_assistant(wake_words: List[str] = None, personality_name: str = "BUDDY") -> VoiceAssistant:
    """Start a voice assistant with optional customization"""
    personality = VoicePersonality(name=personality_name)
    assistant = VoiceAssistant(personality)
    
    await assistant.initialize()
    
    if wake_words:
        await assistant.enable_wake_word(wake_words)
    
    return assistant

# Voice command shortcuts for common tasks

async def voice_schedule_meeting(duration_text: str = "Schedule a meeting") -> str:
    """Voice shortcut for scheduling meetings"""
    assistant = VoiceAssistant()
    await assistant.say(duration_text)
    return await assistant.chat()

async def voice_weather_check(location: str = None) -> str:
    """Voice shortcut for weather checking"""
    assistant = VoiceAssistant()
    
    if location:
        prompt = f"What's the weather like in {location}?"
    else:
        prompt = "What's the weather like today?"
    
    await assistant.say(prompt)
    return await assistant.chat()

async def voice_email_send(recipient: str = None) -> str:
    """Voice shortcut for sending emails"""
    assistant = VoiceAssistant()
    
    if recipient:
        prompt = f"Send an email to {recipient}"
    else:
        prompt = "Help me send an email"
    
    await assistant.say(prompt)
    return await assistant.chat()

# Demo and testing functions

async def voice_demo() -> None:
    """Run a voice interaction demo"""
    print("🎤 BUDDY 2.0 Voice Assistant Demo")
    print("=" * 40)
    
    assistant = VoiceAssistant()
    
    # Initialize
    print("Initializing voice assistant...")
    if not await assistant.initialize():
        print("❌ Failed to initialize voice assistant")
        return
    
    print("✅ Voice assistant ready!")
    
    # Demo interactions
    demo_scenarios = [
        "Hello BUDDY! How are you today?",
        "What can you help me with?",
        "Schedule a meeting with the team tomorrow",
        "What's the weather forecast?",
        "Play some relaxing music",
        "Thank you for your help!"
    ]
    
    for i, scenario in enumerate(demo_scenarios, 1):
        print(f"\n🎬 Demo {i}: User says '{scenario}'")
        response = await voice_chat(scenario)
        print(f"🤖 BUDDY responds: {response}")
        
        # Small delay between interactions
        await asyncio.sleep(1.0)
    
    print("\n🎉 Voice demo complete!")

if __name__ == "__main__":
    # Run demo if script is executed directly
    asyncio.run(voice_demo())
