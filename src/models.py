"""Core data models for the Agent Permission Guard system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PermissionCategory(Enum):
    """Categories of permissions an agent can hold."""
    WEB_ACCESS = "web_access"
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    SHELL_EXECUTION = "shell_execution"
    SKILL_CONNECTIONS = "skill_connections"
    NETWORK_OUTBOUND = "network_outbound"
    SYSTEM_MODIFICATION = "system_modification"


class PermissionScope(Enum):
    """How broadly a permission is granted."""
    UNRESTRICTED = "unrestricted"
    LIMITED = "limited"
    DISABLED = "disabled"


class TaskCapability(Enum):
    """High-level capabilities a task may require."""
    INFORMATION_GATHERING = "information_gathering"
    CONTENT_CREATION = "content_creation"
    CODE_EXECUTION = "code_execution"
    FILE_MANAGEMENT = "file_management"
    COMMUNICATION = "communication"
    SYSTEM_MODIFICATION = "system_modification"


class RiskLevel(Enum):
    """Severity levels for identified risks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def weight(self) -> int:
        return {
            RiskLevel.LOW: 1,
            RiskLevel.MEDIUM: 2,
            RiskLevel.HIGH: 3,
            RiskLevel.CRITICAL: 4,
        }[self]

    @property
    def label(self) -> str:
        return self.value.upper()


@dataclass
class Permission:
    """A single permission with its scope and details."""
    category: PermissionCategory
    scope: PermissionScope
    details: str = ""
    excess_reason: str = ""

    @property
    def is_active(self) -> bool:
        return self.scope != PermissionScope.DISABLED

    @property
    def risk_weight(self) -> int:
        """Inherent risk weight of this permission category."""
        weights = {
            PermissionCategory.WEB_ACCESS: 2,
            PermissionCategory.FILE_READ: 1,
            PermissionCategory.FILE_WRITE: 2,
            PermissionCategory.SHELL_EXECUTION: 3,
            PermissionCategory.SKILL_CONNECTIONS: 2,
            PermissionCategory.NETWORK_OUTBOUND: 3,
            PermissionCategory.SYSTEM_MODIFICATION: 3,
        }
        base = weights.get(self.category, 1)
        if self.scope == PermissionScope.UNRESTRICTED:
            return base * 2
        return base


@dataclass
class RiskPath:
    """A dangerous permission combination that creates an attack vector."""
    name: str
    description: str
    level: RiskLevel
    involved_permissions: list[PermissionCategory]
    attack_scenario: str

    @property
    def severity_tag(self) -> str:
        return f"[{self.level.label}]"


@dataclass
class ConvergenceSuggestion:
    """A recommendation to tighten a specific permission."""
    permission_category: PermissionCategory
    current_scope: PermissionScope
    recommended_scope: PermissionScope
    reason: str

    @property
    def action_label(self) -> str:
        if self.recommended_scope == PermissionScope.DISABLED:
            return "Disable"
        elif self.recommended_scope == PermissionScope.LIMITED:
            return "Restrict"
        return "Keep"


@dataclass
class ConsultantReport:
    """The full output of the Capability Boundary Consultant."""
    task_description: str
    task_intents: list[TaskCapability]
    required_permissions: list[Permission]
    current_permissions: list[Permission]
    excess_permissions: list[Permission]
    deviation_index: float
    risk_paths: list[RiskPath]
    suggestions: list[ConvergenceSuggestion]
    confidence: float = 1.0
    analysis_mode: str = "keyword"
    risk_relevance: dict = field(default_factory=dict)
    summary_note: str = ""
