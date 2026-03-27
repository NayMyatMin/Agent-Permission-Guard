"""Detects dangerous permission combinations and computes risk paths."""

from __future__ import annotations

from .models import (
    PermissionCategory,
    PermissionScope,
    RiskLevel,
    RiskPath,
)
from .permission_config import PermissionConfig


# Predefined risk path rules: each requires ALL listed categories to be active
_RISK_PATH_DEFINITIONS: list[dict] = [
    {
        "name": "Data Exfiltration",
        "description": "Local file content could be silently sent to external endpoints.",
        "level": RiskLevel.CRITICAL,
        "involved_permissions": [
            PermissionCategory.FILE_READ,
            PermissionCategory.NETWORK_OUTBOUND,
        ],
        "attack_scenario": (
            "The agent reads sensitive local files (credentials, personal data, source code) "
            "and transmits them to an external server via outbound network requests. "
            "This can happen through prompt injection or compromised skill behavior."
        ),
    },
    {
        "name": "Data Exfiltration via Skills",
        "description": "Local file content could be leaked through connected skills.",
        "level": RiskLevel.CRITICAL,
        "involved_permissions": [
            PermissionCategory.FILE_READ,
            PermissionCategory.SKILL_CONNECTIONS,
        ],
        "attack_scenario": (
            "The agent reads local files and passes their content to a connected skill "
            "(e.g., email, messaging, or cloud storage) which sends data externally. "
            "The user may not realize file contents are being transmitted."
        ),
    },
    {
        "name": "Remote Code Execution",
        "description": "Content fetched from the web could be executed as shell commands.",
        "level": RiskLevel.CRITICAL,
        "involved_permissions": [
            PermissionCategory.WEB_ACCESS,
            PermissionCategory.SHELL_EXECUTION,
        ],
        "attack_scenario": (
            "The agent fetches content from a website (which may contain prompt injection "
            "or malicious instructions) and then executes it as a shell command. "
            "This enables full system compromise from a single malicious webpage."
        ),
    },
    {
        "name": "Supply Chain Attack",
        "description": "Malicious packages could be downloaded, written to disk, and executed.",
        "level": RiskLevel.CRITICAL,
        "involved_permissions": [
            PermissionCategory.WEB_ACCESS,
            PermissionCategory.FILE_WRITE,
            PermissionCategory.SHELL_EXECUTION,
        ],
        "attack_scenario": (
            "The agent downloads a package or script from the internet, writes it to the "
            "local filesystem, and then executes it. A compromised or typosquatted package "
            "could install malware, backdoors, or exfiltrate data."
        ),
    },
    {
        "name": "Privacy Leak via Communication",
        "description": "Private file contents could be sent through messaging channels.",
        "level": RiskLevel.HIGH,
        "involved_permissions": [
            PermissionCategory.FILE_READ,
            PermissionCategory.SKILL_CONNECTIONS,
        ],
        "attack_scenario": (
            "The agent reads private documents and sends their content through a connected "
            "communication skill (email, Slack, etc.). This may happen if the agent "
            "misinterprets task scope or is manipulated via prompt injection."
        ),
    },
    {
        "name": "Local Filesystem Compromise",
        "description": "External content could be written to the local filesystem.",
        "level": RiskLevel.HIGH,
        "involved_permissions": [
            PermissionCategory.WEB_ACCESS,
            PermissionCategory.FILE_WRITE,
        ],
        "attack_scenario": (
            "The agent downloads files from the internet and writes them locally. "
            "Malicious files could overwrite configuration, inject code into projects, "
            "or place executable payloads on disk."
        ),
    },
    {
        "name": "Privilege Escalation",
        "description": "Shell access combined with system modification enables privilege escalation.",
        "level": RiskLevel.HIGH,
        "involved_permissions": [
            PermissionCategory.SHELL_EXECUTION,
            PermissionCategory.SYSTEM_MODIFICATION,
        ],
        "attack_scenario": (
            "The agent uses shell commands to modify system configuration, environment "
            "variables, startup scripts, or user permissions. This could escalate the "
            "agent's own privileges or create persistent backdoor access."
        ),
    },
    {
        "name": "Persistent Backdoor",
        "description": "File write and shell access together enable persistent malware installation.",
        "level": RiskLevel.MEDIUM,
        "involved_permissions": [
            PermissionCategory.FILE_WRITE,
            PermissionCategory.SHELL_EXECUTION,
        ],
        "attack_scenario": (
            "The agent writes a script or binary to disk and then executes it or "
            "registers it as a scheduled task/cron job. This creates a persistent "
            "foothold that survives the agent session."
        ),
    },
]


class RiskEngine:
    """Evaluates permission configurations for dangerous combinations."""

    def __init__(self) -> None:
        self._definitions = _RISK_PATH_DEFINITIONS

    def evaluate(
        self,
        config: PermissionConfig,
        required_categories: set[PermissionCategory] | None = None,
    ) -> list[RiskPath]:
        """Find all active risk paths in the given configuration.

        If required_categories is provided, only flag risk paths that involve
        at least one permission NOT in the required set (excess permissions).
        """
        active_categories = config.active_categories
        risk_paths: list[RiskPath] = []

        for defn in self._definitions:
            involved: list[PermissionCategory] = defn["involved_permissions"]

            # All involved permissions must be active
            if not all(cat in active_categories for cat in involved):
                continue

            # If we know what's required, only flag paths involving excess permissions
            if required_categories is not None:
                excess_in_path = [c for c in involved if c not in required_categories]
                if not excess_in_path:
                    continue

            risk_paths.append(RiskPath(
                name=defn["name"],
                description=defn["description"],
                level=defn["level"],
                involved_permissions=involved,
                attack_scenario=defn["attack_scenario"],
            ))

        # Sort by severity (critical first)
        risk_paths.sort(key=lambda rp: rp.level.weight, reverse=True)
        return risk_paths

    def compute_deviation_index(
        self,
        config: PermissionConfig,
        required_categories: set[PermissionCategory],
    ) -> float:
        """Compute deviation index: ratio of excess permission weight to total weight.

        Returns a float between 0.0 (perfectly aligned) and 1.0 (maximum over-authorization).
        """
        total_weight = 0
        excess_weight = 0

        for perm in config.active_permissions:
            weight = perm.risk_weight
            total_weight += weight
            if perm.category not in required_categories:
                excess_weight += weight
            elif perm.scope == PermissionScope.UNRESTRICTED:
                # Category is needed but scope is broader than necessary
                excess_weight += weight // 2

        if total_weight == 0:
            return 0.0
        return round(excess_weight / total_weight, 2)
