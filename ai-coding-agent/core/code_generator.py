from __future__ import annotations

import json
import subprocess
from pathlib import Path

from core.config import PROMPTS_DIR
from core.llm_client import LLMClient
from schemas.models import Patch, Plan, RepoSummary, TargetFile


PATCH_JSON_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["path", "action", "full_content", "change_summary"],
    "properties": {
        "path": {"type": "string"},
        "action": {"type": "string", "enum": ["modify", "create"]},
        "full_content": {"type": "string"},
        "change_summary": {"type": "string"},
    },
}


class CodeGenerator:
    # Initializes the code generator with LLM client and creates syntax check directory
    def __init__(self, llm_client: LLMClient, run_dir: Path) -> None:
        self.llm_client = llm_client
        self.run_dir = run_dir
        self.system_prompt = (PROMPTS_DIR / "codegen_system.md").read_text(encoding="utf-8")
        self.syntax_dir = run_dir / "syntax-checks"
        self.syntax_dir.mkdir(parents=True, exist_ok=True)

    # Generates code patches for all target files specified in the plan
    def generate_patches(self, *, repo_path: Path, repo_summary: RepoSummary, plan: Plan) -> list[Patch]:
        patches: list[Patch] = []
        for target_file in plan.target_files:
            patches.append(
                self.generate_patch(
                    repo_path=repo_path,
                    repo_summary=repo_summary,
                    plan=plan,
                    target_file=target_file,
                )
            )
        return patches

    # Generates a single code patch for a target file with syntax validation and retry logic
    def generate_patch(
        self,
        *,
        repo_path: Path,
        repo_summary: RepoSummary,
        plan: Plan,
        target_file: TargetFile,
    ) -> Patch:
        file_path = repo_path / target_file.path
        original_content = ""
        if target_file.action == "modify":
            original_content = file_path.read_text(encoding="utf-8", errors="replace")

        user_prompt = self._build_user_prompt(
            repo_summary=repo_summary,
            plan=plan,
            target_file=target_file,
            current_content=original_content,
            repair_error=None,
        )

        last_error: str | None = None
        for attempt in range(1, 3):
            prompt = user_prompt
            if last_error:
                prompt = self._build_user_prompt(
                    repo_summary=repo_summary,
                    plan=plan,
                    target_file=target_file,
                    current_content=original_content,
                    repair_error=last_error,
                )
            patch = self.llm_client.complete_json(
                call_name=f"codegen_{self._safe_name(target_file.path)}",
                system_prompt=self.system_prompt,
                user_prompt=prompt,
                schema_name="patch",
                json_schema=PATCH_JSON_SCHEMA,
                parser=lambda data: Patch.from_dict(
                    data,
                    expected_path=target_file.path,
                    expected_action=target_file.action,
                    original_content=original_content,
                ),
            )

            syntax_error = self._syntax_error_if_any(patch)
            if not syntax_error:
                return patch
            last_error = syntax_error

        raise RuntimeError(
            f"Generated code for {target_file.path} failed node --check after one repair retry: {last_error}"
        )

    # Builds the user prompt with plan, repo info, and current file content for the LLM
    def _build_user_prompt(
        self,
        *,
        repo_summary: RepoSummary,
        plan: Plan,
        target_file: TargetFile,
        current_content: str,
        repair_error: str | None,
    ) -> str:
        relevant_schema_changes = [
            item.to_dict() if hasattr(item, "to_dict") else item.__dict__
            for item in plan.schema_changes
            if item.file == target_file.path
        ]
        prompt = (
            "Plan:\n"
            f"{json.dumps(plan.to_dict(), indent=2)}\n\n"
            "Repository stack and important files:\n"
            f"{json.dumps(repo_summary.to_dict(), indent=2)}\n\n"
            "Target file:\n"
            f"{json.dumps(target_file.__dict__, indent=2)}\n\n"
            "Schema changes directly mentioning this file:\n"
            f"{json.dumps(relevant_schema_changes, indent=2)}\n\n"
            "Current full file content:\n"
            "```text\n"
            f"{current_content}"
            "\n```"
        )
        if repair_error:
            prompt += (
                "\n\nThe previous generated content failed validation with this exact error:\n"
                f"{repair_error}\n"
                "Return a corrected complete file as JSON."
            )
        return prompt

    # Runs Node.js syntax check on generated JavaScript code and returns error if any
    def _syntax_error_if_any(self, patch: Patch) -> str | None:
        if not patch.path.endswith(".js"):
            return None
        check_path = self.syntax_dir / self._safe_name(patch.path)
        check_path.write_text(patch.full_content, encoding="utf-8")
        result = subprocess.run(
            ["node", "--check", str(check_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return None
        return (result.stderr or result.stdout or "node --check failed").strip()

    # Converts file path to a safe filename for temporary syntax check files
    def _safe_name(self, path: str) -> str:
        return path.replace("/", "__").replace("\\", "__")
