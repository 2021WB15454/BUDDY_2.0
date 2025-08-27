"""Core skill abstractions for BUDDY.

Provides:
 - SkillSchema: descriptive metadata
 - SkillResult: standardized execution outcome
 - BaseSkill: lifecycle + execution contract
 - SkillsRegistry: registration / lookup / broadcasting utilities
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Callable, Awaitable, List
import abc
import logging

logger = logging.getLogger(__name__)

@dataclass
class SkillSchema:
    name: str
    version: str = "0.1.0"
    description: str = ""
    category: str = "general"
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_schema: Dict[str, Any] = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    requires_online: bool = False
    timeout_ms: int = 5000

@dataclass
class SkillResult:
    success: bool
    result_metadata: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_result_metadata: Optional[str] = None

class BaseSkill(abc.ABC):
    schema: SkillSchema
    enabled: bool = True

    def __init__(self, event_bus=None):
        self.event_bus = event_bus

    async def initialize(self) -> bool:  # optional override
        return True

    @abc.abstractmethod
    async def execute(self, parameters: Dict[str, Any], context: Dict[str, Any]) -> SkillResult:  # pragma: no cover
        ...

    async def cleanup(self) -> None:  # optional override
        return None


class SkillsRegistry:
    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill):
        name = getattr(skill, 'schema', None) and skill.schema.name or skill.__class__.__name__.lower()
        if name in self._skills:
            logger.warning(f"skill_already_registered skill={name}")
        self._skills[name] = skill
        logger.info(f"skill_registered skill={name}")

    def get(self, name: str) -> Optional[BaseSkill]:
        return self._skills.get(name)

    def list(self) -> List[str]:
        return list(self._skills.keys())

    async def initialize_all(self):
        for s in self._skills.values():
            try:
                await s.initialize()
            except Exception as e:
                _nm = s.schema.name if getattr(s, 'schema', None) else s.__class__.__name__
                logger.error(f"skill_init_failed skill={_nm} error={e}")
                s.enabled = False

    async def cleanup_all(self):
        for s in self._skills.values():
            try:
                await s.cleanup()
            except Exception:
                pass

skills_registry = SkillsRegistry()
