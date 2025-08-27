"""
BUDDY 2.0 Enhanced Intelligence Response Engine
Provides contextual, personalized, and intelligent responses
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class BUDDYEnhancedIntelligence:
    def __init__(self, user_profile_manager=None, memory_engine=None, openai_client=None):
        self.user_profile = user_profile_manager
        self.memory = memory_engine
        self.openai = openai_client
        self.conversation_context = {}
        
        # Initialize memory manager if not provided
        if not self.memory:
            try:
                from memory.cross_device_memory import CrossDeviceMemoryManager
                self.memory = CrossDeviceMemoryManager()
                logger.info("Cross-device memory manager initialized")
            except ImportError:
                logger.warning("Cross-device memory manager not available")
                self.memory = None
        
        # Enhanced knowledge base for intelligent responses
        self.knowledge_base = {
            'identity_responses': {
                'with_profile': "You are {name}, and I've been assisting you across {device_count} devices. We've had {interaction_count} conversations together. {preferences_info}Currently, you're using BUDDY on your {device_type}.",
                'without_profile': "I don't have your profile information yet. Would you like to tell me your name so I can personalize our conversations and remember your preferences across all devices?"
            },
            'system_info': {
                'development': """I'm BUDDY 2.0, an advanced AI assistant built with:

🧠 **Core Intelligence**: Python with FastAPI, natural language processing, and context-aware responses

🌐 **Cross-Platform Architecture**: 
   • Backend: FastAPI with SQLite and in-memory vector storage
   • Frontend: HTML/CSS/JavaScript GUIs optimized for each device
   • Sync: Real-time WebSocket communication across all platforms

💾 **Memory System**: Vector-based semantic memory that learns from our conversations and syncs across all your devices

🔒 **Security**: Local-first privacy with secure cross-device synchronization

The goal is to be your intelligent companion that remembers our conversations, learns your preferences, and provides consistent help across all your devices.""",
                
                'capabilities': """Here's what I can do for you:

🎯 **Intelligent Assistance**:
   • Contextual conversations that remember our history
   • Personalized responses based on your preferences
   • Cross-device memory and synchronization

📱 **Multi-Device Support**:
   • Web, Desktop, Mobile, Watch, Car, and TV interfaces
   • Seamless handoff between devices
   • Device-optimized responses and interactions

🧠 **Smart Features**:
   • Learning from our conversations
   • Intent recognition and context awareness
   • Performance metrics and system monitoring

💬 **Communication**:
   • Natural language understanding
   • Voice interaction support (device-dependent)
   • Real-time messaging with typing indicators

🔧 **Technical Capabilities**:
   • Code assistance and explanations
   • System information and diagnostics
   • Task management and reminders

What specific area would you like to explore or get help with?"""
            },
            'location_info': """I exist in the cloud and on your devices simultaneously! 

🏠 **Your Devices**: I run locally on your {device} for privacy and speed
☁️ **Intelligence**: My core knowledge and your memories are stored securely
🌍 **Global Access**: Available wherever you are, across all your devices
🔄 **Real-time Sync**: Your conversations sync instantly between devices

