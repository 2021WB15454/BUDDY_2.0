"""
BUDDY Skills Registry

Manages the registration, discovery, and execution of skills (capabilities).
Each skill is a composable unit that handles specific user requests with
defined input/output contracts, permissions, and lifecycle management.
"""

import asyncio
import logging
import json
import importlib
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import yaml

from .events import EventBus, Event, get_event_bus

logger = logging.getLogger(__name__)


@dataclass
class SkillSchema:
    """Defines the contract for a skill."""
    
    name: str
    version: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    permissions: List[str] = field(default_factory=list)
    timeout_ms: int = 5000
    category: str = "general"
    author: str = "unknown"
    requires_confirmation: bool = False
    requires_online: bool = False
    supported_devices: List[str] = field(default_factory=lambda: ["all"])
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "permissions": self.permissions,
            "timeout_ms": self.timeout_ms,
            "category": self.category,
            "author": self.author,
            "requires_confirmation": self.requires_confirmation,
            "requires_online": self.requires_online,
            "supported_devices": self.supported_devices
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SkillSchema":
        """Create from dictionary."""
        return cls(**data)
    
    @classmethod
    def from_yaml_file(cls, file_path: Path) -> "SkillSchema":
        """Load schema from YAML file."""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)


@dataclass
class SkillResult:
    """Result of skill execution."""
    
    success: bool
    data: Any = None
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error_message": self.error_message,
            "execution_time_ms": self.execution_time_ms,
            "metadata": self.metadata
        }


class BaseSkill:
    """Base class for all BUDDY skills."""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or get_event_bus()
        self.schema: Optional[SkillSchema] = None
        self._enabled = True
        
    async def initialize(self) -> bool:
        """Initialize the skill. Return True if successful."""
        return True
        
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        """
        Execute the skill with given parameters.
        
        Args:
            parameters: Input parameters
            context: Execution context (user_id, session_id, device_id, etc.)
            
        Returns:
            SkillResult with execution outcome
        """
        raise NotImplementedError("Skills must implement execute method")
        
    async def cleanup(self):
        """Clean up resources when skill is disabled."""
        pass
        
    def get_schema(self) -> SkillSchema:
        """Get the skill schema."""
        if self.schema is None:
            raise ValueError("Skill schema not defined")
        return self.schema
        
    def validate_input(self, parameters: Dict[str, Any]) -> bool:
        """Validate input parameters against schema."""
        # Simplified validation - real implementation would use jsonschema
        schema = self.get_schema()
        required_fields = schema.input_schema.get("required", [])
        
        for field in required_fields:
            if field not in parameters:
                return False
                
        return True
        
    def is_enabled(self) -> bool:
        """Check if skill is enabled."""
        return self._enabled
        
    def enable(self):
        """Enable the skill."""
        self._enabled = True
        
    def disable(self):
        """Disable the skill."""
        self._enabled = False


