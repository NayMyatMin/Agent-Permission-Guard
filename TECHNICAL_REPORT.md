# Agent Permission Guard: Technical Report

## Capability Boundary Consultant for AI Agent Permission Over-Authorization

---

## 1. Research Background

### 1.1 Problem Statement

As users interact with AI Agents daily, they gradually grant more permissions through habitual approval. This creates an accumulation of high-risk permission combinations that allow agents to autonomously execute dangerous actions.

Key findings from Anthropic's analysis of millions of Claude Code sessions:

- **Session duration nearly doubled** from <25 minutes (2025) to >45 minutes (2026)
- **Auto-approval adoption increases with experience**: ~20% for new users (<50 interactions) vs >40% for experienced users (>750 interactions)
- During a single task, LLMs often request additional permissions, and users tend to grant them

### 1.2 Root Causes

1. **Too many configurations and invisible combinations** -- Users cannot mentally model the interaction effects of 7+ permission categories across 3 scope levels
2. **Users are not clearly aware of high-risk actions** -- Users understand "payment risk" but do not recognize equally high risks in actions like automatically downloading files, logging into unfamiliar websites, modifying settings, or sending messages externally

### 1.3 Industry Consensus

Safe use of AI Agents requires collaboration of three parties:

| Party | Responsibility |
|-------|---------------|
| **System** | Initial access with minimal permissions |
| **User** | Decision-making on delegation for one-time tasks |
| **Agent** | Independently assess risks and proactively seek verification |

This PoC addresses the **System** layer: automatically analyzing task-permission alignment and advising users before execution begins.

---

## 2. Project Objective

Build a **Capability Boundary Consultant** that, when an agent starts a task, automatically generates:

1. **Task intent vs. actual agent capability** (deviation index)
2. **Risk roadmap** of the current permission combination
3. **Convergence suggestions** for agent permission configuration

### 2.1 Key Innovation Points

| AS IS | TO BE |
|-------|-------|
| Users review complex permission configurations themselves | System informs users of possible risk paths in the current configuration |
| System only notifies users of risk | System provides the minimum permission combination required for the task |

---

## 3. System Architecture

### 3.1 Project Structure

```
Agent-Permission-Guard/
├── main.py                      # CLI entry point (interactive + non-interactive + JSON)
├── requirements.txt             # openai>=1.0.0
├── src/
│   ├── models.py                # Core enums and dataclasses
│   ├── task_analyzer.py         # Keyword-based intent extraction (deterministic fallback)
│   ├── llm_analyzer.py          # LLM-backed intent extraction + risk relevance (gpt-5-mini)
│   ├── permission_config.py     # JSON permission profile loader with validation
│   ├── risk_engine.py           # Rule-based risk path detection + deviation index
│   ├── consultant.py            # Orchestrator: analysis pipeline coordinator
│   └── display.py               # ANSI-colored terminal panel renderer
├── configs/
│   ├── overpermissioned.json    # All 7 permissions UNRESTRICTED (demo default)
│   ├── developer.json           # Moderate developer workflow
│   └── minimal_research.json    # Tightly scoped for research tasks
└── tests/                       # 47 unit + integration tests
    ├── test_task_analyzer.py
    ├── test_risk_engine.py
    ├── test_consultant.py
    ├── test_permission_config.py
    └── test_display.py
```

**Total**: 22 files, 2,305 lines of code

### 3.2 Analysis Pipeline

```
User enters task description
        │
        ▼
┌─────────────────────────────┐
│  1. TASK INTENT ANALYSIS    │  LLM (gpt-5-mini) ──→ intents + minimum permissions
│     (src/llm_analyzer.py)   │  Fallback: keyword regex matching
│                             │  Output: TaskAnalysisResult (intents, permissions, confidence)
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  2. PERMISSION COMPARISON   │  Load JSON profile → compare required vs current
│     (src/consultant.py)     │  Output: excess permissions list
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  3. RISK PATH DETECTION     │  7 predefined dangerous combinations
│     (src/risk_engine.py)    │  Only flags paths involving EXCESS permissions
│                             │  Output: risk paths + deviation index (0.0-1.0)
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  4. RISK RELEVANCE SCORING  │  LLM rates each risk path's plausibility (0-1)
│     (src/llm_analyzer.py)   │  for this specific task
│                             │  Output: relevance scores + reasoning per risk
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  5. CONVERGENCE SUGGESTIONS │  DISABLE (not needed) or RESTRICT (scope too broad)
│     (src/consultant.py)     │  Sorted: disables first, then restrictions
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│  6. USER DECISION           │  [A] Accept all   [P] Partial   [K] Keep current
│     (main.py)               │  Non-blocking: user always proceeds regardless
└─────────────────────────────┘
```