I'm designed to be location-independent while respecting your privacy and providing consistent assistance wherever you need me."""
        }
        
    async def generate_intelligent_response(self, user_input: str, session_context: dict) -> dict:
        """Generate contextually aware, intelligent responses"""
        
        try:
            # 1. Analyze user input with context
            intent_analysis = await self.analyze_user_intent(user_input, session_context)
            
            # 2. Retrieve relevant user context (simulated for now)
            user_context = await self.gather_user_context(
                session_context.get('user_id'), user_input
            )
            
            # 3. Generate personalized response
            response = await self.generate_contextual_response(
                user_input, intent_analysis, user_context, session_context
            )
            
            # 4. Update memory simulation
            await self.update_user_memory(user_input, response, session_context)
            
            return response
            
        except Exception as e:
            logger.error(f"Error in enhanced intelligence: {e}")
            return await self.generate_fallback_response(user_input, session_context)
    
    async def analyze_user_intent(self, user_input: str, context: dict) -> dict:
        """Analyze what the user is really asking"""
        
        user_input_lower = user_input.lower()
        
        # Identity queries
        if any(phrase in user_input_lower for phrase in ['who am i', 'about me', 'my profile', 'know about me']):
            return {'type': 'identity_query', 'target': 'user_profile'}
            
        # System/development inquiries
        elif any(phrase in user_input_lower for phrase in ['how are you built', 'how were you developed', 'your code', 'how do you work', 'your architecture']):
            return {'type': 'system_inquiry', 'topic': 'development'}
            
        # Capability inquiries
        elif any(phrase in user_input_lower for phrase in ['what can you do', 'your capabilities', 'help me with', 'your features', 'what are you capable of']):
            return {'type': 'capability_inquiry', 'detail_level': 'comprehensive'}
            
        # Location queries
        elif any(phrase in user_input_lower for phrase in ['where are you', 'where do you live', 'your location', 'where from']):
            return {'type': 'location_query', 'context': 'system_origin'}
            
        # Greeting patterns
        elif any(phrase in user_input_lower for phrase in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']):
            return {'type': 'greeting', 'context': 'friendly'}
            
        # Technical questions
        elif any(phrase in user_input_lower for phrase in ['how to', 'explain', 'what is', 'help with', 'tutorial']):
            return {'type': 'technical_help', 'context': 'explanation_needed'}
            
        # General conversation
        else:
            return {'type': 'general_conversation', 'needs_context': True}
    
    async def ai_intent_analysis(self, user_input: str, context: dict) -> dict:
        """Enhanced AI-powered intent analysis with specific mail/device detection"""
        
        try:
            user_input_lower = user_input.lower()
            
            # Priority patterns for specific actions
            if re.search(r'\bsend\s+(a\s+)?mail\b|\bsend\s+(an\s+)?email\b', user_input_lower):
                return {'type': 'send_mail', 'confidence': 0.95, 'method': 'pattern_matching'}
            
            if re.search(r'\b(what are|list|show).*devices?\s+connected\b|\bconnected\s+devices?\b', user_input_lower):
                return {'type': 'list_devices', 'confidence': 0.9, 'method': 'pattern_matching'}
            
            # Enhanced pattern matching for AI simulation
            if any(word in user_input_lower for word in ['task', 'do', 'help', 'assist', 'need']):
                return {'type': 'task_request', 'confidence': 0.8}
            elif any(word in user_input_lower for word in ['know', 'tell', 'explain', 'what', 'how', 'why']):
                return {'type': 'knowledge_query', 'confidence': 0.7}
            elif any(word in user_input_lower for word in ['chat', 'talk', 'conversation']):
                return {'type': 'small_talk', 'confidence': 0.6}
            elif any(word in user_input_lower for word in ['time', 'clock', 'date']):
                return {'type': 'time_inquiry', 'confidence': 0.8}
            elif any(word in user_input_lower for word in ['weather', 'temperature', 'forecast']):
                return {'type': 'weather_inquiry', 'confidence': 0.8}
            elif any(word in user_input_lower for word in ['calculate', 'math', '+', '-', '*', '/']):
                return {'type': 'calculation', 'confidence': 0.8}
            elif any(word in user_input_lower for word in ['sad', 'depressed', 'upset', 'anxious']):
                return {'type': 'emotional_support', 'confidence': 0.7}
            elif any(word in user_input_lower for word in ['joke', 'funny', 'entertain']):
                return {'type': 'entertainment', 'confidence': 0.7}
            else:
                return {'type': 'general_conversation', 'confidence': 0.5}
                
        except Exception as e:
            logger.error(f"AI intent analysis error: {e}")
            return {'type': 'unknown', 'confidence': 0.3}
    
    async def create_conversation_embedding(self, user_input: str, response: str) -> list:
        """Create embeddings for semantic search (simulated for now)"""
        
        try:
            # In real implementation, this would use OpenAI embeddings
            # For now, simulate with a simple hash-based approach
            text = f"User: {user_input}\nBUDDY: {response}"
            
            # Simple embedding simulation (768 dimensions like OpenAI)
            import hashlib
            hash_obj = hashlib.md5(text.encode())
            hash_hex = hash_obj.hexdigest()
            
            # Convert hex to float values between -1 and 1
            embedding = []
            for i in range(0, len(hash_hex), 2):
                hex_pair = hash_hex[i:i+2]
                float_val = (int(hex_pair, 16) - 127.5) / 127.5
                embedding.append(float_val)
            
            # Pad to 768 dimensions
            while len(embedding) < 768:
                embedding.extend(embedding[:min(len(embedding), 768 - len(embedding))])
            
            return embedding[:768]
            
        except Exception as e:
            logger.error(f"Embedding creation error: {e}")
            # Return zero vector as fallback
            return [0.0] * 768
    
    async def handle_send_mail(self, user_input: str, user_context: dict, session_context: dict) -> dict:
        """
        Two-step flow for sending emails:
         - If we already have recipient/subject/body, send immediately
         - Otherwise ask for missing information
        """
        # Check if caller provided email details in session_context
        draft = session_context.get("draft_email", {})
        
        # Parse potential email info from user input
        if not draft.get("to") and "@" in user_input:
            # Extract email from input
            import re
            email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', user_input)
            if email_match:
                draft["to"] = email_match.group()
        
        # Check what fields are missing
        missing = [f for f in ("to", "subject", "body") if not draft.get(f)]
        
        if missing:
            # Ask for the first missing piece
            field = missing[0]
            prompts = {
                "to": "Who should I send the email to? (provide email address or contact name)",
                "subject": "What's the subject line for this email?",
                "body": "What message would you like to send? (or say 'use template' for a default message)"
            }
            
            # Store draft progress
            session_context["draft_email"] = draft
            session_context["expecting_field"] = field
            
            return {
                "response": prompts[field],
                "response_type": "followup_required",
                "requires_followup": True,
                "expected_field": field,
                "draft_email": draft
            }
        
        # All fields present -> attempt to send email
        mailer = session_context.get("mailer")
        user_email = user_context.get("user_profile", {}).get("email", "buddy@example.com")
        
        if not mailer:
            # Fallback - simulate sending
            session_context.pop("draft_email", None)
            return {
                "response": f"✅ Email sent to {draft['to']}!\n\nSubject: {draft['subject']}\nMessage: {draft['body'][:50]}...\n\n(Note: Email service not configured - this is a simulation)",
                "response_type": "action_completed",
                "memory_updated": True,
                "simulated": True
            }
        
        try:
            send_result = await mailer.send_email(
                from_address=user_email,
                to_address=draft["to"],
                subject=draft["subject"],
                body=draft["body"]
            )
            
            # Clear draft after sending
            session_context.pop("draft_email", None)
            session_context.pop("expecting_field", None)
            
            return {
                "response": f"✅ Email sent to {draft['to']} successfully!\n\nSubject: {draft['subject']}\nMessage ID: {send_result.get('id', 'n/a')}",
                "response_type": "action_completed",
                "memory_updated": True
            }
            
        except Exception as e:
            return {
                "response": f"❌ Failed to send email: {str(e)}\n\nWould you like me to save this as a draft instead?",
                "response_type": "error",
                "requires_followup": False
            }
    
    async def handle_list_devices(self, user_context: dict, device_type: str) -> dict:
        """Return a comprehensive list of active devices with last seen times and actions"""
        
        profile = user_context.get("user_profile", {})
        devices = profile.get("devices_used", [])
        
        if not devices:
            return {
                "response": "I don't see any devices registered to your account yet. This might be your first device!\n\nWould you like me to help you connect additional devices?",
                "response_type": "explanatory",
                "devices": [],
                "suggestions": ["Connect mobile app", "Add desktop client", "Setup smartwatch"]
            }
        
        # Normalize device data
        normalized_devices = []
        for i, device in enumerate(devices):
            if isinstance(device, dict):
                normalized_devices.append(device)
            else:
                # String fallback: name only
                normalized_devices.append({
                    "id": f"device_{i}",
                    "name": str(device),
                    "type": "unknown",
                    "last_seen": "unknown"
                })
        
        # Build readable response
        lines = []
        for i, device in enumerate(normalized_devices, start=1):
            name = device.get("name", "Unknown Device")
            device_type_info = device.get("type", "")
            last_seen = device.get("last_seen", "unknown")
            
            # Format device type
            if device_type_info:
                name = f"{name} ({device_type_info})"
            
            lines.append(f"{i}. **{name}** — last active: {last_seen}")
        
        device_list = "\n".join(lines)
        
        response_text = f"🔗 I found {len(normalized_devices)} device(s) connected to your account:\n\n{device_list}\n\nWould you like to:\n• (a) Disconnect a device\n• (b) See activity logs\n• (c) Rename a device\n• (d) Add a new device?"
        
        return {
            "response": response_text,
            "response_type": "device_list",
            "devices": normalized_devices,
            "device_count": len(normalized_devices),
            "current_device": device_type
        }
    
    async def handle_time_inquiry(self, user_context: dict, device_type: str) -> dict:
        """Handle time-related queries"""
        from datetime import datetime
        
        now = datetime.now()
        user_name = user_context.get('name', 'there')
        
        time_str = now.strftime("%I:%M %p")
        date_str = now.strftime("%A, %B %d, %Y")
        
        response = f"⏰ Hi {user_name}! It's currently **{time_str}** on {date_str}."
        
        # Add device-specific context
        if device_type in ['mobile', 'watch']:
            response += "\n\nWould you like me to set a reminder or alarm?"
        
        return {
            "response": response,
            "response_type": "time_info",
            "timestamp": now.isoformat(),
            "timezone": "local"
        }
    
    async def handle_calculation(self, user_input: str, user_context: dict) -> dict:
        """Handle mathematical calculations"""
        import re
        
        user_name = user_context.get('name', 'there')
        
        # Extract mathematical expressions
        math_pattern = r'(\d+(?:\.\d+)?)\s*([\+\-\*\/])\s*(\d+(?:\.\d+)?)'
        match = re.search(math_pattern, user_input)
        
        if match:
            num1, operator, num2 = match.groups()
            try:
                num1, num2 = float(num1), float(num2)
                
                if operator == '+':
                    result = num1 + num2
                elif operator == '-':
                    result = num1 - num2
                elif operator == '*':
                    result = num1 * num2
                elif operator == '/':
                    if num2 == 0:
                        return {
                            "response": "🤔 I can't divide by zero! Try a different number.",
                            "response_type": "calculation_error"
                        }
                    result = num1 / num2
                
                # Format result nicely
                if result == int(result):
                    result = int(result)
                
                response = f"🧮 {user_name}, here's your calculation:\n\n**{num1} {operator} {num2} = {result}**"
                
                return {
                    "response": response,
                    "response_type": "calculation_result",
                    "calculation": {
                        "expression": f"{num1} {operator} {num2}",
                        "result": result
                    }
                }
                
            except Exception as e:
                return {
                    "response": f"❌ Sorry, I had trouble with that calculation: {str(e)}",
                    "response_type": "calculation_error"
                }
        else:
            return {
                "response": f"🤔 I can help with math! Try asking something like 'What's 25 * 4?' or 'Calculate 100 / 5'",
                "response_type": "calculation_help"
            }
    
    async def gather_user_context(self, user_id: Optional[str], user_input: str) -> dict:
        """Gather user context from real memory system or fallback to simulation"""
        
        try:
            # Check if we have a valid user_id before proceeding
            if self.memory and user_id:
                # Use real memory system
                context = await self.memory.sync_user_context_across_devices(user_id, 'current')
                return context.get('user_profile', self.get_simulated_context())
            else:
                # Fallback to simulated context when no user_id or memory system
                return self.get_simulated_context()
                
        except Exception as e:
            logger.error(f"Context gathering error: {e}")
            return self.get_simulated_context()
    
    def get_simulated_context(self) -> dict:
        """Get simulated user context for fallback"""
        return {
            'name': None,  # Will be None initially
            'total_interactions': 1,
            'devices_used': ['desktop', 'web'],
            'preferences': {
                'response_style': 'detailed',
                'technical_level': 'intermediate'
            },
            'recent_topics': ['greetings', 'system_info'],
            'last_interaction': datetime.now(timezone.utc),
            'device_history': {
                'desktop': 5,
                'web': 3,
                'mobile': 0
            }
        }
    
    async def generate_contextual_response(self, user_input: str, intent: dict, 
                                        user_context: dict, session_context: dict) -> dict:
        """Generate personalized, contextual responses with action handlers"""
        
        device_type = session_context.get('device_type', 'desktop')
        user_name = user_context.get('name')
        
        # Handle specific action intents first
        if intent['type'] == 'send_mail':
            return await self.handle_send_mail(user_input, user_context, session_context)
            
        elif intent['type'] == 'list_devices':
            return await self.handle_list_devices(user_context, device_type)
            
        elif intent['type'] == 'identity_query':
            return await self.handle_identity_query(user_context, device_type)
            
        elif intent['type'] == 'system_inquiry':
            return await self.handle_system_inquiry(intent.get('topic', 'general'), device_type)
            
        elif intent['type'] == 'location_query':
            return await self.handle_location_query(user_context, device_type)
            
        elif intent['type'] == 'capability_inquiry':
            return await self.handle_capability_inquiry(user_context, device_type)
            
        elif intent['type'] == 'greeting':
            return await self.handle_greeting(user_context, session_context)
            
        elif intent['type'] == 'technical_help':
            return await self.handle_technical_help(user_input, user_context, device_type)
            
        elif intent['type'] == 'time_inquiry':
            return await self.handle_time_inquiry(user_context, device_type)
            
        elif intent['type'] == 'calculation':
            return await self.handle_calculation(user_input, user_context)
            
        else:
            # Generate contextual conversation response
            return await self.generate_contextual_conversation(user_input, user_context, session_context)
    
    async def handle_identity_query(self, user_context: dict, device_type: str) -> dict:
        """Handle 'who am i' type questions with personalization"""
        
        user_name = user_context.get('name')
        interaction_count = user_context.get('total_interactions', 0)
        devices_used = user_context.get('devices_used', [])
        preferences = user_context.get('preferences', {})
        
        if user_name:
            preferences_info = ""
            if preferences:
                pref_items = []
                if preferences.get('response_style'):
                    pref_items.append(f"prefer {preferences['response_style']} explanations")
                if preferences.get('technical_level'):
                    pref_items.append(f"work at {preferences['technical_level']} technical level")
                
                if pref_items:
                    preferences_info = f"I know you {' and '.join(pref_items)}. "
            
            response = self.knowledge_base['identity_responses']['with_profile'].format(
                name=user_name,
                device_count=len(devices_used),
                interaction_count=interaction_count,
                preferences_info=preferences_info,
                device_type=device_type
            )
        else:
            response = self.knowledge_base['identity_responses']['without_profile']
        
        return {
            'response': response,
            'response_type': 'personalized_identity',
            'requires_followup': not user_name,
            'memory_updated': True,
            'intent': 'identity_query'
        }
    
    async def handle_system_inquiry(self, topic: str, device_type: str) -> dict:
        """Handle questions about BUDDY's development and architecture"""
        
        if topic == 'development':
            response = self.knowledge_base['system_info']['development']
        else:
            response = self.knowledge_base['system_info']['development']
        
        return {
            'response': response,
            'response_type': 'technical_explanation',
            'includes_formatting': True,
            'intent': 'system_inquiry'
        }
    
    async def handle_location_query(self, user_context: dict, device_type: str) -> dict:
        """Handle location-related questions"""
        
        response = self.knowledge_base['location_info'].format(device=device_type)
        
        return {
            'response': response,
            'response_type': 'explanatory',
            'includes_formatting': True,
            'intent': 'location_query'
        }
    
    async def handle_capability_inquiry(self, user_context: dict, device_type: str) -> dict:
        """Handle capability and feature questions"""
        
        response = self.knowledge_base['system_info']['capabilities']
        
        return {
            'response': response,
            'response_type': 'capability_overview',
            'includes_formatting': True,
            'intent': 'capability_inquiry'
        }
    
    async def handle_greeting(self, user_context: dict, session_context: dict) -> dict:
        """Handle greetings with personalization"""
        
        user_name = user_context.get('name')
        device_type = session_context.get('device_type', 'desktop')
        interaction_count = user_context.get('total_interactions', 0)
        
        if user_name:
            if interaction_count > 5:
                response = f"Hello again, {user_name}! Great to see you back on your {device_type}. How can I assist you today?"
            else:
                response = f"Hi {user_name}! Nice to see you on your {device_type}. What can I help you with?"
        else:
            response = f"Hello! I'm BUDDY 2.0, your intelligent AI assistant. I'm running on your {device_type} and ready to help. What would you like to know or do today?"
        
        return {
            'response': response,
            'response_type': 'personalized_greeting',
            'intent': 'greeting'
        }
    
    async def handle_technical_help(self, user_input: str, user_context: dict, device_type: str) -> dict:
        """Handle technical help requests"""
        
        response = f"I'd be happy to help you with that! Based on your question '{user_input}', I can provide detailed technical assistance. Could you tell me more specifically what you'd like to learn about or what problem you're trying to solve?"
        
        return {
            'response': response,
            'response_type': 'technical_help',
            'requires_followup': True,
            'intent': 'technical_help'
        }
    
    async def generate_contextual_conversation(self, user_input: str, user_context: dict, session_context: dict) -> dict:
        """Generate intelligent contextual responses for general conversation"""
        
        device_type = session_context.get('device_type', 'desktop')
        user_name = user_context.get('name')
        
        # Analyze the input for better responses
        if 'thank' in user_input.lower():
            name_part = f" {user_name}" if user_name else ""
            response = f"You're very welcome{name_part}! I'm here whenever you need assistance on your {device_type} or any other device. Is there anything else I can help you with?"
            
        elif any(word in user_input.lower() for word in ['test', 'testing', 'check']):
            response = f"Great! I'm working perfectly and ready to assist you. All systems are operational across all platforms. What would you like to test or explore?"
            
        elif 'good' in user_input.lower() and any(word in user_input.lower() for word in ['job', 'work', 'response']):
            response = "Thank you for the positive feedback! I'm constantly learning and improving to provide better assistance. Is there anything specific you'd like help with?"
            
        else:
            # Intelligent contextual response
            response = f"I understand you're mentioning '{user_input}'. I'm here to provide intelligent assistance tailored to your needs. Could you tell me more about what you'd like to explore or accomplish? I can help with explanations, technical questions, or general assistance across all your devices."
        
        return {
            'response': response,
            'response_type': 'contextual_conversation',
            'intent': 'general_conversation'
        }
    
    async def generate_fallback_response(self, user_input: str, session_context: dict) -> dict:
        """Generate fallback response when there are errors"""
        
        device_type = session_context.get('device_type', 'desktop')
        
        response = f"I understand you're asking about '{user_input}'. Let me help you with that in the best way I can. Could you provide a bit more context so I can give you the most relevant and helpful information for your {device_type}?"
        
        return {
            'response': response,
            'response_type': 'fallback',
            'requires_followup': True,
            'intent': 'fallback'
        }
    
    async def update_user_memory(self, user_input: str, response: dict, session_context: dict):
        """Update user memory and learning with real memory system"""
        
        try:
            if self.memory:
                # Use real memory system
                await self.memory.update_conversation_memory(user_input, response, session_context)
            else:
                # Fallback simulation
                memory_entry = {
                    'user_id': session_context.get('user_id'),
                    'user_input': user_input,
                    'response': response['response'],
                    'intent': response.get('intent'),
                    'device_type': session_context.get('device_type'),
                    'timestamp': datetime.now(timezone.utc),
                    'response_type': response.get('response_type')
                }
                
                logger.info(f"Memory simulated: {memory_entry['intent']} interaction on {memory_entry['device_type']}")
            
        except Exception as e:
            logger.error(f"Memory update error: {e}")
