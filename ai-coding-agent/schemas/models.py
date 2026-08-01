from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ImportantFile:
    path: str
    role: str
    description: str


@dataclass
class RepoSummary:
    repo_path: str
    stack: str
    file_tree: str
    files: list[str]
    important_files: list[ImportantFile]
    dependencies: dict[str, str] = field(default_factory=dict)
    entry_point: str | None = None
    assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def pretty(self) -> str:
        important = "\n".join(
            f"  - {item.path}: {item.description}" for item in self.important_files
        )
        deps = ", ".join(f"{name}@{version}" for name, version in self.dependencies.items())
        assumptions = "\n".join(f"  - {item}" for item in self.assumptions) or "  - none"
        return (
            "RepoSummary\n"
            f"Stack: {self.stack}\n"
            f"Entry point: {self.entry_point or 'unknown'}\n"
            f"Dependencies: {deps or 'none'}\n"
            "File tree:\n"
            f"{self.file_tree}\n"
            "Important files:\n"
            f"{important or '  - none'}\n"
            "Assumptions:\n"
            f"{assumptions}"
        )


@dataclass
class FileContext:
    path: str
    content: str
    score: float
    reason: str
    estimated_tokens: int


@dataclass
class ContextBundle:
    files: list[FileContext]
    total_estimated_tokens: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def pretty(self) -> str:
        lines = [
            "ContextBundle",
            f"Total estimated tokens: {self.total_estimated_tokens}",
            "Ranked files:",
        ]
        for item in self.files:
            lines.append(
                f"  - {item.path}: score={item.score:.2f}, tokens={item.estimated_tokens}, {item.reason}"
            )
        return "\n".join(lines)


@dataclass
class SchemaChange:
    file: str
    description: str


@dataclass
class ApiChange:
    method: str
    path: str
    description: str


@dataclass
class TargetFile:
    path: str
    action: str
    reason: str


@dataclass
class Plan:
    feature_name: str
    rationale: str
    user_facing_behavior: str
    schema_changes: list[SchemaChange]
    api_changes: list[ApiChange]
    target_files: list[TargetFile]
    out_of_scope: list[str]
    assumptions: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any], known_files: set[str]) -> "Plan":
        required = [
            "feature_name",
            "rationale",
            "user_facing_behavior",
            "schema_changes",
            "api_changes",
            "target_files",
            "out_of_scope",
            "assumptions",
        ]
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError(f"Plan is missing required keys: {missing}")

        target_files = [
            TargetFile(
                path=self_data["path"],
                action=self_data["action"],
                reason=self_data["reason"],
            )
            for self_data in data["target_files"]
        ]
        if not target_files:
            raise ValueError("Plan.target_files must not be empty")

        for target_file in target_files:
            if target_file.action not in {"modify", "create"}:
                raise ValueError(f"Invalid target file action for {target_file.path}: {target_file.action}")
            if target_file.action != "create" and target_file.path not in known_files:
                raise ValueError(f"Target file does not exist in repo summary: {target_file.path}")

        api_changes = [
            ApiChange(
                method=item["method"],
                path=item["path"],
                description=item["description"],
            )
            for item in data["api_changes"]
        ]
        for api_change in api_changes:
            if api_change.method not in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
                raise ValueError(f"Invalid API method: {api_change.method}")

        if api_changes:
            known_route_files = {path for path in known_files if "/routes/" in path or path.startswith("routes/")}
            if known_route_files and not any(
                target.path in known_route_files for target in target_files
            ):
                raise ValueError(
                    "Plan has API changes but does not include a routes file in target_files."
                )

        return cls(
            feature_name=str(data["feature_name"]),
            rationale=str(data["rationale"]),
            user_facing_behavior=str(data["user_facing_behavior"]),
            schema_changes=[
                SchemaChange(file=item["file"], description=item["description"])
                for item in data["schema_changes"]
            ],
            api_changes=api_changes,
            target_files=target_files,
            out_of_scope=[str(item) for item in data["out_of_scope"]],
            assumptions=[str(item) for item in data["assumptions"]],
        )

    def pretty(self) -> str:
        target_lines = "\n".join(
            f"  - {item.path} ({item.action}): {item.reason}" for item in self.target_files
        )
        schema_lines = "\n".join(
            f"  - {item.file}: {item.description}" for item in self.schema_changes
        ) or "  - none"
        api_lines = "\n".join(
            f"  - {item.method} {item.path}: {item.description}" for item in self.api_changes
        ) or "  - none"
        assumptions = "\n".join(f"  - {item}" for item in self.assumptions) or "  - none"
        return (
            "Plan\n"
            f"Feature: {self.feature_name}\n"
            f"Rationale: {self.rationale}\n"
            f"User-facing behavior: {self.user_facing_behavior}\n"
            "Schema changes:\n"
            f"{schema_lines}\n"
            "API changes:\n"
            f"{api_lines}\n"
            "Target files:\n"
            f"{target_lines}\n"
            "Assumptions:\n"
            f"{assumptions}"
        )


@dataclass
class Patch:
    path: str
    action: str
    full_content: str
    change_summary: str
    original_content: str = ""
    applied: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        expected_path: str,
        expected_action: str,
        original_content: str,
    ) -> "Patch":
        required = ["path", "action", "full_content", "change_summary"]
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError(f"Patch is missing required keys: {missing}")
        if data["path"] != expected_path:
            raise ValueError(f"Patch path {data['path']} does not match expected {expected_path}")
        if data["action"] != expected_action:
            raise ValueError(f"Patch action {data['action']} does not match expected {expected_action}")
        full_content = str(data["full_content"])
        if not full_content.strip():
            raise ValueError(f"Patch for {expected_path} has empty full_content")
        return cls(
            path=str(data["path"]),
            action=str(data["action"]),
            full_content=full_content,
            change_summary=str(data["change_summary"]),
            original_content=original_content,
        )

    def pretty(self) -> str:
        status = "applied" if self.applied else "generated"
        if self.error:
            status = f"error: {self.error}"
        return f"Patch {self.path} ({self.action}, {status}): {self.change_summary}"


@dataclass
class PatchApplicationResult:
    applied_patches: list[Patch]
    backup_dir: str
    git_diff_path: str
    commit_hash: str | None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def pretty(self) -> str:
        lines = [
            "PatchApplicationResult",
            f"Backup dir: {self.backup_dir}",
            f"Git diff: {self.git_diff_path}",
            f"Commit: {self.commit_hash or 'not created'}",
            "Applied patches:",
        ]
        for patch in self.applied_patches:
            lines.append(f"  - {patch.path}: applied={patch.applied}, error={patch.error or 'none'}")
        if self.errors:
            lines.append("Errors:")
            lines.extend(f"  - {error}" for error in self.errors)
        return "\n".join(lines)


@dataclass(frozen=True)
class RouteSignature:
    method: str
    path: str


@dataclass
class ValidationCheck:
    name: str
    status: str
    details: str


@dataclass
class ValidationReport:
    checks: list[ValidationCheck]
    overall_status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def pretty(self) -> str:
        lines = ["ValidationReport", f"Overall status: {self.overall_status}", "Checks:"]
        for check in self.checks:
            lines.append(f"  - {check.name}: {check.status} - {check.details}")
        return "\n".join(lines)