### 3.3 Dual Analysis Modes

| Feature | LLM Mode (default) | Keyword Mode (`--no-llm`) |
|---------|-------------------|--------------------------|
| Model | gpt-5-mini | None |
| Intent extraction | Semantic understanding | Regex word-boundary matching |
| Permission details | Context-aware explanations | Template descriptions |
| Risk relevance | Per-path scoring with reasoning | Not available |
| Confidence | LLM self-assessed (0.0-1.0) | 1.0 if matched, 0.0 if fallback |
| Speed | ~3-5 seconds | <0.01 seconds |
| Dependency | OPENAI_API_KEY required | None |

---

## 4. Data Models

### 4.1 Permission Categories (7)

| Category | Risk Weight | Description |
|----------|------------|-------------|
| `web_access` | 2 | Browsing websites, fetching web content |
| `file_read` | 1 | Reading files from the filesystem |
| `file_write` | 2 | Writing/creating files on the filesystem |
| `shell_execution` | 3 | Running shell/terminal commands |
| `skill_connections` | 2 | Using integrated skills (email, Slack, git, cloud) |
| `network_outbound` | 3 | Making outbound HTTP/network requests |
| `system_modification` | 3 | Changing system settings, env vars, configs |

**Scope levels**: `UNRESTRICTED` (weight x2), `LIMITED` (base weight), `DISABLED` (0)

### 4.2 Risk Path Definitions (7)

| Risk Path | Severity | Permission Combination |
|-----------|----------|----------------------|
| Data Exfiltration | CRITICAL | file_read + network_outbound |
| Data Exfiltration via Skills | CRITICAL | file_read + skill_connections |
| Remote Code Execution | CRITICAL | web_access + shell_execution |
| Supply Chain Attack | CRITICAL | web_access + file_write + shell_execution |
| Local Filesystem Compromise | HIGH | web_access + file_write |
| Privilege Escalation | HIGH | shell_execution + system_modification |
| Persistent Backdoor | MEDIUM | file_write + shell_execution |

### 4.3 Deviation Index Formula

```
deviation_index = weighted_excess / weighted_total

where:
  weighted_excess = sum of risk_weight for each excess permission
                  + half risk_weight for required permissions with UNRESTRICTED scope
  weighted_total  = sum of risk_weight for all active permissions

If task confidence < 0.5: deviation_index *= 0.5 (dampened)
```

Range: **0.0** (perfectly aligned) to **1.0** (maximum over-authorization)

---

## 5. Terminal Display Color Coding

The Capability Boundary Consultant panel uses ANSI terminal colors with the following scheme:

### 5.1 Color Legend

```
CYAN + BOLD        Panel header ("CAPABILITY BOUNDARY CONSULTANT")
MAGENTA + BOLD     Section headers ("1. TASK INTENT ANALYSIS", etc.)
GREEN              Positive indicators: detected intents (+), required permissions (+)
                   Scope labels: DISABLED, well-aligned status
RED                Negative indicators: excess permissions (!), UNRESTRICTED scope
YELLOW             Moderate indicators: LIMITED scope, MEDIUM risk level
                   LOW CONFIDENCE warning
RED + BOLD         CRITICAL risk tags, DISABLE action labels
YELLOW + BOLD      RESTRICT action labels
DIM (gray)         Permission details, attack scenarios, reasons
WHITE + BOLD       Task description text
CYAN + BOLD        Summary note label
```

### 5.2 Deviation Index Bar

```
[██████████████████████░░░░░░░░] 75% (HIGH)
 ▲ Filled (colored)   ▲ Empty (gray)
```

| Range | Color | Label |
|-------|-------|-------|
| 0-30% | GREEN | LOW |
| 31-60% | YELLOW | MODERATE |
| 61-80% | RED | HIGH |
| 81-100% | RED + BOLD | CRITICAL |

### 5.3 Risk Relevance Scores (LLM mode)

```
[CRITICAL] Remote Code Execution  (relevance: 35%)
                                   ▲
                                   Color by relevance:
                                   ≥70%: RED
                                   40-69%: YELLOW
                                   <40%: DIM (gray)
```

---

## 6. PoC Demonstration

### 6.1 Use Case 1: Spec Example (Over-Permissioned Agent + Research Task)

**Setup**: Agent has all 7 permissions set to UNRESTRICTED (typical after months of habitual granting)
**Task**: "Help me search online for information on competitors and summarize it."

#### Step 1: Agent initiates task

```bash
$ python main.py configs/overpermissioned.json \
    "Help me search online for information on competitors and summarize it"
```