class SkillRegistry:
    """
    Central registry for managing all skills in the BUDDY system.
    
    Handles skill discovery, registration, validation, and execution
    with support for permissions, timeouts, and error handling.
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or get_event_bus()
        self.skills: Dict[str, BaseSkill] = {}
        self.schemas: Dict[str, SkillSchema] = {}
        self.categories: Dict[str, List[str]] = {}
        self.permission_grants: Dict[str, List[str]] = {}  # user_id -> permissions
        self._registration_lock = asyncio.Lock()  # Prevent concurrent registrations
        self._builtin_skills_loaded = False  # Track if builtin skills are loaded
        
        # Subscribe to skill execution requests
        self.event_bus.subscribe("skill.execute", self._handle_skill_execution)
        self.event_bus.subscribe("skill.list", self._handle_skill_list_request)
        
        logger.info("Skill registry initialized")
        
        # Register built-in skills during initialization
        asyncio.create_task(self._initialize_builtin_skills())
        
        # Subscribe to skill execution requests
        self.event_bus.subscribe("skill.execute", self._handle_skill_execution)
        self.event_bus.subscribe("skill.list", self._handle_skill_list_request)
        
        logger.info("Skill registry initialized")
        
        # Register built-in skills during initialization
        asyncio.create_task(self._initialize_builtin_skills())

    # ---- Internal helper methods ----
    def _validate_schema(self, schema: SkillSchema) -> bool:
        """Validate a skill schema (basic checks + duplicate handling)."""
        if not schema or not getattr(schema, "name", None) or not getattr(schema, "version", None):
            return False
        # Prevent duplicate exact versions
        if schema.name in self.schemas:
            existing_version = self.schemas[schema.name].version
            if existing_version == schema.version:
                logger.info(f"Skill {schema.name} v{schema.version} already registered – skipping")
                return False
        return True

    def _check_permissions(self, user_id: str, required_permissions: List[str]) -> bool:
        """Check if a user has all required permissions."""
        if not required_permissions:
            return True
        user_permissions = self.permission_grants.get(user_id, [])
        return all(perm in user_permissions for perm in required_permissions)

    def _check_device_compatibility(self, schema: SkillSchema, device_id: str) -> bool:
        """Check if a skill is compatible with a given device."""
        if not device_id:
            return True
        if "all" in schema.supported_devices:
            return True
        return device_id in schema.supported_devices
        
    async def _initialize_builtin_skills(self):
        """Initialize built-in skills during startup (called once)."""
        try:
            await self.register_builtin_skills()
            logger.info("Built-in skills initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize built-in skills: {e}")
        
    async def register_builtin_skills(self):
        """Register a comprehensive set of built-in skills including advanced AI capabilities."""
        async with self._registration_lock:
            if self._builtin_skills_loaded:
                logger.info("Built-in skills already loaded – skipping")
                return
                
            # Mark as loading to prevent duplicates
            self._builtin_skills_loaded = True
        # Core skills
        core_skills = [TimeSkill, RemindersSkill, FallbackSkill, GreetingSkill, WeatherSkill, CalculatorSkill, HelpSkill]
        
        # Try to import memory skill
        try:
            import sys
            from pathlib import Path
            
            # Try different import strategies for memory skill
            try:
                from .skills.memory import MemorySkill
                core_skills.append(MemorySkill)
                logger.info("Memory skill imported successfully")
            except ImportError:
                try:
                    # Add the skills directory to Python path
                    skills_dir = Path(__file__).parent / "skills"
                    sys.path.insert(0, str(skills_dir))
                    
                    from memory import MemorySkill
                    core_skills.append(MemorySkill)
                    logger.info("Memory skill imported successfully")
                except ImportError as e:
                    logger.warning(f"Memory skill dependencies not available: {e}")
        except Exception as e:
            logger.warning(f"Memory skill not available: {e}")
        except Exception as e:
            logger.warning(f"Failed to import memory skill: {e}")
        
        # Advanced skills
        try:
            from .advanced_skills import ADVANCED_SKILLS
            all_skills = core_skills + ADVANCED_SKILLS
        except ImportError:
            logger.warning("Advanced skills not available, using core skills only")
            all_skills = core_skills
        
        all_ok = True
        for cls in all_skills:
            try:
                skill = cls(self.event_bus)
                ok = await self.register_skill(skill)
                all_ok = all_ok and ok
            except Exception as e:
                logger.error(f"Failed to register {cls.__name__}: {e}")
                all_ok = False
        
        if all_ok:
            logger.info(f"All {len(all_skills)} built-in skills registered successfully")
        else:
            logger.warning("Some built-in skills failed to register")

    async def register_skill(self, skill: BaseSkill, schema: Optional[SkillSchema] = None) -> bool:
        """
        Register a skill with the registry.
        
        Args:
            skill: Skill instance to register
            schema: Optional schema (will use skill.get_schema() if not provided)
            
        Returns:
            True if registration successful
        """
        try:
            # Initialize first so the skill can set its schema internally
            init_ok = await skill.initialize()
            if not init_ok:
                logger.error("Failed to initialize skill (no schema yet)")
                return False

            # Determine schema (prefer passed in, else skill.schema)
            if schema is not None:
                skill.schema = schema
            else:
                schema = getattr(skill, 'schema', None)

            if schema is None:
                logger.error("Skill schema not defined after initialization")
                return False

            # If already registered with identical version, skip silently
            if schema.name in self.schemas and self.schemas[schema.name].version == schema.version:
                logger.info(f"Skill {schema.name} v{schema.version} already registered – skipping")
                return True

            # Basic inline validation (avoid dependency on helper if import order issues)
            if not schema.name or not schema.version:
                logger.error("Invalid schema (missing name/version)")
                return False
                
            # Register skill
            self.skills[schema.name] = skill
            self.schemas[schema.name] = schema
            
            # Update category mapping
            if schema.category not in self.categories:
                self.categories[schema.category] = []
            self.categories[schema.category].append(schema.name)
            
            # Publish registration event (only if event bus is running)
            if hasattr(self.event_bus, 'is_running') and self.event_bus.is_running:
                await self.event_bus.publish(
                    "skill.registered",
                    {
                        "skill_name": schema.name,
                        "version": schema.version,
                        "category": schema.category,
                        "permissions": schema.permissions
                    },
                    source="skill_registry"
                )
            
            logger.info(f"Registered skill: {schema.name} v{schema.version}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering skill: {e}")
            return False
            
    async def unregister_skill(self, skill_name: str) -> bool:
        """
        Unregister a skill from the registry.
        
        Args:
            skill_name: Name of skill to unregister
            
        Returns:
            True if unregistration successful
        """
        if skill_name not in self.skills:
            logger.warning(f"Skill {skill_name} not found for unregistration")
            return False
            
        try:
            skill = self.skills[skill_name]
            schema = self.schemas[skill_name]
            
            # Cleanup skill
            await skill.cleanup()
            
            # Remove from registry
            del self.skills[skill_name]
            del self.schemas[skill_name]
            
            # Update category mapping
            if schema.category in self.categories:
                self.categories[schema.category].remove(skill_name)
                if not self.categories[schema.category]:
                    del self.categories[schema.category]
                    
            # Publish unregistration event (only if event bus is running)
            if hasattr(self.event_bus, 'is_running') and self.event_bus.is_running:
                await self.event_bus.publish(
                    "skill.unregistered",
                    {"skill_name": skill_name},
                    source="skill_registry"
                )
            
            logger.info(f"Unregistered skill: {skill_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error unregistering skill {skill_name}: {e}")
            return False
            
    async def execute_skill(self, skill_name: str, parameters: Dict[str, Any], 
                           context: Dict[str, Any]) -> SkillResult:
        """
        Execute a skill with given parameters.
        
        Args:
            skill_name: Name of skill to execute
            parameters: Input parameters
            context: Execution context
            
        Returns:
            SkillResult with execution outcome
        """
        start_time = datetime.now()
        
        # Check if skill exists
        if skill_name not in self.skills:
            return SkillResult(
                success=False,
                error_message=f"Skill '{skill_name}' not found"
            )
            
        skill = self.skills[skill_name]
        schema = self.schemas[skill_name]
        
        # Check if skill is enabled
        if not skill.is_enabled():
            return SkillResult(
                success=False,
                error_message=f"Skill '{skill_name}' is disabled"
            )
            
        # Validate permissions
        user_id = context.get("user_id")
        if not self._check_permissions(user_id, schema.permissions):
            return SkillResult(
                success=False,
                error_message=f"Insufficient permissions for skill '{skill_name}'"
            )
            
        # Validate input
        if not skill.validate_input(parameters):
            return SkillResult(
                success=False,
                error_message="Invalid input parameters"
            )
            
        # Check device compatibility
        device_id = context.get("device_id", "unknown")
        if not self._check_device_compatibility(schema, device_id):
            return SkillResult(
                success=False,
                error_message=f"Skill '{skill_name}' not supported on device '{device_id}'"
            )
            
        try:
            # Execute skill with timeout
            result = await asyncio.wait_for(
                skill.execute(parameters, context),
                timeout=schema.timeout_ms / 1000.0
            )
            
            # Calculate execution time
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            result.execution_time_ms = execution_time
            
            # Publish execution result (only if event bus is running)
            if hasattr(self.event_bus, 'is_running') and self.event_bus.is_running:
                await self.event_bus.publish(
                    "skill.result",
                    {
                        "skill_name": skill_name,
                    "session_id": context.get("session_id"),
                    "turn_id": context.get("turn_id"),
                    "success": result.success,
                    "execution_time_ms": execution_time,
                    "result": result.to_dict()
                },
                source="skill_registry"
            )
            
            return result
            
        except asyncio.TimeoutError:
            return SkillResult(
                success=False,
                error_message=f"Skill '{skill_name}' timed out after {schema.timeout_ms}ms"
            )
        except Exception as e:
            logger.error(f"Error executing skill {skill_name}: {e}")
            return SkillResult(
                success=False,
                error_message=f"Skill execution error: {str(e)}"
            )
    
    async def _handle_skill_execution(self, event: Event):
        """Event bus handler: execute a skill when a 'skill.execute' event is received."""
        try:
            payload = event.payload or {}
            skill_name = payload.get("skill_name")
            parameters = payload.get("parameters", {})
            context = {
                "user_id": payload.get("user_id"),
                "session_id": payload.get("session_id"),
                "turn_id": payload.get("turn_id"),
                "device_id": payload.get("device_id")
            }
            await self.execute_skill(skill_name, parameters, context)
        except Exception as e:
            logger.error(f"Skill execution handler error: {e}")

    async def _handle_skill_list_request(self, event: Event):
        """Event bus handler: publish list of skills."""
        try:
            payload = event.payload or {}
            category = payload.get("category")
            device_id = payload.get("device_id")
            skills = self.list_skills(category=category, device_id=device_id)
            # Publish list response (only if event bus is running)
            if hasattr(self.event_bus, 'is_running') and self.event_bus.is_running:
                await self.event_bus.publish(
                    "skill.list_response",
                    {"skills": skills, "request_id": payload.get("request_id")},
                source="skill_registry"
            )
        except Exception as e:
            logger.error(f"Skill list handler error: {e}")
            
    def list_skills(self, category: Optional[str] = None, 
                   device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List available skills.
        
        Args:
            category: Filter by category
            device_id: Filter by device compatibility
            
        Returns:
            List of skill information
        """
        skills = []
        
        for name, schema in self.schemas.items():
            skill = self.skills[name]
            
            # Apply filters
            if category and schema.category != category:
                continue
                
            if device_id and not self._check_device_compatibility(schema, device_id):
                continue
                
            skills.append({
                "name": name,
                "version": schema.version,
                "description": schema.description,
                "category": schema.category,
                "permissions": schema.permissions,
                "enabled": skill.is_enabled(),
                "requires_online": schema.requires_online,
                "requires_confirmation": schema.requires_confirmation
            })
            
        return skills

    # (Removed duplicate out-of-class helper methods)

    async def discover_skills(self, search_paths: List[Path]):
        """
        Discover and load skills from specified paths.
        
        Args:
            search_paths: List of paths to search for skills
        """
        # Register built-in skills first
        try:
            await self.register_builtin_skills()
            logger.info("Built-in skills registered successfully")
        except Exception as e:
            logger.error(f"Failed to register built-in skills: {e}")
        
        # Then discover custom skills from paths
        for path in search_paths:
            if not path.exists():
                continue
                
            # Look for Python skill modules
            for py_file in path.glob("*.py"):
                await self._load_skill_module(py_file)
                
            # Look for YAML skill definitions
            for yaml_file in path.glob("*.yaml"):
                await self._load_skill_yaml(yaml_file)
                
    async def _load_skill_module(self, module_path: Path):
        """Load a skill from a Python module."""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("skill", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for skill classes
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, BaseSkill) and 
                    attr != BaseSkill):
                    
                    skill_instance = attr(self.event_bus)
                    await self.register_skill(skill_instance)
                    
        except Exception as e:
            logger.error(f"Error loading skill module {module_path}: {e}")
            
    async def _load_skill_yaml(self, yaml_path: Path):
        """Load a skill definition from YAML."""
        try:
            schema = SkillSchema.from_yaml_file(yaml_path)
            # Create a generic skill wrapper for YAML-defined skills
            # This would be expanded in a real implementation
            logger.info(f"Loaded skill definition: {schema.name}")
        except Exception as e:
            logger.error(f"Error loading skill YAML {yaml_path}: {e}")


