from __future__ import annotations

import json
from pathlib import Path

from core.config import PROMPTS_DIR
from core.llm_client import LLMClient
from schemas.models import ContextBundle, Plan, RepoSummary


PLAN_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "feature_name",
        "rationale",
        "user_facing_behavior",
        "schema_changes",
        "api_changes",
        "target_files",
        "out_of_scope",
        "assumptions",
    ],
    "properties": {
        "feature_name": {"type": "string"},
        "rationale": {"type": "string"},
        "user_facing_behavior": {"type": "string"},
        "schema_changes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["file", "description"],
                "properties": {
                    "file": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        },
        "api_changes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["method", "path", "description"],
                "properties": {
                    "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]},
                    "path": {"type": "string"},
                    "description": {"type": "string"},
                },
            },
        },
        "target_files": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["path", "action", "reason"],
                "properties": {
                    "path": {"type": "string"},
                    "action": {"type": "string", "enum": ["modify", "create"]},
                    "reason": {"type": "string"},
                },
            },
        },
        "out_of_scope": {"type": "array", "items": {"type": "string"}},
        "assumptions": {"type": "array", "items": {"type": "string"}},
    },
}


class Planner:
    # Initializes the planner with an LLM client and loads the system prompt
    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client
        self.system_prompt = (PROMPTS_DIR / "planner_system.md").read_text(encoding="utf-8")

    # Uses LLM to create a structured execution plan based on the user request and repo context
    def create_plan(
        self,
        *,
        request: str,
        repo_summary: RepoSummary,
        context_bundle: ContextBundle,
    ) -> Plan:
        known_files = set(repo_summary.files)
        user_prompt = self._build_user_prompt(request, repo_summary, context_bundle)
        return self.llm_client.complete_json(
            call_name="planner",
            system_prompt=self.system_prompt,
            user_prompt=user_prompt,
            schema_name="plan",
            json_schema=PLAN_JSON_SCHEMA,
            parser=lambda data: Plan.from_dict(data, known_files=known_files),
        )

    # Builds the user prompt containing request, repo summary, and file contents for the LLM
    def _build_user_prompt(
        self,
        request: str,
        repo_summary: RepoSummary,
        context_bundle: ContextBundle,
    ) -> str:
        files = []
        for item in context_bundle.files:
            files.append(
                {
                    "path": item.path,
                    "score": item.score,
                    "reason": item.reason,
                    "content": item.content,
                }
            )
        return (
            f"User request:\n{request}\n\n"
            "Repo summary:\n"
            f"{json.dumps(repo_summary.to_dict(), indent=2)}\n\n"
            "Shortlisted files with full content:\n"
            f"{json.dumps(files, indent=2)}"
        )