#### Step 2: System analyzes task intent (LLM mode)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ CAPABILITY BOUNDARY CONSULTANT  [llm]                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ 1. TASK INTENT ANALYSIS                                                      │
│   Task: Help me search online for information on competitors and summarize it│
│                                                                              │
│   Detected intents:                                                          │
│     + Information Gathering                                                  │
│     + Content Creation                                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ 2. MINIMUM REQUIRED PERMISSIONS                                              │
│   + web_access             [LIMITED]                                         │
│     To browse public websites, search engines, news articles, and company    │
│     pages to collect information about competitors.                          │
│   + network_outbound       [LIMITED]                                         │
│     To make outbound HTTP requests needed to fetch web pages, APIs, or       │
│     search results for compiling and summarizing competitor information.      │
```

The LLM identifies only **2 permissions** needed (web_access and network_outbound), both at LIMITED scope. It correctly determines that file_read, file_write, shell_execution, skill_connections, and system_modification are **not required**.

#### Step 3: System analyzes current permission combination

```
├──────────────────────────────────────────────────────────────────────────────┤
│ 3. EXCESS PERMISSIONS DETECTED                                               │
│   ! web_access             [UNRESTRICTED]                                    │
│     Scope exceeds task needs (LIMITED sufficient)                             │
│   ! file_read              [UNRESTRICTED]                                    │
│     Not required for this task                                               │
│   ! file_write             [UNRESTRICTED]                                    │
│     Not required for this task                                               │
│   ! shell_execution        [UNRESTRICTED]                                    │
│     Not required for this task                                               │
│   ! skill_connections      [UNRESTRICTED]                                    │
│     Not required for this task                                               │
│   ! network_outbound       [UNRESTRICTED]                                    │
│     Scope exceeds task needs (LIMITED sufficient)                             │
│   ! system_modification    [UNRESTRICTED]                                    │
│     Not required for this task                                               │
│                                                                              │
│   Deviation Index: [█████████████████████████░░░░░] 84% (CRITICAL)           │
```

**All 7 permissions** are flagged as excess: 5 should be DISABLED, 2 should be RESTRICTED from UNRESTRICTED to LIMITED. Deviation index: **84% CRITICAL**.

#### Step 4: System displays risk roadmap with LLM relevance scoring

```
├──────────────────────────────────────────────────────────────────────────────┤
│ 4. RISK ROADMAP                                                              │
│   [CRITICAL] Remote Code Execution  (relevance: 20%)                         │
│     Content fetched from the web could be executed as shell commands.         │
│     Requires: web_access, shell_execution                                    │
│     Scenario: The agent fetches content from a website (which may contain     │
│       prompt injection) and executes it as a shell command.                   │
│     Why: Web access is core to the task. If shell execution is also granted,  │
│       fetched content could be executed, but execution is not needed for      │
│       research, so relevance is moderate.                                     │
│                                                                              │
│   [CRITICAL] Data Exfiltration  (relevance: 15%)                             │
│     Local file content could be silently sent to external endpoints.          │
│     Requires: file_read, network_outbound                                    │
│     Why: The task does not require reading local files. Exfiltration is       │
│       possible only if the agent is overprivileged or prompt-injected.        │
│                                                                              │
│   [CRITICAL] Data Exfiltration via Skills  (relevance: 12%)                  │
│     Local file content could be leaked through connected skills.              │
│     Requires: file_read, skill_connections                                    │
│                                                                              │
│   [CRITICAL] Supply Chain Attack  (relevance: 10%)                           │
│     Malicious packages could be downloaded, written to disk, and executed.    │
│     Requires: web_access, file_write, shell_execution                         │
│                                                                              │
│   [HIGH] Local Filesystem Compromise  (relevance: 18%)                       │
│     External content could be written to the local filesystem.                │
│     Requires: web_access, file_write                                          │
│                                                                              │
│   [HIGH] Privilege Escalation  (relevance: 6%)                               │
│     Shell access + system modification enables privilege escalation.           │
│     Requires: shell_execution, system_modification                            │
│                                                                              │
│   [MEDIUM] Persistent Backdoor  (relevance: 8%)                              │
│     File write + shell access enables persistent malware installation.        │
│     Requires: file_write, shell_execution                                     │
```

The LLM provides **per-risk relevance scoring** with explanations. Remote Code Execution gets 20% relevance (web access is required for the task, so fetching malicious content is plausible), while Privilege Escalation gets only 6% (completely unrelated to research).

#### Step 5: System provides convergence suggestions

```
├──────────────────────────────────────────────────────────────────────────────┤
│ 5. CONVERGENCE SUGGESTIONS                                                   │
│   1. [DISABLE] file_read                                                     │
│      UNRESTRICTED -> DISABLED                                                │
│      Not required for task: Information Gathering, Content Creation           │
│                                                                              │
│   2. [DISABLE] file_write                                                    │
│      UNRESTRICTED -> DISABLED                                                │
│      Not required for task: Information Gathering, Content Creation           │
│                                                                              │
│   3. [DISABLE] shell_execution                                               │
│      UNRESTRICTED -> DISABLED                                                │
│      Not required for task: Information Gathering, Content Creation           │
│                                                                              │
│   4. [DISABLE] skill_connections                                             │
│      UNRESTRICTED -> DISABLED                                                │
│      Not required for task: Information Gathering, Content Creation           │
│                                                                              │
│   5. [DISABLE] system_modification                                           │
│      UNRESTRICTED -> DISABLED                                                │
│      Not required for task: Information Gathering, Content Creation           │
│                                                                              │
│   6. [RESTRICT] web_access                                                   │
│      UNRESTRICTED -> LIMITED                                                 │
│      Task requires web_access but only with limited scope.                   │
│                                                                              │
│   7. [RESTRICT] network_outbound                                             │
│      UNRESTRICTED -> LIMITED                                                 │
│      Task requires network_outbound but only with limited scope.             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   Note: The above changes preserve the primary capability of "Information    │
│   Gathering, Content Creation" while significantly reducing risks both       │
│   externally and locally. Addresses 4 CRITICAL risk path(s).                 │
│   Addresses 2 HIGH risk path(s).                                             │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