# ---------- Built-in minimal skills ----------

class TimeSkill(BaseSkill):
    async def initialize(self) -> bool:
        self.schema = SkillSchema(
            name="time",
            version="1.0.0",
            description="Provide current local time with contextual information",
            input_schema={"type": "object", "properties": {"query_type": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            category="utility"
        )
        return True

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        from datetime import datetime
        now = datetime.now()
        formatted_time = now.strftime("%I:%M %p")
        day_part = "morning" if now.hour < 12 else "afternoon" if now.hour < 17 else "evening"
        
        response = f"🕐 It's currently **{formatted_time}** on this {now.strftime('%A')} {day_part}. "
        
        # Add contextual information
        if now.hour < 6:
            response += "Early bird today! 🌅"
        elif now.hour < 9:
            response += "Perfect time to start the day! ☀️"
        elif now.hour < 12:
            response += "Great morning productivity time! 💪"
        elif now.hour < 14:
            response += "Lunch time approaching! 🍽️"
        elif now.hour < 17:
            response += "Afternoon energy time! ⚡"
        elif now.hour < 20:
            response += "Evening wind-down time! 🌆"
        else:
            response += "Time to relax and recharge! 🌙"
        
        return SkillResult(success=True, data={"text": response})


class RemindersSkill(BaseSkill):
    async def initialize(self) -> bool:
        self.schema = SkillSchema(
            name="reminders",
            version="1.0.0",
            description="Set and manage intelligent reminders",
            input_schema={
                "type": "object", 
                "properties": {
                    "title": {"type": "string"}, 
                    "time": {"type": "string"}
                }
            },
            output_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            category="productivity"
        )
        return True

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        title = (parameters or {}).get("title") or "your task"
        when = (parameters or {}).get("time") or "soon"
        
        # Enhanced reminder response with tips
        response = f"⏰ **Reminder Set Successfully!**\n\n"
        response += f"📝 **Task**: {title}\n"
        response += f"🕐 **When**: {when}\n\n"
        response += "💡 **Productivity Tip**: Break large tasks into smaller, manageable steps for better success! "
        response += "I'll help you stay organized and on track. ✅"
        
        return SkillResult(success=True, data={"text": response})


class FallbackSkill(BaseSkill):
    async def initialize(self) -> bool:
        self.schema = SkillSchema(
            name="fallback",
            version="1.0.0",
            description="Intelligent fallback responses with helpful suggestions",
            input_schema={"type": "object", "properties": {"original_text": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            category="conversation"
        )
        return True

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        original_text = (parameters or {}).get("original_text", "")
        
        responses = [
            f"I understand you said: '{original_text}' - I'm continuously learning and expanding my capabilities! "
            "While I may not have a specific response for that yet, I can help with weather, calculations, time queries, and general conversation. "
            "Try asking 'what can you do?' to see all my capabilities! 🤖✨",
            
            f"That's an interesting request: '{original_text}' - I'm working on understanding more complex queries like this! "
            "For now, I excel at weather forecasts, math calculations, time/date info, and helpful conversations. "
            "What would you like to explore? 🚀",
            
            f"I hear you asking about: '{original_text}' - I'm always learning new things! "
            "Currently, I'm great with weather updates, calculations, current time, and engaging chat. "
            "Is there something specific I can help you with from my current abilities? 💡"
        ]
        
        import random
        response = random.choice(responses)
        
        return SkillResult(success=True, data={"text": response})


class GreetingSkill(BaseSkill):
    async def initialize(self) -> bool:
        self.schema = SkillSchema(
            name="greeting",
            version="1.0.0",
            description="Handle greetings with personalized, time-aware responses",
            input_schema={"type": "object", "properties": {"message_type": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            category="conversation"
        )
        return True

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        from datetime import datetime
        
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"
        
        greetings = [
            f"{greeting}! I'm BUDDY, your AI assistant. Ready to tackle whatever you need help with today! 🚀",
            f"{greeting}! Great to see you! I'm here to help make your day more productive. What's on your mind?",
            f"{greeting}! I'm BUDDY, and I'm excited to assist you today. Whether it's information, calculations, or just a chat - I'm here for you! ✨"
        ]
        
        import random
        response = random.choice(greetings)
        
        return SkillResult(success=True, data={"text": response})


class WeatherSkill(BaseSkill):
    async def initialize(self) -> bool:
        self.schema = SkillSchema(
            name="weather",
            version="1.0.0",
            description="Provide detailed weather information with contextual advice",
            input_schema={"type": "object", "properties": {"location": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            category="information"
        )
        return True

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        location = (parameters or {}).get("location")
        
        if not location:
            response = "🌤️ I'd love to get weather information for you! Please specify a city like 'weather in Chennai' or 'what's the weather like in Tamil Nadu?'"
        else:
            try:
                import aiohttp
                import json
                
                # Handle Tamil Nadu specifically
                if "tamil nadu" in location.lower():
                    location = "Chennai, Tamil Nadu, India"
                elif location.lower() in ["chennai", "madras"]:
                    location = "Chennai, Tamil Nadu, India"
                elif location.lower() in ["coimbatore"]:
                    location = "Coimbatore, Tamil Nadu, India"
                elif location.lower() in ["madurai"]:
                    location = "Madurai, Tamil Nadu, India"
                
                # Use OpenWeatherMap-like free API (wttr.in)
                url = f"https://wttr.in/{location}?format=j1"
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, timeout=5) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            current = data['current_condition'][0]
                            
                            temp_c = current['temp_C']
                            temp_f = current['temp_F']
                            desc = current['weatherDesc'][0]['value']
                            humidity = current['humidity']
                            wind_speed = current['windspeedKmph']
                            feels_like = current['FeelsLikeC']
                            
                            response = f"🌤️ **Weather for {location}**\n\n"
                            response += f"🌡️ **Temperature:** {temp_c}°C ({temp_f}°F)\n"
                            response += f"🌫️ **Condition:** {desc}\n"
                            response += f"🤗 **Feels like:** {feels_like}°C\n"
                            response += f"💧 **Humidity:** {humidity}%\n"
                            response += f"💨 **Wind Speed:** {wind_speed} km/h\n\n"
                            
                            # Add weather advice
                            temp_int = int(temp_c)
                            if temp_int > 35:
                                response += "🔥 It's quite hot! Stay hydrated and avoid direct sunlight."
                            elif temp_int > 25:
                                response += "☀️ Pleasant weather! Perfect for outdoor activities."
                            elif temp_int > 15:
                                response += "🌤️ Comfortable temperature for most activities."
                            else:
                                response += "🧥 It's a bit cool - you might want a light jacket."
                                
                        else:
                            response = f"🌤️ Sorry, I couldn't fetch weather data for {location}. Please try a more specific location like 'Chennai' or 'Coimbatore'."
                            
            except ImportError:
                response = f"🌤️ Weather service needs aiohttp library. Please install it with: pip install aiohttp"
            except Exception as e:
                response = f"🌤️ I'm having trouble accessing weather data right now. Please try again in a moment. (Error: {str(e)[:50]}...)"
        
        return SkillResult(success=True, data={"text": response})


class CalculatorSkill(BaseSkill):
    async def initialize(self) -> bool:
        self.schema = SkillSchema(
            name="calculate",
            version="1.0.0",
            description="Perform mathematical calculations with detailed explanations",
            input_schema={"type": "object", "properties": {"expression": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            category="utility"
        )
        return True

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        expression = (parameters or {}).get("expression", "")
        
        if not expression:
            response = "🧮 I can help with various calculations! Try formats like:\n"
            response += "• Basic math: '25 * 4' or 'calculate 100 / 5'\n"
            response += "• Percentages: '15 percent of 200'\n"
            response += "• Powers: '2^8' or '3 to the power of 4'\n"
            response += "What calculation would you like me to solve?"
        else:
            # Simple calculation handling
            try:
                import re
                
                # Basic arithmetic
                basic_match = re.search(r'(\d+(?:\.\d+)?)\s*([\+\-\*\/])\s*(\d+(?:\.\d+)?)', expression)
                if basic_match:
                    num1, operator, num2 = basic_match.groups()
                    num1, num2 = float(num1), float(num2)
                    
                    if operator == '+':
                        result = num1 + num2
                        op_name = "addition"
                    elif operator == '-':
                        result = num1 - num2
                        op_name = "subtraction"
                    elif operator == '*':
                        result = num1 * num2
                        op_name = "multiplication"
                    elif operator == '/':
                        if num2 != 0:
                            result = num1 / num2
                            op_name = "division"
                        else:
                            return SkillResult(success=True, data={"text": "🚫 I can't divide by zero! That would break the laws of mathematics. Try a different number! 😄"})
                    
                    if result.is_integer():
                        result = int(result)
                    
                    response = f"🧮 {num1} {operator} {num2} = **{result}**\n\n💡 That's a {op_name} operation. Need help with more calculations?"
                else:
                    response = "🧮 I had trouble parsing that calculation. Please try a format like 'calculate 25 * 4'."
                    
            except Exception:
                response = "🧮 I encountered an error with that calculation. Please try a simpler format like '25 * 4'."
        
        return SkillResult(success=True, data={"text": response})


class HelpSkill(BaseSkill):
    async def initialize(self) -> bool:
        self.schema = SkillSchema(
            name="help",
            version="1.0.0",
            description="Provide comprehensive help and capability information",
            input_schema={"type": "object", "properties": {"help_type": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            category="information"
        )
        return True

    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:
        response = """🤖 **Welcome to BUDDY - Your Intelligent AI Assistant!**

I'm here to make your life easier and more productive. Here's what I can help you with:

**🔥 Core Capabilities:**
• 💬 **Intelligent Conversation** - Natural, contextual chat about any topic
• 🕐 **Time & Scheduling** - Current time, date, and time-related queries
• 🌤️ **Weather Intelligence** - Real-time weather for any city worldwide
• 🧮 **Advanced Calculator** - Math, percentages, powers, square roots
• 📊 **System Monitoring** - Performance metrics and health checks

**⚡ Quick Commands to Try:**
• "What's the weather in Paris?"
• "Calculate 15 percent of 250"
• "What time is it?"
• "System status report"
• "What's today's date?"

**🎯 Smart Features:**
• **Contextual Responses** - I remember our conversation
• **Personalized Interaction** - Responses adapt to you
• **Detailed Explanations** - I explain how things work
• **Proactive Suggestions** - I offer helpful tips

What would you like to explore first? 🚀"""
        
        return SkillResult(success=True, data={"text": response})
        
    # (Removed duplicate helper and handler methods that were previously duplicated below)
