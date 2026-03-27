# Agent Permission Guard

A Capability Boundary Consultant that detects permission over-authorization in AI agent configurations and provides actionable convergence suggestions.

## Problem

As users interact with AI agents daily, they gradually grant more permissions. This creates dangerous permission combinations that allow agents to autonomously execute high-risk actions:

- **Data exfiltration**: file read + outbound network = silent data theft
- **Remote code execution**: web access + shell execution = full system compromise
- **Supply chain attacks**: web + file write + shell = malicious package installation

Studies show that over 40% of experienced users enable full auto-approval, yet most users don't recognize risks beyond payments (e.g., auto-downloading files, modifying settings, sending messages externally).

## Solution

Agent Permission Guard sits between task initiation and execution. For each task, it:

1. **Analyzes task intent** - Extracts what capabilities the task actually needs
2. **Compares against current permissions** - Identifies excess permissions not needed for the task
3. **Detects risk paths** - Finds dangerous permission combinations from excess authorizations
4. **Provides convergence suggestions** - Recommends the minimum permission set for the task
5. **Lets the user decide** - Accept all, partial, or keep current (non-blocking)

## Quick Start

```bash
# No dependencies required - Python 3.10+ only
python main.py
```

### Interactive Mode

```bash
python main.py
```

Walks through profile selection, task input, consultant panel display, and user choice.

### Non-Interactive Mode

```bash
python main.py configs/overpermissioned.json "Help me search online for information on competitors and summarize it"
```

### Run Tests

```bash
python -m pytest tests/ -v
```

## Architecture

```
├── main.py                      # Interactive CLI demo
├── src/
│   ├── models.py                # Core data models (enums, dataclasses)
│   ├── task_analyzer.py         # Task description → required capabilities
│   ├── permission_config.py     # Permission profile loading & representation
│   ├── risk_engine.py           # Risk path detection from permission combos
│   ├── consultant.py            # Deviation index + convergence suggestions
│   └── display.py               # Terminal panel rendering (ANSI colors)
├── configs/
│   ├── overpermissioned.json    # Typical over-authorized config (demo default)
│   ├── developer.json           # Moderate developer workflow config
│   └── minimal_research.json   # Minimal config for research tasks
└── tests/
    ├── test_task_analyzer.py
    ├── test_risk_engine.py
    └── test_consultant.py
```

## Risk Paths Detected

| Risk Path | Permission Combination | Severity |
|---|---|---|
| Data Exfiltration | file_read + network_outbound | CRITICAL |
| Data Exfiltration via Skills | file_read + skill_connections | CRITICAL |
| Remote Code Execution | web_access + shell_execution | CRITICAL |
| Supply Chain Attack | web_access + file_write + shell_execution | CRITICAL |
| Privacy Leak | file_read + skill_connections | HIGH |
| Local Filesystem Compromise | web_access + file_write | HIGH |
| Privilege Escalation | shell_execution + system_modification | HIGH |
| Persistent Backdoor | file_write + shell_execution | MEDIUM |

## Example Output

For the task "Help me search online for information on competitors and summarize it" with an over-permissioned configuration:

- **Detected intents**: Information Gathering, Content Creation
- **Deviation Index**: 75% (HIGH)
- **Risk paths found**: 6 (3 CRITICAL, 2 HIGH, 1 MEDIUM)
- **Suggestions**: Disable shell, skills, system modification; Restrict web, file I/O, and network to limited scope

## Design Principles

- **Non-blocking**: Suggestions are advisory. Users can always proceed with current config.
- **Task-aware**: Only flags excess permissions relative to the current task, not globally.
- **Weighted risk**: Deviation index accounts for permission severity, not just count.
- **Zero dependencies**: Pure Python standard library. No external packages required.