#### Step 6: User selection

```
Select an option:
  [A] Accept all suggestions
  [P] Partially accept (select which to apply)
  [K] Keep current configuration and continue
```

No interception is performed. Even if the user selects **[K] Keep current**, the task proceeds.

#### Summary Output

```
Analysis Mode: llm
Confidence: 85%
Intents: information_gathering, content_creation
Deviation Index: 84%
Risk Paths: 7
Suggestions: 7
  - Disable file_read: unrestricted -> disabled
  - Disable file_write: unrestricted -> disabled
  - Disable shell_execution: unrestricted -> disabled
  - Disable skill_connections: unrestricted -> disabled
  - Disable system_modification: unrestricted -> disabled
  - Restrict web_access: unrestricted -> limited
  - Restrict network_outbound: unrestricted -> limited
```

---

### 6.2 Use Case 2: Code Execution Task (Over-Permissioned Agent + Dev Task)

**Setup**: Same over-permissioned agent (all 7 UNRESTRICTED)
**Task**: "Run the test suite and fix any failing tests."
**Key difference**: This task *legitimately requires* shell_execution, file_read, and file_write -- the system should RESTRICT them, not DISABLE.

```bash
$ python main.py configs/overpermissioned.json \
    "Run the test suite and fix any failing tests"
```

