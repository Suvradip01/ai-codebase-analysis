from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from schemas.models import Patch, RouteSignature, ValidationCheck, ValidationReport


class Validator:
    # Regex pattern to extract Express route definitions from code
    ROUTE_PATTERN = re.compile(r"app\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]")

    # Runs all validation checks (syntax, dependencies, routes, lint, smoke) on the modified repository
    def validate(
        self,
        *,
        repo_path: Path,
        patches: list[Patch],
        baseline_routes: set[RouteSignature],
    ) -> ValidationReport:
        checks: list[ValidationCheck] = []
        checks.extend(self._syntax_checks(repo_path=repo_path, patches=patches))
        checks.append(self._dependency_check(repo_path=repo_path, patches=patches))
        checks.append(self._route_regression_check(repo_path=repo_path, baseline_routes=baseline_routes))
        checks.append(self._lint_check(repo_path=repo_path))
        checks.append(self._smoke_check(repo_path=repo_path))

        overall_status = "fail" if any(check.status == "fail" for check in checks) else "pass"
        return ValidationReport(checks=checks, overall_status=overall_status)

    # Extracts route signatures (method and path) from a routes file
    def extract_routes_from_file(self, route_file: Path) -> set[RouteSignature]:
        if not route_file.exists():
            return set()
        return self.extract_routes(route_file.read_text(encoding="utf-8", errors="replace"))

    # Parses route definitions from file content using regex
    def extract_routes(self, content: str) -> set[RouteSignature]:
        return {
            RouteSignature(method=method.upper(), path=path)
            for method, path in self.ROUTE_PATTERN.findall(content)
        }

    # Validates JavaScript syntax using Node.js --check for all modified JS files
    def _syntax_checks(self, *, repo_path: Path, patches: list[Patch]) -> list[ValidationCheck]:
        checks: list[ValidationCheck] = []
        js_patches = [patch for patch in patches if patch.applied and patch.path.endswith(".js")]
        if not js_patches:
            return [ValidationCheck("syntax", "skipped", "No modified JavaScript files.")]
        for patch in js_patches:
            result = subprocess.run(
                ["node", "--check", str(repo_path / patch.path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            details = (result.stderr or result.stdout or "syntax ok").strip()
            checks.append(
                ValidationCheck(
                    name=f"syntax: {patch.path}",
                    status="pass" if result.returncode == 0 else "fail",
                    details=details if result.returncode != 0 else "node --check passed",
                )
            )
        return checks

    # Validates that any new dependencies in package.json can be resolved via npm install
    def _dependency_check(self, *, repo_path: Path, patches: list[Patch]) -> ValidationCheck:
        package_patch = next((patch for patch in patches if patch.path == "package.json" and patch.applied), None)
        if not package_patch:
            return ValidationCheck("dependency validation", "pass", "No package.json dependency changes detected.")

        try:
            before = json.loads(package_patch.original_content or "{}").get("dependencies", {})
            after = json.loads((repo_path / "package.json").read_text(encoding="utf-8")).get("dependencies", {})
        except json.JSONDecodeError as exc:
            return ValidationCheck("dependency validation", "fail", f"package.json is invalid JSON: {exc}")

        added = sorted(set(after) - set(before))
        if not added:
            return ValidationCheck("dependency validation", "pass", "package.json changed but no dependencies were added.")

        missing = [name for name in added if not after.get(name)]
        if missing:
            return ValidationCheck("dependency validation", "fail", f"Added dependencies missing versions: {missing}")

        result = subprocess.run(
            ["npm", "install", "--dry-run"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return ValidationCheck("dependency validation", "pass", f"Added dependencies resolve: {', '.join(added)}")
        return ValidationCheck("dependency validation", "fail", (result.stderr or result.stdout).strip())

    # Ensures all existing routes are still present after modifications (no breaking changes)
    def _route_regression_check(self, *, repo_path: Path, baseline_routes: set[RouteSignature]) -> ValidationCheck:
        if not baseline_routes:
            return ValidationCheck("route regression", "skipped", "No baseline routes were available.")

        route_files = list((repo_path / "app" / "routes").glob("*.js"))
        current_routes: set[RouteSignature] = set()
        for route_file in route_files:
            current_routes.update(self.extract_routes_from_file(route_file))

        missing = sorted(baseline_routes - current_routes, key=lambda route: (route.method, route.path))
        if missing:
            details = ", ".join(f"{route.method} {route.path}" for route in missing)
            return ValidationCheck("route regression", "fail", f"Missing pre-existing routes: {details}")
        preserved = ", ".join(
            f"{route.method} {route.path}" for route in sorted(baseline_routes, key=lambda route: (route.method, route.path))
        )
        return ValidationCheck("route regression", "pass", f"All baseline routes preserved: {preserved}")

    # Runs ESLint if configuration is present in the repository
    def _lint_check(self, *, repo_path: Path) -> ValidationCheck:
        lint_files = [".eslintrc", ".eslintrc.js", ".eslintrc.json", "eslint.config.js"]
        if not any((repo_path / name).exists() for name in lint_files):
            return ValidationCheck("lint", "skipped", "No ESLint configuration found.")
        result = subprocess.run(
            ["npm", "run", "lint"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return ValidationCheck(
            "lint",
            "pass" if result.returncode == 0 else "fail",
            (result.stdout or result.stderr or "lint completed").strip(),
        )

    # Attempts to start the server briefly to check for runtime errors
    def _smoke_check(self, *, repo_path: Path) -> ValidationCheck:
        server_path = repo_path / "server.js"
        if not server_path.exists():
            return ValidationCheck("runtime smoke", "skipped", "No server.js entry point found.")

        process = subprocess.Popen(
            ["node", "server.js"],
            cwd=repo_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate(timeout=5)
            combined = f"{stdout}\n{stderr}".strip()
            if "Server is listening on port 3000" in combined:
                return ValidationCheck("runtime smoke", "pass", "Server started and listened on port 3000.")
            return ValidationCheck("runtime smoke", "pass", "Server stayed running without an immediate crash.")

        combined = f"{stdout}\n{stderr}".strip()
        if "Could not connect to the database" in combined:
            return ValidationCheck("runtime smoke", "skipped", "No local MongoDB detected; app reached DB connection step.")
        if "Server is listening on port 3000" in combined and "Error" not in combined:
            return ValidationCheck("runtime smoke", "pass", "Server listened on port 3000.")
        if process.returncode == 0:
            return ValidationCheck("runtime smoke", "pass", combined or "Server process exited cleanly.")
        return ValidationCheck("runtime smoke", "fail", combined or f"Server exited with code {process.returncode}.")
