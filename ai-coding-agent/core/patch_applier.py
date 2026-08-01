from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from schemas.models import Patch, PatchApplicationResult, Plan


class PatchApplier:
    # Initializes the patch applier with a backup directory for safe file modifications
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.backup_dir = run_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    # Applies all patches to the repository, creates backups, and commits changes via git
    def apply(self, *, repo_path: Path, plan: Plan, patches: list[Patch]) -> PatchApplicationResult:
        applied: list[Patch] = []
        errors: list[str] = []

        for patch in patches:
            try:
                self._apply_one(repo_path=repo_path, patch=patch)
                patch.applied = True
            except OSError as exc:
                patch.error = f"I/O error: {exc}"
                errors.append(f"{patch.path}: {patch.error}")
                self._restore_backup(repo_path=repo_path, patch=patch)
            except ValueError as exc:
                patch.error = str(exc)
                errors.append(f"{patch.path}: {patch.error}")
            applied.append(patch)

        git_diff_path = self.run_dir / "git_diff.patch"
        git_diff = self._run_git(repo_path, ["diff"], check=False).stdout
        git_diff_path.write_text(git_diff, encoding="utf-8")

        commit_hash: str | None = None
        if any(patch.applied for patch in applied) and not errors:
            self._run_git(repo_path, ["add", "-A"], check=True)
            message = self._commit_message(plan=plan, patches=applied)
            self._run_git(repo_path, ["commit", "-m", message], check=True)
            commit_hash = self._run_git(repo_path, ["rev-parse", "HEAD"], check=True).stdout.strip()

        return PatchApplicationResult(
            applied_patches=applied,
            backup_dir=str(self.backup_dir),
            git_diff_path=str(git_diff_path),
            commit_hash=commit_hash,
            errors=errors,
        )

    # Applies a single patch to a file with safety checks and backup creation
    def _apply_one(self, *, repo_path: Path, patch: Patch) -> None:
        target_path = repo_path / patch.path
        if patch.action == "modify":
            if not target_path.exists():
                raise ValueError(f"Cannot modify missing file: {patch.path}")
            current_content = target_path.read_text(encoding="utf-8", errors="replace")
            if current_content != patch.original_content:
                raise ValueError("File changed since context selection; refusing to overwrite.")
            backup_path = self.backup_dir / patch.path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target_path, backup_path)
        elif patch.action == "create":
            if target_path.exists():
                current_content = target_path.read_text(encoding="utf-8", errors="replace")
                if current_content != patch.original_content:
                    raise ValueError("Create target already exists with unexpected content.")
            backup_path = self.backup_dir / patch.path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            backup_path.write_text(patch.original_content, encoding="utf-8")
        else:
            raise ValueError(f"Unsupported patch action: {patch.action}")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(patch.full_content, encoding="utf-8")

    # Restores a file from backup if patch application fails
    def _restore_backup(self, *, repo_path: Path, patch: Patch) -> None:
        backup_path = self.backup_dir / patch.path
        target_path = repo_path / patch.path
        if backup_path.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup_path, target_path)

    # Runs a git command in the repository and returns the result
    def _run_git(self, repo_path: Path, args: list[str], *, check: bool) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if check and result.returncode != 0:
            raise RuntimeError(
                f"git {' '.join(args)} failed with exit {result.returncode}: "
                f"{result.stderr or result.stdout}"
            )
        return result

    # Generates a git commit message based on the plan and modified files
    def _commit_message(self, *, plan: Plan, patches: list[Patch]) -> str:
        changed = ", ".join(patch.path for patch in patches if patch.applied)
        return f"{plan.feature_name}: update {changed}"