#### Intent Analysis

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ CAPABILITY BOUNDARY CONSULTANT  [llm]                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ 1. TASK INTENT ANALYSIS                                                      │
│   Task: Run the test suite and fix any failing tests                         │
│                                                                              │
│   Detected intents:                                                          │
│     + Code Execution                                                         │
│     + File Management                                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ 2. MINIMUM REQUIRED PERMISSIONS                                              │
│   + shell_execution        [LIMITED]                                         │
│     Run the project's test runner (e.g., pytest/npm test) and obtain output. │
│   + file_read              [LIMITED]                                         │
│     Read source code, tests, and config files to diagnose failures.          │
│   + file_write             [LIMITED]                                         │
│     Modify source/test files to implement fixes for failing tests.           │
│   + network_outbound       [LIMITED]                                         │
│     Only if running tests requires installing dependencies.                  │
```

**4 permissions required** (vs 2 for research). Shell, file read, file write are all legitimately needed -- the system recognizes this.

#### Excess Permissions and Deviation

```
│ 3. EXCESS PERMISSIONS DETECTED                                               │
│   ! web_access             [UNRESTRICTED]  -- Not required for this task     │
│   ! file_read              [UNRESTRICTED]  -- Scope exceeds (LIMITED enough) │
│   ! file_write             [UNRESTRICTED]  -- Scope exceeds (LIMITED enough) │
│   ! shell_execution        [UNRESTRICTED]  -- Scope exceeds (LIMITED enough) │
│   ! skill_connections      [UNRESTRICTED]  -- Not required for this task     │
│   ! network_outbound       [UNRESTRICTED]  -- Scope exceeds (LIMITED enough) │
│   ! system_modification    [UNRESTRICTED]  -- Not required for this task     │
│                                                                              │
│   Deviation Index: [█████████████████████░░░░░░░░░] 72% (HIGH)               │
```

Deviation is **72% HIGH** -- lower than the research task's 84% because more permissions are legitimately needed.

#### Risk Roadmap (with LLM relevance)

```
│ 4. RISK ROADMAP                                                              │
│   [CRITICAL] Data Exfiltration via Skills  (relevance: 85%)                  │
│     Requires: file_read, skill_connections                                   │
│     Why: Running tests requires reading source files which may include        │
│     secrets. If skill_connections is also granted, those files could be       │
│     sent externally through email or Slack.                                   │
│                                                                              │
│   [CRITICAL] Supply Chain Attack  (relevance: 80%)                           │
│     Requires: web_access, file_write, shell_execution                        │
│     Why: Fixing tests often entails installing/updating dependencies.         │
│     That combination maps closely to a supply-chain attack vector.            │
│                                                                              │
│   [CRITICAL] Remote Code Execution  (relevance: 60%)                         │
│     Requires: web_access, shell_execution                                    │
│     Why: The task uses shell commands. If web content is fetched and          │
│     executed, full compromise is possible. Plausible but less direct.         │
│                                                                              │
│   [HIGH] Local Filesystem Compromise  (relevance: 70%)                       │
│     Requires: web_access, file_write                                         │
│     Why: The agent may write patches or downloaded resources to disk.         │
│                                                                              │
│   [HIGH] Privilege Escalation  (relevance: 35%)                              │
│     Requires: shell_execution, system_modification                           │
│     Why: Shell is needed, but system modification is not. Possible            │
│     only with excessive permissions.                                          │
```

**Key insight**: Supply Chain Attack gets **80% relevance** here (vs 10% for research) because installing dependencies during test fixing is a realistic workflow. The same risk path, completely different relevance depending on the task.

#### Convergence Suggestions

```
│ 5. CONVERGENCE SUGGESTIONS                                                   │
│   1. [DISABLE] web_access         UNRESTRICTED -> DISABLED                   │
│   2. [DISABLE] skill_connections  UNRESTRICTED -> DISABLED                   │
│   3. [DISABLE] system_modification UNRESTRICTED -> DISABLED                  │
│   4. [RESTRICT] file_read         UNRESTRICTED -> LIMITED                    │
│   5. [RESTRICT] file_write        UNRESTRICTED -> LIMITED                    │
│   6. [RESTRICT] shell_execution   UNRESTRICTED -> LIMITED                    │
│   7. [RESTRICT] network_outbound  UNRESTRICTED -> LIMITED                    │
```

**3 DISABLE + 4 RESTRICT** -- the system correctly keeps shell_execution, file_read, and file_write active (restricted) while disabling unrelated permissions.

#### Summary

```
Analysis Mode: llm | Confidence: 80% | Deviation: 72% (HIGH)
Intents: code_execution, file_management
Risk Paths: 5 | Suggestions: 7
```

---

### 6.3 Use Case 3: Communication Task (Highest Risk Relevance)

**Setup**: Same over-permissioned agent (all 7 UNRESTRICTED)
**Task**: "Send an email to the team with the weekly status update."
**Key difference**: Only needs **1 permission** (skill_connections). The tightest minimum set of any task. Data Exfiltration via Skills gets **95% relevance** -- the highest of any scenario -- because the task *actually uses* the communication channel.

```bash
$ python main.py configs/overpermissioned.json \
    "Send an email to the team with the weekly status update"
```

#### Intent Analysis

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ CAPABILITY BOUNDARY CONSULTANT  [llm]                                        │
├──────────────────────────────────────────────────────────────────────────────┤
│ 1. TASK INTENT ANALYSIS                                                      │
│   Task: Send an email to the team with the weekly status update              │
│                                                                              │
│   Detected intents:                                                          │
│     + Communication                                                          │
│     + Content Creation                                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ 2. MINIMUM REQUIRED PERMISSIONS                                              │
│   + skill_connections      [LIMITED]                                         │
│     Use the integrated email-sending capability to compose and send a        │
│     single weekly status email to the team's recipients; limited to this     │
│     message only (no broader mailbox access or file operations).             │
```

**Only 1 permission** needed. The LLM determines that even network_outbound and file_read are unnecessary -- the email skill handles the network layer internally.

#### Excess Permissions and Deviation

