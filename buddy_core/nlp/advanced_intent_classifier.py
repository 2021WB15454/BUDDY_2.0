"""
BUDDY 2.0 Advanced Intent Classifier
ML-powered intent classification replacing regex-based detection

This implementation provides sophisticated intent understanding using:
- BART zero-shot classification
- Sentence transformers for semantic similarity
- Context-aware refinement
- Entity extraction per intent type
"""

import os
import json
import asyncio
import logging
import re
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

# ML and NLP imports
try:
    import torch
    from transformers import (
        AutoTokenizer, AutoModelForSequenceClassification, 
        pipeline, BartForSequenceClassification
    )
    from sentence_transformers import SentenceTransformer
    import spacy
    ML_DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"ML dependencies not fully available: {e}")
    ML_DEPENDENCIES_AVAILABLE = False

# Date/time parsing
try:
    import dateparser
    from dateutil import parser as date_parser
    DATE_PARSING_AVAILABLE = True
except ImportError:
    DATE_PARSING_AVAILABLE = False

logger = logging.getLogger(__name__)

class AdvancedIntentClassifier:
    """
    Advanced ML-powered intent classification with context awareness
    and sophisticated entity extraction capabilities.
    """
    
    def __init__(self):
        self.initialized = False
        self.tokenizer = None
        self.classification_model = None
        self.sentence_model = None
        self.nlp_model = None
        
        # Comprehensive intent categories for JARVIS-level functionality
        self.intent_categories = [
            # Communication & Social
            'email_send', 'email_check', 'email_reply', 'call_make', 'call_answer',
            'message_send', 'contact_find', 'social_post', 'social_check',
            
            # Calendar & Time Management
            'calendar_schedule', 'calendar_check', 'calendar_modify', 'calendar_cancel',
            'reminder_create', 'reminder_list', 'reminder_modify', 'reminder_delete',
            'timer_set', 'alarm_set', 'timezone_convert',
            
            # Information & Knowledge
            'weather_query', 'weather_forecast', 'news_update', 'news_search',
            'general_qa', 'definition_lookup', 'calculation', 'unit_conversion',
            'web_search', 'fact_check', 'translation',
            
            # Entertainment & Media
            'music_play', 'music_pause', 'music_skip', 'music_search',
            'video_play', 'podcast_play', 'radio_tune', 'volume_control',
            'media_recommend',
            
            # Smart Home & IoT
            'lights_control', 'temperature_control', 'security_check', 'device_control',
            'appliance_control', 'door_lock', 'window_control', 'scene_activate',
            
            # Navigation & Travel
            'navigation_start', 'traffic_check', 'location_find', 'route_plan',
            'public_transport', 'flight_check', 'hotel_book', 'restaurant_find',
            
            # Productivity & Work
            'task_create', 'task_list', 'task_complete', 'note_create', 'note_search',
            'document_create', 'document_edit', 'file_search', 'app_launch',
            
            # Health & Fitness
            'health_track', 'exercise_log', 'medication_remind', 'appointment_schedule',
            'symptom_check', 'fitness_goal', 'sleep_track',
            
            # Shopping & Finance
            'shopping_list', 'product_search', 'price_compare', 'order_track',
            'payment_send', 'account_balance', 'expense_track', 'budget_check',
            
            # System & Control
            'settings_change', 'volume_adjust', 'brightness_control', 'wifi_connect',
            'device_status', 'system_update', 'backup_create', 'troubleshoot',
            
            # Conversational
            'greeting', 'goodbye', 'thank_you', 'help_request', 'complaint',
            'compliment', 'small_talk', 'clarification', 'confirmation'
        ]
        
        # Context tracking for conversation awareness
        self.context_embeddings = {}
        self.conversation_memory = []
        self.user_patterns = {}
        
    async def initialize(self) -> bool:
        """Initialize the advanced intent classifier with ML models"""
        if not ML_DEPENDENCIES_AVAILABLE:
            logger.warning("ML dependencies not available, using enhanced fallback")
            return await self._initialize_fallback()
        
        try:
            logger.info("Initializing Advanced Intent Classifier...")
            start_time = time.time()
            
            # Initialize BART model for zero-shot classification
            self.classifier_pipeline = pipeline(
                "zero-shot-classification",
                model="facebook/bart-large-mnli",
                device=0 if torch.cuda.is_available() else -1
            )
            
            # Initialize sentence transformer for semantic similarity
            self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Initialize spaCy for entity recognition
            try:
                self.nlp_model = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy English model not found, using basic entity extraction")
                self.nlp_model = None
            
            initialization_time = time.time() - start_time
            logger.info(f"Advanced Intent Classifier initialized in {initialization_time:.2f}s")
            
            self.initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Advanced Intent Classifier: {e}")
            return await self._initialize_fallback()
    
    async def _initialize_fallback(self) -> bool:
        """Initialize fallback rule-based classifier"""
        logger.info("Initializing fallback intent classifier...")
        self.initialized = True
        return True
    
    async def classify_intent(self, user_input: str, conversation_context: List[Dict] = None, 
                            user_id: str = None) -> Dict[str, Any]:
        """
        Advanced intent classification with context awareness and entity extraction
        
        Args:
            user_input: The user's message to classify
            conversation_context: Recent conversation history for context
            user_id: User identifier for personalization
            
        Returns:
            Comprehensive intent classification result with entities and confidence
        """
        if not self.initialized:
            await self.initialize()
        
        start_time = time.time()
        conversation_context = conversation_context or []
        
        try:
            # 1. Primary intent classification
            if ML_DEPENDENCIES_AVAILABLE and hasattr(self, 'classifier_pipeline'):
                intent_result = await self._ml_intent_classification(user_input)
            else:
                intent_result = await self._fallback_intent_classification(user_input)
            
            # 2. Context-aware refinement
            if conversation_context:
                intent_result = await self._refine_with_context(
                    user_input, intent_result, conversation_context
                )
            
            # 3. Entity extraction based on classified intent
            entities = await self._extract_entities(
                user_input, intent_result['primary_intent']['intent']
            )
            
            # 4. Confidence adjustment based on user patterns
            if user_id:
                intent_result = await self._adjust_with_user_patterns(
                    intent_result, user_id, user_input
                )
            
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            return {
                'primary_intent': intent_result['primary_intent'],
                'alternative_intents': intent_result.get('alternative_intents', []),
                'entities': entities,
                'context_used': bool(conversation_context),
                'user_personalized': bool(user_id),
                'processing_time_ms': round(processing_time, 2),
                'model_type': 'advanced_ml' if ML_DEPENDENCIES_AVAILABLE else 'enhanced_fallback',
                'confidence_factors': {
                    'base_confidence': intent_result['primary_intent']['confidence'],
                    'context_boost': intent_result.get('context_boost', 0),
                    'user_pattern_boost': intent_result.get('user_pattern_boost', 0)
                }
            }
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return {
                'primary_intent': {'intent': 'general_qa', 'confidence': 0.3},
                'alternative_intents': [],
                'entities': {},
                'context_used': False,
                'user_personalized': False,
                'processing_time_ms': (time.time() - start_time) * 1000,
                'model_type': 'error_fallback',
                'error': str(e)
            }
    
    async def _ml_intent_classification(self, user_input: str) -> Dict[str, Any]:
        """ML-based intent classification using BART zero-shot"""
        try:
            # Use BART for zero-shot classification
            result = self.classifier_pipeline(
                user_input,
                self.intent_categories,
                multi_label=False
            )
            
            # Process results
            primary_intent = {
                'intent': result['labels'][0],
                'confidence': float(result['scores'][0])
            }
            
            alternative_intents = [
                {
                    'intent': label,
                    'confidence': float(score)
                }
                for label, score in zip(result['labels'][1:4], result['scores'][1:4])
                if score > 0.1  # Minimum confidence threshold
            ]
            
            return {
                'primary_intent': primary_intent,
                'alternative_intents': alternative_intents,
                'classification_method': 'bart_zero_shot'
            }
            
        except Exception as e:
            logger.error(f"ML classification failed: {e}")
            return await self._fallback_intent_classification(user_input)
    
    async def _fallback_intent_classification(self, user_input: str) -> Dict[str, Any]:
        """Enhanced rule-based fallback classification"""
        user_lower = user_input.lower().strip()
        
        # Enhanced pattern matching with confidence scoring
        intent_patterns = {
            'email_send': [
                r'send.*email', r'email.*to', r'compose.*email', r'write.*email'
            ],
            'email_check': [
                r'check.*email', r'any.*email', r'new.*email', r'email.*inbox'
            ],
            'calendar_schedule': [
                r'schedule.*meeting', r'book.*appointment', r'set.*meeting', r'calendar.*add'
            ],
            'reminder_create': [
                r'remind.*me', r'set.*reminder', r'don\'t.*forget', r'remember.*to'
            ],
            'weather_query': [
                r'weather.*today', r'how.*hot', r'temperature.*outside', r'weather.*like'
            ],
            'music_play': [
                r'play.*music', r'play.*song', r'music.*on', r'listen.*to'
            ],
            'lights_control': [
                r'turn.*light', r'lights.*on', r'lights.*off', r'dim.*light'
            ],
            'navigation_start': [
                r'navigate.*to', r'directions.*to', r'how.*get.*to', r'route.*to'
            ],
            'calculation': [
                r'calculate', r'what.*is.*\d+', r'[\d+\-\*/]+', r'math.*problem'
            ],
            'greeting': [
                r'hello', r'hi\b', r'hey', r'good.*morning', r'good.*evening'
            ],
            'help_request': [
                r'help.*me', r'how.*do.*i', r'can.*you.*help', r'what.*can.*you'
            ]
        }
        
        intent_scores = {}
        
        for intent, patterns in intent_patterns.items():
            score = 0.0
            matches = 0
            
            for pattern in patterns:
                if re.search(pattern, user_lower):
                    matches += 1
                    # Score based on pattern specificity
                    pattern_weight = len(pattern) / 50.0
                    score += 0.7 + min(pattern_weight, 0.2)
            
            if matches > 0:
                # Bonus for multiple pattern matches
                score += (matches - 1) * 0.1
                intent_scores[intent] = min(score, 0.95)
        
        if intent_scores:
            # Sort by confidence
            sorted_intents = sorted(intent_scores.items(), key=lambda x: x[1], reverse=True)
            
            primary_intent = {
                'intent': sorted_intents[0][0],
                'confidence': sorted_intents[0][1]
            }
            
            alternative_intents = [
                {'intent': intent, 'confidence': confidence}
                for intent, confidence in sorted_intents[1:3]
            ]
        else:
            # Default classification
            if '?' in user_input:
                primary_intent = {'intent': 'general_qa', 'confidence': 0.6}
            else:
                primary_intent = {'intent': 'small_talk', 'confidence': 0.5}
            alternative_intents = []
        
        return {
            'primary_intent': primary_intent,
            'alternative_intents': alternative_intents,
            'classification_method': 'enhanced_rules'
        }
    
    async def _refine_with_context(self, user_input: str, intent_result: Dict, 
                                 context: List[Dict]) -> Dict[str, Any]:
        """Refine intent classification using conversation context"""
        if not context or not hasattr(self, 'sentence_model'):
            return intent_result
        
        try:
            # Create context representation
            context_messages = [msg.get('content', '') for msg in context[-5:]]
            context_text = ' '.join(context_messages)
            
            # Generate embeddings
            current_embedding = self.sentence_model.encode(user_input)
            context_embedding = self.sentence_model.encode(context_text)
            
            # Calculate semantic similarity
            similarity = np.dot(current_embedding, context_embedding) / (
                np.linalg.norm(current_embedding) * np.linalg.norm(context_embedding)
            )
            
            # Context-based intent boosting
            if similarity > 0.7:  # High contextual relevance
                primary_intent = intent_result['primary_intent']
                
                # Check if current intent is contextually relevant
                if self._is_contextually_relevant(primary_intent['intent'], context):
                    boost_factor = min(similarity * 0.3, 0.2)  # Max 20% boost
                    primary_intent['confidence'] = min(
                        primary_intent['confidence'] + boost_factor, 0.98
                    )
                    intent_result['context_boost'] = boost_factor
                    intent_result['context_similarity'] = float(similarity)
            
            return intent_result
            
        except Exception as e:
            logger.warning(f"Context refinement failed: {e}")
            return intent_result
    
    def _is_contextually_relevant(self, intent: str, context: List[Dict]) -> bool:
        """Check if intent is contextually relevant to conversation history"""
        
        # Intent continuation patterns
        continuation_patterns = {
            'email_send': ['email_check', 'contact_find', 'email_reply'],
            'calendar_schedule': ['calendar_check', 'reminder_create', 'timezone_convert'],
            'weather_query': ['weather_forecast', 'navigation_start', 'travel'],
            'music_play': ['volume_control', 'music_skip', 'music_search'],
            'navigation_start': ['traffic_check', 'location_find', 'weather_query']
        }
        
        # Get recent intents from context
        recent_intents = [
            msg.get('metadata', {}).get('intent', '') 
            for msg in context[-3:]
        ]
        
        # Check if current intent continues the conversation theme
        for recent_intent in recent_intents:
            if recent_intent in continuation_patterns:
                if intent in continuation_patterns[recent_intent]:
                    return True
            if intent in continuation_patterns:
                if recent_intent in continuation_patterns[intent]:
                    return True
        
        return False
    
    async def _extract_entities(self, text: str, intent: str) -> Dict[str, Any]:
        """Extract entities based on intent type using multiple extraction methods"""
        entities = {}
        
        try:
            # 1. spaCy-based entity extraction
            if self.nlp_model:
                entities.update(await self._spacy_entity_extraction(text))
            
            # 2. Intent-specific entity extraction
            entities.update(await self._intent_specific_extraction(text, intent))
            
            # 3. Custom pattern-based extraction
            entities.update(await self._pattern_based_extraction(text, intent))
            
            return entities
            
        except Exception as e:
            logger.warning(f"Entity extraction failed: {e}")
            return {}
    
    async def _spacy_entity_extraction(self, text: str) -> Dict[str, Any]:
        """Extract entities using spaCy NLP model"""
        if not self.nlp_model:
            return {}
        
        try:
            doc = self.nlp_model(text)
            
            entities = {
                'persons': [ent.text for ent in doc.ents if ent.label_ == "PERSON"],
                'organizations': [ent.text for ent in doc.ents if ent.label_ == "ORG"],
                'locations': [ent.text for ent in doc.ents if ent.label_ in ["GPE", "LOC"]],
                'dates': [ent.text for ent in doc.ents if ent.label_ == "DATE"],
                'times': [ent.text for ent in doc.ents if ent.label_ == "TIME"],
                'money': [ent.text for ent in doc.ents if ent.label_ == "MONEY"],
                'quantities': [ent.text for ent in doc.ents if ent.label_ == "QUANTITY"]
            }
            
            # Remove empty lists
            return {k: v for k, v in entities.items() if v}
            
        except Exception as e:
            logger.warning(f"spaCy entity extraction failed: {e}")
            return {}
    
    async def _intent_specific_extraction(self, text: str, intent: str) -> Dict[str, Any]:
        """Extract entities specific to the classified intent"""
        entities = {}
        
        try:
            if intent in ['reminder_create', 'calendar_schedule', 'timer_set']:
                entities.update(await self._extract_time_entities(text))
                entities.update(await self._extract_task_entities(text))
                
            elif intent in ['weather_query', 'weather_forecast']:
                entities.update(await self._extract_location_entities(text))
                entities.update(await self._extract_time_entities(text))
                
            elif intent in ['email_send', 'message_send', 'call_make']:
                entities.update(await self._extract_contact_entities(text))
                entities.update(await self._extract_communication_content(text))
                
            elif intent in ['music_play', 'video_play', 'podcast_play']:
                entities.update(await self._extract_media_entities(text))
                
            elif intent in ['navigation_start', 'location_find']:
                entities.update(await self._extract_location_entities(text))
                entities.update(await self._extract_transportation_entities(text))
                
            elif intent in ['calculation', 'unit_conversion']:
                entities.update(await self._extract_mathematical_entities(text))
                
            elif intent in ['shopping_list', 'product_search']:
                entities.update(await self._extract_product_entities(text))
                
            return entities
            
        except Exception as e:
            logger.warning(f"Intent-specific entity extraction failed: {e}")
            return {}
    
    async def _extract_time_entities(self, text: str) -> Dict[str, Any]:
        """Extract time-related entities"""
        time_entities = {}
        
        if DATE_PARSING_AVAILABLE:
            try:
                # Parse natural language dates/times
                parsed_time = dateparser.parse(text)
                if parsed_time:
                    time_entities['parsed_datetime'] = parsed_time.isoformat()
                    time_entities['date_string'] = parsed_time.strftime('%Y-%m-%d')
                    time_entities['time_string'] = parsed_time.strftime('%H:%M:%S')
            except Exception:
                pass
        
        # Pattern-based time extraction
        time_patterns = {
            'time_expressions': re.findall(r'\b\d{1,2}:\d{2}(?:\s*[ap]m)?\b', text, re.IGNORECASE),
            'date_expressions': re.findall(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', text),
            'relative_time': re.findall(r'\b(?:tomorrow|today|yesterday|next week|next month)\b', text, re.IGNORECASE),
            'duration': re.findall(r'\b\d+\s*(?:minute|hour|day|week|month)s?\b', text, re.IGNORECASE)
        }
        
        # Remove empty lists
        time_entities.update({k: v for k, v in time_patterns.items() if v})
        
        return time_entities
    
    async def _extract_task_entities(self, text: str) -> Dict[str, Any]:
        """Extract task-related entities for reminders and todos"""
        task_entities = {}
        
        # Task action patterns
        action_patterns = re.findall(
            r'\b(?:call|email|buy|pick up|finish|complete|submit|review|meet)\b',
            text, re.IGNORECASE
        )
        
        if action_patterns:
            task_entities['actions'] = list(set(action_patterns))
        
        # Task objects/subjects
        # Simple approach: extract nouns after action words
        task_subjects = re.findall(
            r'(?:call|email|buy|pick up|finish|complete|submit|review|meet)\s+([^,\.]+)',
            text, re.IGNORECASE
        )
        
        if task_subjects:
            task_entities['subjects'] = [subj.strip() for subj in task_subjects]
        
        return task_entities
    
    async def _extract_location_entities(self, text: str) -> Dict[str, Any]:
        """Extract location-related entities"""
        location_entities = {}
        
        # Common location patterns
        location_patterns = {
            'cities': re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text),
            'addresses': re.findall(r'\d+\s+[A-Za-z\s]+(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)', text),
            'zip_codes': re.findall(r'\b\d{5}(?:-\d{4})?\b', text),
            'countries': re.findall(r'\b(?:USA|United States|Canada|UK|United Kingdom|Australia|Germany|France|Japan|China|India)\b', text, re.IGNORECASE)
        }
        
        # Remove empty lists and filter out common false positives
        for key, values in location_patterns.items():
            if values:
                location_entities[key] = list(set(values))
        
        return location_entities
    
    async def _extract_contact_entities(self, text: str) -> Dict[str, Any]:
        """Extract contact-related entities"""
        contact_entities = {}
        
        # Email addresses
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if emails:
            contact_entities['email_addresses'] = emails
        
        # Phone numbers
        phones = re.findall(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', text)
        if phones:
            contact_entities['phone_numbers'] = phones
        
        # Names (simple approach - capitalize words)
        potential_names = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        if potential_names:
            contact_entities['potential_names'] = potential_names
        
        return contact_entities
    
    async def _extract_communication_content(self, text: str) -> Dict[str, Any]:
        """Extract content for emails/messages"""
        content_entities = {}
        
        # Subject line detection
        subject_match = re.search(r'(?:subject|title)[:]\s*(.+)', text, re.IGNORECASE)
        if subject_match:
            content_entities['subject'] = subject_match.group(1).strip()
        
        # Message body detection
        body_patterns = [
            r'(?:tell|say|write).*?["\'](.+?)["\']',
            r'(?:message|email)[:]\s*(.+)',
            r'(?:send).*?["\'](.+?)["\']'
        ]
        
        for pattern in body_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                content_entities['message_body'] = match.group(1).strip()
                break
        
        return content_entities
    
    async def _extract_media_entities(self, text: str) -> Dict[str, Any]:
        """Extract media-related entities for music/video requests"""
        media_entities = {}
        
        # Song/artist patterns
        music_patterns = {
            'song_titles': re.findall(r'(?:play|song).*?["\'](.+?)["\']', text, re.IGNORECASE),
            'artists': re.findall(r'(?:by|artist)[:]\s*([^,\.]+)', text, re.IGNORECASE),
            'genres': re.findall(r'\b(?:rock|pop|jazz|classical|hip hop|country|electronic|folk|blues)\b', text, re.IGNORECASE),
            'albums': re.findall(r'(?:album)[:]\s*([^,\.]+)', text, re.IGNORECASE)
        }
        
        # Remove empty lists
        media_entities.update({k: v for k, v in music_patterns.items() if v})
        
        return media_entities
    
    async def _extract_mathematical_entities(self, text: str) -> Dict[str, Any]:
        """Extract mathematical expressions and numbers"""
        math_entities = {}
        
        # Mathematical expressions
        math_expressions = re.findall(r'[\d+\-*/().\s]+', text)
        if math_expressions:
            math_entities['expressions'] = [expr.strip() for expr in math_expressions if expr.strip()]
        
        # Numbers
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        if numbers:
            math_entities['numbers'] = [float(num) if '.' in num else int(num) for num in numbers]
        
        # Units
        units = re.findall(r'\b(?:feet|meters|inches|pounds|kilograms|celsius|fahrenheit|miles|kilometers)\b', text, re.IGNORECASE)
        if units:
            math_entities['units'] = list(set(units))
        
        return math_entities
    
    async def _extract_product_entities(self, text: str) -> Dict[str, Any]:
        """Extract product and shopping-related entities"""
        product_entities = {}
        
        # Product categories
        categories = re.findall(r'\b(?:electronics|clothing|food|books|toys|furniture|appliances|tools|sports|beauty)\b', text, re.IGNORECASE)
        if categories:
            product_entities['categories'] = list(set(categories))
        
        # Brands (common ones)
        brands = re.findall(r'\b(?:Apple|Samsung|Nike|Adidas|Sony|Microsoft|Google|Amazon|Tesla|BMW|Mercedes)\b', text, re.IGNORECASE)
        if brands:
            product_entities['brands'] = list(set(brands))
        
        # Quantities
        quantities = re.findall(r'\b\d+\s*(?:of|x|pieces?|items?|units?)\b', text, re.IGNORECASE)
        if quantities:
            product_entities['quantities'] = quantities
        
        return product_entities
    
    async def _pattern_based_extraction(self, text: str, intent: str) -> Dict[str, Any]:
        """Additional pattern-based entity extraction"""
        pattern_entities = {}
        
        # URL extraction
        urls = re.findall(r'https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?', text)
        if urls:
            pattern_entities['urls'] = urls
        
        # Currency amounts
        currency = re.findall(r'\$\d+(?:\.\d{2})?|\d+\s*(?:dollars?|cents?|USD)', text, re.IGNORECASE)
        if currency:
            pattern_entities['currency'] = currency
        
        # File extensions
        files = re.findall(r'\w+\.(?:pdf|doc|docx|txt|jpg|png|mp3|mp4|xlsx|pptx)', text, re.IGNORECASE)
        if files:
            pattern_entities['files'] = files
        
        return pattern_entities
    
    async def _adjust_with_user_patterns(self, intent_result: Dict, user_id: str, 
                                       user_input: str) -> Dict[str, Any]:
        """Adjust intent confidence based on user interaction patterns"""
        # This would integrate with user analytics/learning system
        # For now, implement basic pattern tracking
        
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = {
                'common_intents': {},
                'preferred_style': 'neutral',
                'interaction_count': 0
            }
        
        user_pattern = self.user_patterns[user_id]
        primary_intent = intent_result['primary_intent']['intent']
        
        # Track intent frequency
        if primary_intent in user_pattern['common_intents']:
            user_pattern['common_intents'][primary_intent] += 1
        else:
            user_pattern['common_intents'][primary_intent] = 1
        
        user_pattern['interaction_count'] += 1
        
        # Boost confidence for frequently used intents
        if user_pattern['interaction_count'] > 10:  # Enough data for patterns
            intent_frequency = user_pattern['common_intents'].get(primary_intent, 0)
            total_interactions = user_pattern['interaction_count']
            
            if intent_frequency / total_interactions > 0.2:  # Intent used >20% of the time
                boost = min(0.1, intent_frequency / total_interactions * 0.5)
                intent_result['primary_intent']['confidence'] += boost
                intent_result['user_pattern_boost'] = boost
        
        return intent_result

# Global instance
advanced_intent_classifier = AdvancedIntentClassifier()

async def get_advanced_intent_classifier() -> AdvancedIntentClassifier:
    """Get the global advanced intent classifier instance"""
    if not advanced_intent_classifier.initialized:
        await advanced_intent_classifier.initialize()
    return advanced_intent_classifier
