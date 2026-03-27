"""LLM-backed task intent extraction and risk relevance scoring using OpenAI."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from .models import (
    Permission,
    PermissionCategory,
    PermissionScope,
    RiskPath,
    TaskCapability,
)
from .task_analyzer import TaskAnalysisResult

_VALID_INTENTS = [e.value for e in TaskCapability]
_VALID_CATEGORIES = [e.value for e in PermissionCategory]

_INTENT_SYSTEM_PROMPT = """\
You are a task intent analyzer for an AI agent permission guard system.

Given a user's task description, determine:
1. What capabilities the task requires
2. The minimum permissions needed (principle of least privilege)

Valid intents (pick ALL that apply):
- information_gathering: searching, researching, browsing, looking up information
- content_creation: writing, summarizing, drafting, composing documents
- code_execution: running scripts, building, testing, deploying, compiling
- file_management: downloading, uploading, copying, moving, organizing files
- communication: sending emails, messages, notifications, posting to channels
- system_modification: configuring settings, installing software, modifying system config

Valid permission categories:
- web_access: browsing websites, fetching web content
- file_read: reading files from the filesystem
- file_write: writing/creating files on the filesystem
- shell_execution: running shell/terminal commands
- skill_connections: using integrated skills (email, messaging, cloud storage, git)
- network_outbound: making outbound HTTP/network requests
- system_modification: changing system settings, environment variables, configs

Return a JSON object with exactly this structure:
{
  "intents": ["intent1", "intent2"],
  "permissions": [
    {"category": "category_name", "scope": "limited", "details": "why this permission is needed"}
  ],
  "confidence": 0.95,
  "task_summary": "Brief 1-sentence summary of what the user wants to accomplish"
}

Rules:
- scope should ALWAYS be "limited" (minimum privilege)
- Only include permissions strictly necessary for the task
- confidence: 0.0-1.0 based on how clear and specific the task is
- If the task is vague/ambiguous, still make your best guess but lower the confidence
"""

_RISK_RELEVANCE_SYSTEM_PROMPT = """\
You are a security risk analyst for an AI agent permission system.

Given a task description and a list of detected risk paths (dangerous permission combinations), \
rate how relevant each risk path is to this specific task.

A risk is highly relevant if:
- The task could plausibly trigger the attack scenario
- The excess permissions involved are close to what the task does
- A prompt injection or misinterpretation could realistically cause harm through this path

A risk is less relevant if:
- The attack scenario is theoretically possible but extremely unlikely for this task
- The permissions involved are completely unrelated to the task's domain

Return a JSON object with exactly this structure:
{
  "ratings": [
    {
      "risk_name": "Name of the risk path",
      "relevance": 0.85,
      "reasoning": "Brief explanation of why this relevance score"
    }
  ]
}

relevance is 0.0 (not relevant at all) to 1.0 (highly relevant and plausible).
"""


def _get_client():
    """Create OpenAI client. Returns None if no API key is available."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except ImportError:
        return None


def is_llm_available() -> bool:
    """Check if LLM analysis is available (API key set and openai installed)."""
    return _get_client() is not None


def llm_analyze_task(
    task_description: str,
    model: str = "gpt-5-mini",
) -> TaskAnalysisResult | None:
    """Extract task intent using an LLM. Returns None on failure."""
    client = _get_client()
    if client is None:
        return None

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": task_description},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=4096,
        )

        raw = response.choices[0].message.content
        if not raw:
            return None

        data = json.loads(raw)
        return _parse_intent_response(task_description, data)

    except Exception:
        return None


def _parse_intent_response(task_description: str, data: dict) -> TaskAnalysisResult | None:
    """Parse the LLM's JSON response into a TaskAnalysisResult."""
    try:
        raw_intents = data.get("intents", [])
        intents = []
        for val in raw_intents:
            if val in _VALID_INTENTS:
                intents.append(TaskCapability(val))

        raw_permissions = data.get("permissions", [])
        permissions = []
        seen_cats: set[str] = set()
        for entry in raw_permissions:
            cat_val = entry.get("category", "")
            if cat_val in _VALID_CATEGORIES and cat_val not in seen_cats:
                seen_cats.add(cat_val)
                permissions.append(Permission(
                    category=PermissionCategory(cat_val),
                    scope=PermissionScope.LIMITED,
                    details=entry.get("details", ""),
                ))

        confidence = float(data.get("confidence", 0.8))
        confidence = max(0.0, min(1.0, confidence))

        if not intents:
            return None

        return TaskAnalysisResult(
            task_description=task_description,
            intents=intents,
            required_permissions=permissions,
            confidence=confidence,
        )

    except (KeyError, TypeError, ValueError):
        return None


@dataclass
class RiskRelevanceRating:
    """LLM's assessment of a risk path's relevance to the current task."""
    risk_name: str
    relevance: float
    reasoning: str


def llm_score_risk_relevance(
    task_description: str,
    risk_paths: list[RiskPath],
    model: str = "gpt-5-mini",
) -> dict[str, RiskRelevanceRating] | None:
    """Score each risk path's relevance to the task using an LLM. Returns None on failure."""
    if not risk_paths:
        return {}

    client = _get_client()
    if client is None:
        return None

    risk_descriptions = []
    for rp in risk_paths:
        risk_descriptions.append({
            "name": rp.name,
            "level": rp.level.value,
            "description": rp.description,
            "involved_permissions": [c.value for c in rp.involved_permissions],
            "attack_scenario": rp.attack_scenario,
        })

    user_message = json.dumps({
        "task": task_description,
        "risk_paths": risk_descriptions,
    }, indent=2)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _RISK_RELEVANCE_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            max_completion_tokens=4096,
        )

        raw = response.choices[0].message.content
        if not raw:
            return None

        data = json.loads(raw)
        return _parse_relevance_response(data)

    except Exception:
        return None


def _parse_relevance_response(data: dict) -> dict[str, RiskRelevanceRating]:
    """Parse the LLM's risk relevance response."""
    ratings: dict[str, RiskRelevanceRating] = {}
    try:
        for entry in data.get("ratings", []):
            name = entry.get("risk_name", "")
            relevance = float(entry.get("relevance", 0.5))
            relevance = max(0.0, min(1.0, relevance))
            reasoning = entry.get("reasoning", "")
            if name:
                ratings[name] = RiskRelevanceRating(
                    risk_name=name,
                    relevance=relevance,
                    reasoning=reasoning,
                )
    except (KeyError, TypeError, ValueError):
        pass
    return ratings
