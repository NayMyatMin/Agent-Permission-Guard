"""Terminal display rendering for the Capability Boundary Consultant panel."""

from __future__ import annotations

import re
import sys

from .models import ConsultantReport, PermissionScope, RiskLevel

_ANSI_ESCAPE_RE = re.compile(r'\033\[[0-9;]*m')


# ANSI color codes
class _Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"


def _supports_color() -> bool:
    """Check if terminal supports ANSI colors."""
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


class ConsultantDisplay:
    """Renders the Capability Boundary Consultant panel to the terminal."""

    def __init__(self, use_color: bool | None = None) -> None:
        self._color = use_color if use_color is not None else _supports_color()

    def _c(self, code: str, text: str) -> str:
        """Apply color code if colors are enabled."""
        if self._color:
            return f"{code}{text}{_Colors.RESET}"
        return text

    def _risk_color(self, level: RiskLevel) -> str:
        if level == RiskLevel.CRITICAL:
            return _Colors.RED + _Colors.BOLD
        elif level == RiskLevel.HIGH:
            return _Colors.RED
        elif level == RiskLevel.MEDIUM:
            return _Colors.YELLOW
        return _Colors.DIM

    def _scope_color(self, scope: PermissionScope) -> str:
        if scope == PermissionScope.UNRESTRICTED:
            return _Colors.RED
        elif scope == PermissionScope.LIMITED:
            return _Colors.YELLOW
        return _Colors.GREEN

    def render(self, report: ConsultantReport) -> str:
        """Render the full consultant panel as a string."""
        width = 78
        lines: list[str] = []

        # Header
        lines.append(self._box_top(width))
        lines.append(self._box_center(
            self._c(_Colors.BOLD + _Colors.CYAN, "CAPABILITY BOUNDARY CONSULTANT"), width
        ))
        lines.append(self._box_separator(width))

        # Section 1: Task Intent
        lines.append(self._section_header("1. TASK INTENT ANALYSIS", width))
        lines.append(self._box_line(
            f"  Task: {self._c(_Colors.WHITE + _Colors.BOLD, report.task_description)}", width
        ))
        lines.append(self._box_line("", width))
        lines.append(self._box_line(
            f"  Detected intents:", width
        ))
        for intent in report.task_intents:
            label = intent.value.replace("_", " ").title()
            lines.append(self._box_line(
                f"    {self._c(_Colors.GREEN, '+')} {label}", width
            ))

        if report.confidence < 0.5:
            lines.append(self._box_line("", width))
            lines.append(self._box_line(
                f"  {self._c(_Colors.YELLOW + _Colors.BOLD, 'LOW CONFIDENCE')} "
                f"- No specific keywords matched. Using conservative fallback.",
                width,
            ))
            lines.append(self._box_line(
                f"  Deviation index dampened to reduce false positives.",
                width,
            ))

        lines.append(self._box_separator(width))

        # Section 2: Required Permissions (minimum set)
        lines.append(self._section_header("2. MINIMUM REQUIRED PERMISSIONS", width))
        for perm in report.required_permissions:
            scope_str = self._c(self._scope_color(perm.scope), perm.scope.value.upper())
            lines.append(self._box_line(
                f"  {self._c(_Colors.GREEN, '+')} {perm.category.value:<22} [{scope_str}]", width
            ))
            if perm.details:
                lines.append(self._box_line(
                    f"    {self._c(_Colors.DIM, perm.details)}", width
                ))

        lines.append(self._box_separator(width))

        # Section 3: Excess Permissions
        lines.append(self._section_header("3. EXCESS PERMISSIONS DETECTED", width))
        if report.excess_permissions:
            for perm in report.excess_permissions:
                scope_str = self._c(self._scope_color(perm.scope), perm.scope.value.upper())
                lines.append(self._box_line(
                    f"  {self._c(_Colors.RED, '!')} {perm.category.value:<22} [{scope_str}]", width
                ))
                display_reason = perm.excess_reason or perm.details
                if display_reason:
                    lines.append(self._box_line(
                        f"    {self._c(_Colors.DIM, display_reason)}", width
                    ))
        else:
            lines.append(self._box_line(
                f"  {self._c(_Colors.GREEN, 'None - permissions are well-aligned')}", width
            ))

        # Deviation index bar
        lines.append(self._box_line("", width))
        lines.append(self._box_line(
            f"  Deviation Index: {self._render_deviation_bar(report.deviation_index)}", width
        ))

        lines.append(self._box_separator(width))

        # Section 4: Risk Roadmap
        lines.append(self._section_header("4. RISK ROADMAP", width))
        if report.risk_paths:
            for i, rp in enumerate(report.risk_paths):
                color = self._risk_color(rp.level)
                tag = self._c(color, f"[{rp.level.value.upper()}]")
                lines.append(self._box_line(
                    f"  {tag} {self._c(_Colors.BOLD, rp.name)}", width
                ))
                lines.append(self._box_line(
                    f"    {rp.description}", width
                ))
                # Show involved permissions
                involved = ", ".join(c.value for c in rp.involved_permissions)
                lines.append(self._box_line(
                    f"    Requires: {self._c(_Colors.DIM, involved)}", width
                ))
                # Attack scenario
                lines.append(self._box_line(
                    f"    Scenario: {self._c(_Colors.DIM, rp.attack_scenario[:100])}",
                    width,
                ))
                if len(rp.attack_scenario) > 100:
                    lines.append(self._box_line(
                        f"      {self._c(_Colors.DIM, rp.attack_scenario[100:])}",
                        width,
                    ))
                if i < len(report.risk_paths) - 1:
                    lines.append(self._box_line("", width))
        else:
            lines.append(self._box_line(
                f"  {self._c(_Colors.GREEN, 'No risk paths detected with current permissions.')}", width
            ))

        lines.append(self._box_separator(width))

        # Section 5: Convergence Suggestions
        lines.append(self._section_header("5. CONVERGENCE SUGGESTIONS", width))
        if report.suggestions:
            for i, sug in enumerate(report.suggestions, 1):
                action = sug.action_label
                if action == "Disable":
                    action_str = self._c(_Colors.RED + _Colors.BOLD, "DISABLE")
                else:
                    action_str = self._c(_Colors.YELLOW + _Colors.BOLD, "RESTRICT")

                current_str = self._c(
                    self._scope_color(sug.current_scope),
                    sug.current_scope.value.upper()
                )
                recommended_str = self._c(
                    self._scope_color(sug.recommended_scope),
                    sug.recommended_scope.value.upper()
                )

                lines.append(self._box_line(
                    f"  {i}. [{action_str}] {sug.permission_category.value}",
                    width,
                ))
                lines.append(self._box_line(
                    f"     {current_str} -> {recommended_str}",
                    width,
                ))
                lines.append(self._box_line(
                    f"     {self._c(_Colors.DIM, sug.reason)}", width
                ))
                if i < len(report.suggestions):
                    lines.append(self._box_line("", width))
        else:
            lines.append(self._box_line(
                f"  {self._c(_Colors.GREEN, 'No changes recommended.')}", width
            ))

        lines.append(self._box_separator(width))

        # Summary note
        if report.summary_note:
            lines.append(self._box_line("", width))
            lines.append(self._box_line(
                f"  {self._c(_Colors.CYAN + _Colors.BOLD, 'Note:')} {report.summary_note}",
                width,
            ))
            lines.append(self._box_line("", width))

        # Footer
        lines.append(self._box_bottom(width))

        return "\n".join(lines)

    def render_user_choice(self) -> str:
        """Render the user choice prompt."""
        lines = [
            "",
            self._c(_Colors.BOLD, "Select an option:"),
            f"  {self._c(_Colors.GREEN, '[A]')} Accept all suggestions",
            f"  {self._c(_Colors.YELLOW, '[P]')} Partially accept (select which to apply)",
            f"  {self._c(_Colors.RED, '[K]')} Keep current configuration and continue",
            "",
        ]
        return "\n".join(lines)

    def _render_deviation_bar(self, index: float) -> str:
        """Render a visual deviation index bar."""
        bar_width = 30
        filled = int(index * bar_width)
        empty = bar_width - filled

        if index <= 0.3:
            color = _Colors.GREEN
            label = "LOW"
        elif index <= 0.6:
            color = _Colors.YELLOW
            label = "MODERATE"
        elif index <= 0.8:
            color = _Colors.RED
            label = "HIGH"
        else:
            color = _Colors.RED + _Colors.BOLD
            label = "CRITICAL"

        bar = self._c(color, "█" * filled) + self._c(_Colors.DIM, "░" * empty)
        pct = self._c(color, f"{index:.0%}")
        label_str = self._c(color, label)

        return f"[{bar}] {pct} ({label_str})"

    @staticmethod
    def _visible_len(text: str) -> int:
        """Return the visible length of text, ignoring ANSI escape codes."""
        return len(_ANSI_ESCAPE_RE.sub('', text))

    def _box_top(self, width: int) -> str:
        return "┌" + "─" * width + "┐"

    def _box_bottom(self, width: int) -> str:
        return "└" + "─" * width + "┘"

    def _box_separator(self, width: int) -> str:
        return "├" + "─" * width + "┤"

    def _box_line(self, content: str, width: int) -> str:
        """Create a box line with right border, padding to width."""
        # Inner area is width chars: leading space + content + padding + trailing border
        # "│" + " " + content + padding + "│" => visible width = width + 2
        visible = self._visible_len(content)
        inner = width - 1  # space for content after leading " "
        padding = max(0, inner - visible)
        return f"│ {content}{' ' * padding}│"

    def _box_center(self, content: str, width: int) -> str:
        return self._box_line(content, width)

    def _section_header(self, title: str, width: int) -> str:
        return self._box_line(
            self._c(_Colors.BOLD + _Colors.MAGENTA, title), width
        )