```
│ 3. EXCESS PERMISSIONS DETECTED                                               │
│   ! web_access             [UNRESTRICTED]  -- Not required                   │
│   ! file_read              [UNRESTRICTED]  -- Not required                   │
│   ! file_write             [UNRESTRICTED]  -- Not required                   │
│   ! shell_execution        [UNRESTRICTED]  -- Not required                   │
│   ! skill_connections      [UNRESTRICTED]  -- Scope exceeds (LIMITED enough) │
│   ! network_outbound       [UNRESTRICTED]  -- Not required                   │
│   ! system_modification    [UNRESTRICTED]  -- Not required                   │
│                                                                              │
│   Deviation Index: [████████████████████████████░░] 94% (CRITICAL)           │
```

**94% CRITICAL** -- the highest deviation of any task. 6 of 7 permissions should be fully DISABLED, 1 should be RESTRICTED.

#### Risk Roadmap (with LLM relevance)

```
│ 4. RISK ROADMAP                                                              │
│   [CRITICAL] Data Exfiltration via Skills  (relevance: 95%)                  │
│     Requires: file_read, skill_connections                                   │
│     Why: This task explicitly uses an email/communication skill. If the      │
│     agent can read local files and forward content to a connected skill,     │
│     sensitive data could be sent unintentionally or via prompt injection.     │
│     The combination directly maps to the email-sending workflow, making      │
│     it highly relevant.                                                       │
│                                                                              │
│   [CRITICAL] Data Exfiltration  (relevance: 85%)                             │
│     Requires: file_read, network_outbound                                    │
│     Why: Sending an email may read a local draft or notes. If the agent      │
│     has broad file_read plus network_outbound, it could read other           │
│     sensitive local files and send them externally.                           │
│                                                                              │
│   [CRITICAL] Remote Code Execution  (relevance: 5%)                          │
│     Requires: web_access, shell_execution                                    │
│     Why: Fetching and executing web content is not needed to compose or      │
│     send a weekly status email. Relevance is minimal.                        │
│                                                                              │
│   [CRITICAL] Supply Chain Attack  (relevance: 5%)                            │
│     Requires: web_access, file_write, shell_execution                        │
│     Why: Downloading and executing packages is unrelated to composing        │
│     and sending a status email.                                               │
│                                                                              │
│   [HIGH] Local Filesystem Compromise  (relevance: 20%)                       │
│   [HIGH] Privilege Escalation  (relevance: 2%)                               │
│   [MEDIUM] Persistent Backdoor  (relevance: 3%)                              │
```

**Key insight**: Same "Data Exfiltration via Skills" risk path gets **95% relevance** here vs **12% for research** vs **85% for code execution**. The LLM understands that an email task *inherently operates* through the skill_connections channel, making data leakage through that channel far more plausible. Meanwhile, Remote Code Execution drops to **5%** (vs 20% for research, 60% for code execution) because there is no reason to run shell commands when sending an email.

#### Convergence Suggestions

```
│ 5. CONVERGENCE SUGGESTIONS                                                   │
│   1. [DISABLE] web_access          UNRESTRICTED -> DISABLED                  │
│   2. [DISABLE] file_read           UNRESTRICTED -> DISABLED                  │
│   3. [DISABLE] file_write          UNRESTRICTED -> DISABLED                  │
│   4. [DISABLE] shell_execution     UNRESTRICTED -> DISABLED                  │
│   5. [DISABLE] network_outbound    UNRESTRICTED -> DISABLED                  │
│   6. [DISABLE] system_modification UNRESTRICTED -> DISABLED                  │
│   7. [RESTRICT] skill_connections  UNRESTRICTED -> LIMITED                   │
```

**6 DISABLE + 1 RESTRICT** -- the most aggressive convergence of any task. Only skill_connections survives, and even that is restricted to LIMITED scope (single email, specific recipients only).

#### Summary

```
Analysis Mode: llm | Confidence: 90% | Deviation: 94% (CRITICAL)
Intents: communication, content_creation
Risk Paths: 7 | Suggestions: 7
```

---

### 6.4 Use Case Comparison Summary

| Metric | Research Task | Code Execution | Email Task |
|--------|-------------|---------------|------------|
| Task | Search + summarize | Run tests + fix | Send status email |
| Intents | info_gathering, content_creation | code_execution, file_management | communication, content_creation |
| Required permissions | 2 (web, network) | 4 (shell, file_r, file_w, network) | 1 (skills) |
| Deviation index | 84% CRITICAL | 72% HIGH | 94% CRITICAL |
| Risk paths | 7 | 5 | 7 |
| Top risk relevance | RCE 20% | Data Exfil via Skills 85% | Data Exfil via Skills 95% |
| Lowest risk relevance | Priv Escalation 6% | Priv Escalation 35% | Priv Escalation 2% |
| DISABLE suggestions | 5 | 3 | 6 |
| RESTRICT suggestions | 2 | 4 | 1 |

