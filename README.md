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

1. **Analyzes task intent** - LLM (gpt-5-mini) extracts what capabilities the task actually needs
2. **Compares against current permissions** - Identifies excess permissions not needed for the task
3. **Detects risk paths** - Finds dangerous permission combinations from excess authorizations
4. **Scores risk relevance** - LLM rates how plausible each risk path is for the specific task
5. **Provides convergence suggestions** - Recommends the minimum permission set for the task
6. **Lets the user decide** - Accept all, partial, or keep current (non-blocking)

## Quick Start

```bash
pip install openai
export OPENAI_API_KEY="sk-your-key-here"
python main.py
```

### Interactive Mode

```bash
python main.py              # LLM-powered (default)
python main.py --no-llm     # Keyword-only (no API key needed)
```

### Non-Interactive Mode

```bash
python main.py configs/overpermissioned.json "Help me search online for information on competitors and summarize it"
```

### JSON Output

```bash
python main.py --json configs/overpermissioned.json "Search for competitor info"
```

### Session Drift Summary

```bash
python main.py --history
```

### Run Tests

```bash
python -m pytest tests/ -v
```

## Architecture

```
├── main.py                      # CLI entry point (interactive + non-interactive + JSON)
├── requirements.txt             # openai>=1.0.0
├── src/
│   ├── models.py                # Core data models (enums, dataclasses)
│   ├── task_analyzer.py         # Keyword-based intent extraction (deterministic fallback)
│   ├── llm_analyzer.py          # LLM-backed intent extraction + risk relevance (gpt-5-mini)
│   ├── permission_config.py     # Permission profile loading with validation
│   ├── risk_engine.py           # Risk path detection from permission combos
│   ├── consultant.py            # Orchestrator: deviation index + convergence suggestions
│   └── display.py               # ANSI-colored terminal panel rendering
├── configs/
│   ├── overpermissioned.json    # All 7 permissions UNRESTRICTED (demo default)
│   ├── developer.json           # Moderate developer workflow config
│   └── minimal_research.json    # Tightly scoped for research tasks
└── tests/
    ├── test_task_analyzer.py
    ├── test_risk_engine.py
    ├── test_consultant.py
    ├── test_permission_config.py
    └── test_display.py
```

## Dual Analysis Modes

| Feature | LLM Mode (default) | Keyword Mode (`--no-llm`) |
|---------|-------------------|--------------------------|
| Model | gpt-5-mini | None |
| Intent extraction | Semantic understanding | Regex word-boundary matching |
| Risk relevance | Per-path scoring with reasoning | Not available |
| Confidence | LLM self-assessed (0.0-1.0) | 1.0 if matched, 0.0 if fallback |
| Speed | ~3-5 seconds | <0.01 seconds |
| Dependency | `OPENAI_API_KEY` required | None |

If no API key is set, the system automatically falls back to keyword mode.

## Risk Paths Detected

| Risk Path | Permission Combination | Severity |
|---|---|---|
| Data Exfiltration | file_read + network_outbound | CRITICAL |
| Data Exfiltration via Skills | file_read + skill_connections | CRITICAL |
| Remote Code Execution | web_access + shell_execution | CRITICAL |
| Supply Chain Attack | web_access + file_write + shell_execution | CRITICAL |
| Local Filesystem Compromise | web_access + file_write | HIGH |
| Privilege Escalation | shell_execution + system_modification | HIGH |
| Persistent Backdoor | file_write + shell_execution | MEDIUM |

## Example Output

For the task "Help me search online for information on competitors and summarize it" with an over-permissioned configuration (LLM mode):

- **Analysis mode**: llm, Confidence: 85%
- **Detected intents**: Information Gathering, Content Creation
- **Required permissions**: 2 (web_access, network_outbound) -- both LIMITED
- **Deviation Index**: 84% (CRITICAL)
- **Risk paths found**: 7 with relevance scores (RCE 20%, Data Exfiltration 15%, Supply Chain 10%...)
- **Suggestions**: Disable 5 permissions, restrict 2 to LIMITED scope

## Design Principles

- **Non-blocking**: Suggestions are advisory. Users can always proceed with current config.
- **Task-aware**: Only flags excess permissions relative to the current task, not globally.
- **LLM-powered**: gpt-5-mini for semantic intent extraction and risk relevance scoring.
- **Graceful fallback**: Works without API key using deterministic keyword matching.
- **Weighted risk**: Deviation index accounts for permission severity, not just count.
- **Drift tracking**: Session history logs cumulative permission decisions over time.
