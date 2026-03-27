"""Capability Boundary Consultant - generates the full analysis report."""

from __future__ import annotations

from .models import (
    ConsultantReport,
    ConvergenceSuggestion,
    Permission,
    PermissionCategory,
    PermissionScope,
)
from .permission_config import PermissionConfig
from .risk_engine import RiskEngine
from .task_analyzer import TaskAnalyzer, TaskAnalysisResult


class Consultant:
    """Orchestrates task analysis, risk evaluation, and suggestion generation."""

    def __init__(self) -> None:
        self._task_analyzer = TaskAnalyzer()
        self._risk_engine = RiskEngine()

    def analyze(self, task_description: str, config: PermissionConfig) -> ConsultantReport:
        """Run full analysis: task intent -> permission comparison -> risk paths -> suggestions."""
        # Step 1: Analyze task intent
        analysis = self._task_analyzer.analyze(task_description)

        # Step 2: Identify excess permissions
        excess = self._find_excess_permissions(config, analysis)

        # Step 3: Evaluate risk paths (only for excess permissions)
        risk_paths = self._risk_engine.evaluate(config, analysis.required_categories)

        # Step 4: Compute deviation index
        deviation_index = self._risk_engine.compute_deviation_index(
            config, analysis.required_categories
        )

        # Step 5: Generate convergence suggestions
        suggestions = self._generate_suggestions(config, analysis, excess)

        # Step 6: Create summary note
        summary_note = self._generate_summary_note(analysis, excess, risk_paths)

        return ConsultantReport(
            task_description=task_description,
            task_intents=analysis.intents,
            required_permissions=analysis.required_permissions,
            current_permissions=config.active_permissions,
            excess_permissions=excess,
            deviation_index=deviation_index,
            risk_paths=risk_paths,
            suggestions=suggestions,
            summary_note=summary_note,
        )

    def _find_excess_permissions(
        self,
        config: PermissionConfig,
        analysis: TaskAnalysisResult,
    ) -> list[Permission]:
        """Find permissions that are active but not required for the task."""
        required_categories = analysis.required_categories
        excess: list[Permission] = []

        for perm in config.active_permissions:
            if perm.category not in required_categories:
                excess.append(perm)
            else:
                # Category is required but scope may be too broad
                required_perm = next(
                    (rp for rp in analysis.required_permissions if rp.category == perm.category),
                    None,
                )
                if (
                    required_perm
                    and perm.scope == PermissionScope.UNRESTRICTED
                    and required_perm.scope == PermissionScope.LIMITED
                ):
                    excess.append(Permission(
                        perm.category,
                        perm.scope,
                        f"Scope is UNRESTRICTED but task only needs LIMITED: {required_perm.details}",
                    ))

        return excess

    def _generate_suggestions(
        self,
        config: PermissionConfig,
        analysis: TaskAnalysisResult,
        excess: list[Permission],
    ) -> list[ConvergenceSuggestion]:
        """Generate convergence suggestions for each excess permission."""
        suggestions: list[ConvergenceSuggestion] = []
        seen_categories: set[PermissionCategory] = set()

        for perm in excess:
            if perm.category in seen_categories:
                continue
            seen_categories.add(perm.category)

            if perm.category in analysis.required_categories:
                # Scope reduction: UNRESTRICTED -> LIMITED
                required_perm = next(
                    (rp for rp in analysis.required_permissions if rp.category == perm.category),
                    None,
                )
                suggestions.append(ConvergenceSuggestion(
                    permission_category=perm.category,
                    current_scope=PermissionScope.UNRESTRICTED,
                    recommended_scope=PermissionScope.LIMITED,
                    reason=(
                        f"Task requires {perm.category.value} but only with limited scope. "
                        f"{required_perm.details if required_perm else ''}"
                    ),
                ))
            else:
                # Full disable: not needed for task
                suggestions.append(ConvergenceSuggestion(
                    permission_category=perm.category,
                    current_scope=perm.scope,
                    recommended_scope=PermissionScope.DISABLED,
                    reason=f"Not required for task: {', '.join(analysis.intent_labels)}",
                ))

        # Sort: disables first, then restricts
        suggestions.sort(
            key=lambda s: (0 if s.recommended_scope == PermissionScope.DISABLED else 1)
        )
        return suggestions

    def _generate_summary_note(
        self,
        analysis: TaskAnalysisResult,
        excess: list[Permission],
        risk_paths: list,
    ) -> str:
        """Generate a human-readable summary note."""
        if not excess and not risk_paths:
            return (
                "Current permissions are well-aligned with the task. "
                "No excess permissions or risk paths detected."
            )

        intent_str = ", ".join(analysis.intent_labels)
        parts = [
            f"The above changes preserve the primary capability of \"{intent_str}\" "
            f"while significantly reducing risks both externally and locally."
        ]

        if risk_paths:
            critical_count = sum(1 for rp in risk_paths if rp.level.value == "critical")
            high_count = sum(1 for rp in risk_paths if rp.level.value == "high")
            if critical_count:
                parts.append(f"Addresses {critical_count} CRITICAL risk path(s).")
            if high_count:
                parts.append(f"Addresses {high_count} HIGH risk path(s).")

        return " ".join(parts)
