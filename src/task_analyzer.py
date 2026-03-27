"""Analyzes task descriptions to extract intent and minimum required permissions."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Permission, PermissionCategory, PermissionScope, TaskCapability


@dataclass
class _IntentRule:
    """Maps keywords to a task capability and its minimum permissions."""
    capability: TaskCapability
    keywords: list[str]
    required_permissions: list[Permission]


# Keyword-to-intent mapping with minimum permission sets
_INTENT_RULES: list[_IntentRule] = [
    _IntentRule(
        capability=TaskCapability.INFORMATION_GATHERING,
        keywords=[
            "search", "research", "find information", "look up", "lookup",
            "browse", "investigate", "explore online", "check online",
            "gather information", "collect information", "web search",
        ],
        required_permissions=[
            Permission(PermissionCategory.WEB_ACCESS, PermissionScope.LIMITED,
                       "Read-only access to web search and public pages"),
            Permission(PermissionCategory.NETWORK_OUTBOUND, PermissionScope.LIMITED,
                       "HTTPS GET requests to search engines and public sites"),
        ],
    ),
    _IntentRule(
        capability=TaskCapability.CONTENT_CREATION,
        keywords=[
            "summarize", "write", "draft", "create document", "compose",
            "generate report", "create summary", "produce", "author",
            "compile notes", "write up", "document",
        ],
        required_permissions=[
            Permission(PermissionCategory.FILE_WRITE, PermissionScope.LIMITED,
                       "Write to designated output directory only"),
            Permission(PermissionCategory.FILE_READ, PermissionScope.LIMITED,
                       "Read source materials in current directory"),
        ],
    ),
    _IntentRule(
        capability=TaskCapability.CODE_EXECUTION,
        keywords=[
            "run", "execute", "build", "compile", "test", "deploy",
            "start server", "run script", "launch", "invoke",
        ],
        required_permissions=[
            Permission(PermissionCategory.SHELL_EXECUTION, PermissionScope.LIMITED,
                       "Execute approved commands in project directory"),
            Permission(PermissionCategory.FILE_READ, PermissionScope.LIMITED,
                       "Read project source files"),
        ],
    ),
    _IntentRule(
        capability=TaskCapability.FILE_MANAGEMENT,
        keywords=[
            "download", "save", "copy files", "move files", "organize",
            "upload", "transfer", "backup", "archive", "extract",
        ],
        required_permissions=[
            Permission(PermissionCategory.FILE_READ, PermissionScope.LIMITED,
                       "Read files in specified directories"),
            Permission(PermissionCategory.FILE_WRITE, PermissionScope.LIMITED,
                       "Write files to specified directories"),
        ],
    ),
    _IntentRule(
        capability=TaskCapability.COMMUNICATION,
        keywords=[
            "send email", "send message", "notify", "post", "share",
            "email", "message", "slack", "communicate", "alert",
            "broadcast", "publish",
        ],
        required_permissions=[
            Permission(PermissionCategory.SKILL_CONNECTIONS, PermissionScope.LIMITED,
                       "Access to specific messaging/email skills only"),
            Permission(PermissionCategory.NETWORK_OUTBOUND, PermissionScope.LIMITED,
                       "Outbound to approved messaging endpoints"),
        ],
    ),
    _IntentRule(
        capability=TaskCapability.SYSTEM_MODIFICATION,
        keywords=[
            "configure", "install", "update settings", "modify config",
            "change settings", "set up", "setup", "reconfigure",
            "update system", "modify permissions",
        ],
        required_permissions=[
            Permission(PermissionCategory.SYSTEM_MODIFICATION, PermissionScope.LIMITED,
                       "Modify specific application settings only"),
            Permission(PermissionCategory.FILE_WRITE, PermissionScope.LIMITED,
                       "Write to configuration files only"),
        ],
    ),
]


class TaskAnalyzer:
    """Extracts task intent and minimum required permissions from a description."""

    def __init__(self) -> None:
        self._rules = _INTENT_RULES

    def analyze(self, task_description: str) -> TaskAnalysisResult:
        """Analyze a task description and return detected intents and permissions."""
        description_lower = task_description.lower()
        matched_capabilities: list[TaskCapability] = []
        required_permissions: dict[PermissionCategory, Permission] = {}

        for rule in self._rules:
            if self._matches_keywords(description_lower, rule.keywords):
                if rule.capability not in matched_capabilities:
                    matched_capabilities.append(rule.capability)
                for perm in rule.required_permissions:
                    existing = required_permissions.get(perm.category)
                    if existing is None or _scope_priority(perm.scope) > _scope_priority(existing.scope):
                        required_permissions[perm.category] = perm

        if not matched_capabilities:
            matched_capabilities.append(TaskCapability.INFORMATION_GATHERING)
            required_permissions[PermissionCategory.FILE_READ] = Permission(
                PermissionCategory.FILE_READ, PermissionScope.LIMITED,
                "Read-only access to current directory"
            )

        return TaskAnalysisResult(
            task_description=task_description,
            intents=matched_capabilities,
            required_permissions=list(required_permissions.values()),
        )

    def _matches_keywords(self, text: str, keywords: list[str]) -> bool:
        """Check if any keyword appears in the text."""
        for keyword in keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text):
                return True
        return False


@dataclass
class TaskAnalysisResult:
    """Result of analyzing a task description."""
    task_description: str
    intents: list[TaskCapability]
    required_permissions: list[Permission]

    @property
    def intent_labels(self) -> list[str]:
        return [intent.value.replace("_", " ").title() for intent in self.intents]

    @property
    def required_categories(self) -> set[PermissionCategory]:
        return {p.category for p in self.required_permissions}


def _scope_priority(scope: PermissionScope) -> int:
    """Higher number = broader scope."""
    return {
        PermissionScope.DISABLED: 0,
        PermissionScope.LIMITED: 1,
        PermissionScope.UNRESTRICTED: 2,
    }[scope]