This table demonstrates that the system produces **task-aware, proportional responses** -- not a one-size-fits-all alert.

---

### 6.5 Use Case 5: LLM vs Keyword Mode Comparison (Ambiguous Task)

**Task**: "Find competitor pricing strategy and prepare a brief for the exec team"

This task contains no keywords that the regex matcher recognizes. "Find" alone is not in the keyword list (only "find information" is), and "prepare a brief" is not matched by any rule.

#### Keyword Mode Result

```bash
$ python main.py --no-llm --json configs/overpermissioned.json \
    "Find competitor pricing strategy and prepare a brief for the exec team"
```

```json
{
  "analysis_mode": "keyword",
  "confidence": 0.0,
  "task_intents": ["information_gathering"],
  "deviation_index": 0.48
}
```

- **Confidence: 0%** -- No keywords matched, falls back to generic `information_gathering`
- **Deviation index dampened** from ~96% to 48% (multiplied by 0.5 due to low confidence)
- Misses the "content creation" intent entirely

#### LLM Mode Result

```bash
$ python main.py --json configs/overpermissioned.json \
    "Find competitor pricing strategy and prepare a brief for the exec team"
```

```json
{
  "analysis_mode": "llm",
  "confidence": 0.8,
  "task_intents": ["information_gathering", "content_creation"],
  "deviation_index": 0.94
}
```

- **Confidence: 80%** -- LLM understands the full task semantics
- Correctly identifies **both** intents: research + document creation
- **Deviation index: 94%** -- accurate reflection of the over-authorization

---

### 6.6 Use Case 6: Well-Aligned Configuration

**Setup**: Minimal research profile (only 4 permissions active, all LIMITED)
**Task**: Same research task as Use Case 1

```bash
$ python main.py --json configs/minimal_research.json \
    "Help me search online for information on competitors and summarize it"
```

```json
{
  "analysis_mode": "llm",
  "confidence": 0.85,
  "deviation_index": 0.38,
  "excess_permissions": [
    {"category": "file_read", "excess_reason": "Not required for this task"},
    {"category": "file_write", "excess_reason": "Not required for this task"}
  ],
  "risk_paths": [
    {"name": "Data Exfiltration", "level": "critical"},
    {"name": "Local Filesystem Compromise", "level": "high"}
  ],
  "suggestions": [
    {"action": "Disable", "permission": "file_read"},
    {"action": "Disable", "permission": "file_write"}
  ]
}
```

- **Deviation: 38%** (MODERATE) -- much lower than the 84% from overpermissioned config
- Only **2 risk paths** detected (vs 7 with overpermissioned)
- Only **2 suggestions** (vs 7)
- System does not over-alarm when permissions are reasonable

---

### 6.7 Use Case 7: JSON Output for Automation

```bash
$ python main.py --json configs/overpermissioned.json "Run the test suite"
```

Produces a complete machine-readable JSON report suitable for:
- CI/CD pipeline integration
- Automated permission auditing
- Dashboard visualization
- Alerting systems

---

### 6.8 Use Case 8: Session Drift Tracking

After multiple analyses, the system logs each result to `session_history.jsonl`:

```bash
$ python main.py --history
```

```
  SESSION DRIFT SUMMARY (5 analyses)
  ─────────────────────────────────────
  Suggestions dismissed: 3/5 (60%)
  Average deviation index: 72%
  Total risk paths flagged: 28
  Warning: Majority of suggestions dismissed — permission surface unchanged.
```

This directly connects to the research data: as users dismiss suggestions, permission surface grows over time.

---

## 7. Comparison: Before vs After

### 7.1 The 6-Step Flow

| Step | Spec Requirement | PoC Implementation |
|------|-----------------|-------------------|
| 1. Agent initiates task | "Help me search online for competitors and summarize it" | Interactive CLI or non-interactive `python main.py <config> <task>` |
| 2. System analyzes task intent | Refine goal: collect info, summarize, output for review | LLM extracts intents + minimum permissions with confidence score |
| 3. Analyze current permissions | Found: any website, all file paths, skills, shell | Loads JSON profile, compares all 7 categories and scopes |
| 4. Display consultant panel | Show objectives, excess, risk paths | 5-section panel with color coding, deviation bar, relevance scores |
| 5. Provide suggestions | Disable shell, read-only dir, disconnect skills | Ordered DISABLE/RESTRICT suggestions with reasons |
| 6. User selection | Agree / Partially agree / Keep current | [A] Accept all / [P] Partial / [K] Keep current (non-blocking) |

