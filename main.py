#!/usr/bin/env python3
"""Agent Permission Guard - Interactive Demo.

Demonstrates the Capability Boundary Consultant that analyzes task intent,
detects permission over-authorization, and provides convergence suggestions.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from src.consultant import Consultant
from src.display import ConsultantDisplay
from src.permission_config import PermissionConfig


CONFIG_DIR = Path(__file__).parent / "configs"

EXAMPLE_TASKS = [
    "Help me search online for information on competitors and summarize it.",
    "Run the test suite and fix any failing tests.",
    "Send an email to the team with the weekly status update.",
    "Download the dataset from the URL and process it locally.",
    "Configure the CI/CD pipeline and update deployment settings.",
    "Read the project files and create a summary document.",
]


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


def run_demo():
    """Main demo loop."""
    profiles = load_config_profiles()
    if not profiles:
        print("Error: No configuration profiles found in configs/ directory.")
        sys.exit(1)

    consultant = Consultant()
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
            print("\n  Permissions are well-aligned. Proceeding with task.\n")

        # Continue or exit
        print("─" * 60)
        try:
            again = input("\nAnalyze another task? [Y/n]: ").strip().lower()
            if again in ("n", "no"):
                break
        except (EOFError, KeyboardInterrupt):
            break

    print("\nDone. Thank you for using Agent Permission Guard.\n")


def run_non_interactive(task: str, config_path: str):
    """Non-interactive mode for scripting/testing."""
    config = PermissionConfig.from_json_file(config_path)
    consultant = Consultant()
    display = ConsultantDisplay()

    report = consultant.analyze(task, config)
    print(display.render(report))
    print(display.render_user_choice())

    # Print machine-readable summary
    print("\n--- SUMMARY ---")
    print(f"Task: {report.task_description}")
    print(f"Intents: {', '.join(i.value for i in report.task_intents)}")
    print(f"Deviation Index: {report.deviation_index:.0%}")
    print(f"Risk Paths: {len(report.risk_paths)}")
    print(f"Suggestions: {len(report.suggestions)}")
    for sug in report.suggestions:
        print(f"  - {sug.action_label} {sug.permission_category.value}: "
              f"{sug.current_scope.value} -> {sug.recommended_scope.value}")


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        # Non-interactive: python main.py <config_file> <task_description>
        config_path = sys.argv[1]
        task_description = " ".join(sys.argv[2:])
        run_non_interactive(task_description, config_path)
    elif len(sys.argv) == 2 and sys.argv[1] in ("--help", "-h"):
        print("Usage:")
        print("  python main.py                           # Interactive demo")
        print("  python main.py <config.json> <task>      # Non-interactive")
        print()
        print("Examples:")
        print('  python main.py configs/overpermissioned.json "Search for competitor info"')
    else:
        run_demo()
