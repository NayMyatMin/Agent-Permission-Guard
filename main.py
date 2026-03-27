#!/usr/bin/env python3
"""Agent Permission Guard - Interactive Demo.

Demonstrates the Capability Boundary Consultant that analyzes task intent,
detects permission over-authorization, and provides convergence suggestions.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.consultant import Consultant
from src.display import ConsultantDisplay
from src.models import ConsultantReport
from src.permission_config import PermissionConfig


CONFIG_DIR = Path(__file__).parent / "configs"
HISTORY_FILE = Path(__file__).parent / "session_history.jsonl"

EXAMPLE_TASKS = [
    "Help me search online for information on competitors and summarize it.",
    "Run the test suite and fix any failing tests.",
    "Send an email to the team with the weekly status update.",
    "Download the dataset from the URL and process it locally.",
    "Configure the CI/CD pipeline and update deployment settings.",
    "Read the project files and create a summary document.",
]


def report_to_dict(report: ConsultantReport) -> dict:
    """Serialize a ConsultantReport to a JSON-safe dictionary."""
    return {
        "task_description": report.task_description,
        "analysis_mode": report.analysis_mode,
        "confidence": report.confidence,
        "task_intents": [i.value for i in report.task_intents],
        "deviation_index": report.deviation_index,
        "required_permissions": [
            {
                "category": p.category.value,
                "scope": p.scope.value,
                "details": p.details,
            }
            for p in report.required_permissions
        ],
        "excess_permissions": [
            {
                "category": p.category.value,
                "scope": p.scope.value,
                "details": p.details,
                "excess_reason": p.excess_reason,
            }
            for p in report.excess_permissions
        ],
        "risk_paths": [
            {
                "name": rp.name,
                "level": rp.level.value,
                "description": rp.description,
                "involved_permissions": [c.value for c in rp.involved_permissions],
                "attack_scenario": rp.attack_scenario,
            }
            for rp in report.risk_paths
        ],
        "suggestions": [
            {
                "action": s.action_label,
                "permission": s.permission_category.value,
                "current_scope": s.current_scope.value,
                "recommended_scope": s.recommended_scope.value,
                "reason": s.reason,
            }
            for s in report.suggestions
        ],
        "risk_relevance": report.risk_relevance,
        "summary_note": report.summary_note,
    }


def log_session_history(report: ConsultantReport, user_choice: str, profile_name: str):
    """Append analysis result to session history for drift tracking."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "profile": profile_name,
        "task": report.task_description,
        "confidence": report.confidence,
        "deviation_index": report.deviation_index,
        "risk_path_count": len(report.risk_paths),
        "critical_risks": sum(1 for rp in report.risk_paths if rp.level.value == "critical"),
        "suggestion_count": len(report.suggestions),
        "user_choice": user_choice,
        "excess_categories": [p.category.value for p in report.excess_permissions],
    }
    with open(HISTORY_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")


def print_drift_summary():
    """Print a summary of permission drift from session history."""
    if not HISTORY_FILE.exists():
        return

    entries = []
    with open(HISTORY_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    if len(entries) < 2:
        return

    dismissed = sum(1 for e in entries if e["user_choice"] == "keep")
    total = len(entries)
    avg_deviation = sum(e["deviation_index"] for e in entries) / total
    total_risks = sum(e["risk_path_count"] for e in entries)

    print(f"\n  SESSION DRIFT SUMMARY ({total} analyses)")
    print(f"  ─────────────────────────────────────")
    print(f"  Suggestions dismissed: {dismissed}/{total} ({dismissed/total:.0%})")
    print(f"  Average deviation index: {avg_deviation:.0%}")
    print(f"  Total risk paths flagged: {total_risks}")
    if dismissed > total / 2:
        print(f"  Warning: Majority of suggestions dismissed — permission surface unchanged.")
    print()


def load_config_profiles() -> dict[str, Path]:
    """Discover available configuration profiles."""
    profiles: dict[str, Path] = {}
    if CONFIG_DIR.exists():
        for f in sorted(CONFIG_DIR.glob("*.json")):
            profiles[f.stem] = f
    return profiles


def select_profile(profiles: dict[str, Path]) -> PermissionConfig:
    """Let the user select a permission profile."""
    print("\n┌─────────────────────────────────────────────────┐")
    print("│  AGENT PERMISSION GUARD - Configuration Select  │")
    print("└─────────────────────────────────────────────────┘\n")
    print("Available permission profiles:\n")

    profile_list = list(profiles.items())
    for i, (name, path) in enumerate(profile_list, 1):
        config = PermissionConfig.from_json_file(path)
        active_count = len(config.active_permissions)
        total_count = len(config.permissions)
        print(f"  [{i}] {config.profile_name}")
        print(f"      Active permissions: {active_count}/{total_count}")
        print(f"      File: {path.name}")
        print()

    while True:
        try:
            choice = input("Select a profile [1]: ").strip()
            if not choice:
                choice = "1"
            idx = int(choice) - 1
            if 0 <= idx < len(profile_list):
                name, path = profile_list[idx]
                config = PermissionConfig.from_json_file(path)
                print(f"\n  Loaded: {config.profile_name}\n")
                return config
            print(f"  Please enter a number between 1 and {len(profile_list)}")
        except ValueError:
            print("  Please enter a valid number.")
        except (EOFError, KeyboardInterrupt):
            print("\n\nExiting.")
            sys.exit(0)


def get_task_description() -> str:
    """Get task description from user, with example suggestions."""
    print("─" * 60)
    print("\nExample tasks:")
    for i, task in enumerate(EXAMPLE_TASKS, 1):
        print(f"  [{i}] {task}")

    print(f"\nEnter a task description (or pick 1-{len(EXAMPLE_TASKS)}):")

    while True:
        try:
            task_input = input("\n  > ").strip()
            if not task_input:
                continue

            # Check if user picked an example number
            try:
                idx = int(task_input) - 1
                if 0 <= idx < len(EXAMPLE_TASKS):
                    task = EXAMPLE_TASKS[idx]
                    print(f"  Selected: {task}")
                    return task
            except ValueError:
                pass

            return task_input
        except (EOFError, KeyboardInterrupt):
            print("\n\nExiting.")
            sys.exit(0)


def handle_user_choice(report) -> str:
    """Handle the user's response to suggestions."""
    display = ConsultantDisplay()
    print(display.render_user_choice())

    while True:
        try:
            choice = input("  Your choice [A/P/K]: ").strip().upper()
            if choice in ("A", "P", "K"):
                return choice
            if not choice:
                continue
            print("  Please enter A, P, or K.")
        except (EOFError, KeyboardInterrupt):
            print("\n\nExiting.")
            sys.exit(0)


def handle_partial_accept(report) -> list[int]:
    """Let user select which suggestions to apply."""
    print("\nSelect suggestions to apply (comma-separated numbers):\n")
    for i, sug in enumerate(report.suggestions, 1):
        action = sug.action_label
        print(f"  [{i}] {action} {sug.permission_category.value}")
        print(f"      {sug.current_scope.value} -> {sug.recommended_scope.value}")
        print(f"      {sug.reason}\n")

    while True:
        try:
            selections = input("  Apply which? (e.g., 1,3,4): ").strip()
            if not selections:
                continue
            indices = []
            for part in selections.split(","):
                idx = int(part.strip())
                if 1 <= idx <= len(report.suggestions):
                    indices.append(idx)
            if indices:
                return indices
            print(f"  Enter numbers between 1 and {len(report.suggestions)}")
        except ValueError:
            print("  Please enter valid numbers separated by commas.")
        except (EOFError, KeyboardInterrupt):
            print("\n\nExiting.")
            sys.exit(0)


def apply_suggestions(config: PermissionConfig, report, indices: list[int] | None = None):
    """Show what the resulting configuration would look like."""
    print("\n" + "─" * 60)
    print("\n  RESULTING CONFIGURATION:\n")

    applied_categories = set()
    if indices is None:
        # Apply all
        for sug in report.suggestions:
            applied_categories.add(sug.permission_category)
    else:
        for idx in indices:
            sug = report.suggestions[idx - 1]
            applied_categories.add(sug.permission_category)

    sug_map = {sug.permission_category: sug for sug in report.suggestions}

    for perm in config.permissions:
        if perm.category in applied_categories and perm.category in sug_map:
            sug = sug_map[perm.category]
            scope_str = sug.recommended_scope.value.upper()
            status = "CHANGED"
        else:
            scope_str = perm.scope.value.upper()
            status = "unchanged"

        marker = "*" if status == "CHANGED" else " "
        print(f"  {marker} {perm.category.value:<24} [{scope_str:<12}] {status}")

    print()
    changed_count = len(applied_categories)
    total = len(config.permissions)
    print(f"  {changed_count} of {total} permissions modified.")
    print()


def run_demo(use_llm: bool = True):
    """Main demo loop."""
    profiles = load_config_profiles()
    if not profiles:
        print("Error: No configuration profiles found in configs/ directory.")
        sys.exit(1)

    consultant = Consultant(use_llm=use_llm)
    display = ConsultantDisplay()

    print("\n" + "=" * 60)
    print("  AGENT PERMISSION GUARD")
    print("  Capability Boundary Consultant Demo")
    print("=" * 60)

    config = select_profile(profiles)

    while True:
        # Get task description
        task = get_task_description()

        # Run analysis
        print("\n  Analyzing task and permissions...\n")
        report = consultant.analyze(task, config)

        # Display consultant panel
        print(display.render(report))

        # User choice
        if report.suggestions:
            choice = handle_user_choice(report)
            choice_label = {"A": "accept_all", "P": "partial", "K": "keep"}[choice]

            if choice == "A":
                print("\n  All suggestions accepted.")
                apply_suggestions(config, report)
            elif choice == "P":
                indices = handle_partial_accept(report)
                print(f"\n  Applied {len(indices)} suggestion(s).")
                apply_suggestions(config, report, indices)
            else:
                print("\n  Keeping current configuration. Proceeding with task.")
                print("  (No permissions were modified)\n")
        else:
            choice_label = "aligned"
            print("\n  Permissions are well-aligned. Proceeding with task.\n")

        # Log to session history
        log_session_history(report, choice_label, config.profile_name)

        # Continue or exit
        print("─" * 60)
        try:
            again = input("\nAnalyze another task? [Y/n]: ").strip().lower()
            if again in ("n", "no"):
                break
        except (EOFError, KeyboardInterrupt):
            break

    # Show drift summary at end of session
    print_drift_summary()
    print("Done. Thank you for using Agent Permission Guard.\n")


def run_non_interactive(task: str, config_path: str, json_output: bool = False, use_llm: bool = True):
    """Non-interactive mode for scripting/testing."""
    config = PermissionConfig.from_json_file(config_path)
    consultant = Consultant(use_llm=use_llm)

    report = consultant.analyze(task, config)

    if json_output:
        print(json.dumps(report_to_dict(report), indent=2))
        return

    display = ConsultantDisplay()
    print(display.render(report))
    print(display.render_user_choice())

    # Print machine-readable summary
    print("\n--- SUMMARY ---")
    print(f"Task: {report.task_description}")
    print(f"Analysis Mode: {report.analysis_mode}")
    print(f"Confidence: {report.confidence:.0%}")
    print(f"Intents: {', '.join(i.value for i in report.task_intents)}")
    print(f"Deviation Index: {report.deviation_index:.0%}")
    print(f"Risk Paths: {len(report.risk_paths)}")
    print(f"Suggestions: {len(report.suggestions)}")
    for sug in report.suggestions:
        print(f"  - {sug.action_label} {sug.permission_category.value}: "
              f"{sug.current_scope.value} -> {sug.recommended_scope.value}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}

    use_llm = "--no-llm" not in flags

    if "--help" in flags or "-h" in {sys.argv[1]} if len(sys.argv) > 1 else set():
        print("Usage:")
        print("  python main.py                                  # Interactive demo (LLM default)")
        print("  python main.py --no-llm                         # Interactive, keyword-only")
        print("  python main.py <config.json> <task>             # Non-interactive")
        print("  python main.py --json <config.json> <task>      # JSON output")
        print("  python main.py --no-llm <config.json> <task>    # Keyword-only, non-interactive")
        print("  python main.py --history                        # Show session drift summary")
        print()
        print("Flags:")
        print("  --no-llm    Use keyword matching instead of LLM (no API key needed)")
        print("  --json      Output analysis as JSON (non-interactive mode)")
        print("  --history   Show session drift summary and exit")
        print()
        print("Examples:")
        print('  python main.py configs/overpermissioned.json "Search for competitor info"')
        print('  python main.py --json configs/overpermissioned.json "Search for competitor info"')
    elif "--history" in flags:
        print_drift_summary()
    elif len(args) >= 2:
        config_path = args[0]
        task_description = " ".join(args[1:])
        run_non_interactive(task_description, config_path, json_output="--json" in flags, use_llm=use_llm)
    else:
        run_demo(use_llm=use_llm)