### 7.2 Innovation Points Delivered

| Innovation | How Delivered |
|-----------|--------------|
| Show risk paths (not just list permissions) | 7 risk path definitions with attack scenarios, LLM relevance scoring |
| Provide minimum permission set (not just flag risk) | LLM-generated minimum permissions with context-aware justifications |
| Quantify over-authorization | Weighted deviation index (0-100%) with visual bar |
| Track permission drift | Session history JSONL log with drift summary |

---

## 8. Test Results

```
============================= test session starts ==============================
collected 47 items

tests/test_consultant.py::TestConsultant::test_all_risk_paths_involve_excess       PASSED [  2%]
tests/test_consultant.py::TestConsultant::test_ambiguous_task_dampens_deviation     PASSED [  4%]
tests/test_consultant.py::TestConsultant::test_ambiguous_task_has_low_confidence    PASSED [  6%]
tests/test_consultant.py::TestConsultant::test_code_execution_task                 PASSED [  8%]
tests/test_consultant.py::TestConsultant::test_excess_permissions_preserve_details  PASSED [ 10%]
tests/test_consultant.py::TestConsultant::test_no_duplicate_risk_paths             PASSED [ 12%]
tests/test_consultant.py::TestConsultant::test_report_has_summary_note             PASSED [ 14%]
tests/test_consultant.py::TestConsultant::test_research_task_with_minimal_config    PASSED [ 17%]
tests/test_consultant.py::TestConsultant::test_research_task_with_overpermissioned  PASSED [ 19%]
tests/test_consultant.py::TestConsultant::test_suggestions_disable_before_restrict  PASSED [ 21%]
tests/test_display.py::TestConsultantDisplay::test_box_line_consistent_width        PASSED [ 23%]
tests/test_display.py::TestConsultantDisplay::test_box_line_has_right_border        PASSED [ 25%]
tests/test_display.py::TestConsultantDisplay::test_box_line_long_content_closes     PASSED [ 27%]
tests/test_display.py::TestConsultantDisplay::test_visible_len_plain_text           PASSED [ 29%]
tests/test_display.py::TestConsultantDisplay::test_visible_len_with_ansi            PASSED [ 31%]
tests/test_permission_config.py::TestPermissionConfigValidation (8 tests)           PASSED [ 48%]
tests/test_risk_engine.py::TestRiskEngine (12 tests)                               PASSED [ 74%]
tests/test_task_analyzer.py::TestTaskAnalyzer (12 tests)                           PASSED [100%]

============================== 47 passed in 0.04s ==============================
```

### Test Coverage by Module

| Module | Tests | Coverage |
|--------|-------|---------|
| `test_consultant.py` | 10 | Full pipeline, ambiguity handling, excess detection, risk paths, confidence |
| `test_risk_engine.py` | 12 | All 7 risk paths, excess filtering, deviation index, sorting, edge cases |
| `test_task_analyzer.py` | 12 | All 6 intent types, fallback, confidence, multi-intent, scope dedup |
| `test_permission_config.py` | 8 | File not found, invalid JSON, missing fields, bad values, validation |
| `test_display.py` | 5 | ANSI stripping, box border closure, width consistency |
| **Total** | **47** | **All pass in 0.04s** |

---

## 9. CLI Reference

```bash
# Interactive demo (LLM-powered, prompts for profile and task)
python main.py

# Interactive demo, keyword-only (no API key needed)
python main.py --no-llm

# Non-interactive analysis
python main.py configs/overpermissioned.json "Your task description"

# JSON output (machine-readable, for automation)
python main.py --json configs/overpermissioned.json "Your task description"

# Keyword-only, non-interactive
python main.py --no-llm configs/overpermissioned.json "Your task description"

# Show session drift summary
python main.py --history

# Help
python main.py --help
```

### Environment Requirements

- Python 3.10+
- `openai` Python SDK (`pip install openai`)
- `OPENAI_API_KEY` environment variable (for LLM mode; keyword mode works without it)

---

## 10. Conclusion

This PoC demonstrates that a **Capability Boundary Consultant** can effectively:

1. **Detect permission over-authorization** by comparing task intent against current configuration
2. **Quantify risk** through a weighted deviation index and per-risk relevance scoring
3. **Provide actionable convergence** with specific DISABLE/RESTRICT recommendations
4. **Operate non-blockingly** -- advising users without preventing task execution

The dual-mode architecture (LLM + keyword) provides both **flexibility** (LLM handles ambiguous, paraphrased tasks) and **reliability** (keyword fallback when no API is available), while the risk relevance scoring ensures users see the most contextually relevant threats first rather than a flat list of all possible attack paths.
