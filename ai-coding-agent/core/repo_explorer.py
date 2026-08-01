from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from core.config import IGNORED_DIRS, IGNORED_FILES
from schemas.models import ImportantFile, RepoSummary


SOURCE_EXTENSIONS = {".js", ".ts", ".py", ".java", ".rb", ".go", ".php"}
FRAMEWORKS = {
    "express": "Express",
    "mongoose": "Mongoose",
}


class RepoExplorer:
    # Analyzes the repository structure and returns a summary with important files, stack, and dependencies
    def explore(self, repo_path: Path) -> RepoSummary:
        root = repo_path.resolve()
        if not root.exists() or not root.is_dir():
            raise FileNotFoundError(f"Repository path is not a readable directory: {root}")

        files = self._walk(root)
        package_json_paths = [path for path in files if path.name == "package.json"]
        assumptions: list[str] = []

        package_data: dict[str, Any] = {}
        package_path: Path | None = None
        if package_json_paths:
            package_path = min(package_json_paths, key=lambda path: len(path.relative_to(root).parts))
            if len(package_json_paths) > 1:
                assumptions.append(
                    f"Multiple package.json files found; using {self._rel(root, package_path)}."
                )
            package_data = self._read_json(package_path)

        dependencies = package_data.get("dependencies", {}) if package_data else {}
        entry_point = package_data.get("main") if package_data else None
        stack = self._detect_stack(root, package_data, dependencies)

        important_files = self._discover_important_files(root, files, package_path, entry_point)
        if not important_files:
            assumptions.append(
                "Expected framework conventions were not found; falling back to ranked source files."
            )
            important_files = self._fallback_important_files(root, files)

        file_tree = "\n".join(self._rel(root, path) for path in files)
        return RepoSummary(
            repo_path=str(root),
            stack=stack,
            file_tree=file_tree,
            files=[self._rel(root, path) for path in files],
            important_files=important_files,
            dependencies=dict(dependencies),
            entry_point=entry_point,
            assumptions=assumptions,
        )

    # Recursively walks the directory tree and returns all files, excluding ignored directories and files
    def _walk(self, root: Path) -> list[Path]:
        results: list[Path] = []
        for path in root.rglob("*"):
            relative_parts = path.relative_to(root).parts
            if any(part in IGNORED_DIRS for part in relative_parts):
                continue
            if path.is_file() and path.name not in IGNORED_FILES:
                results.append(path)
        return sorted(results, key=lambda item: self._rel(root, item))

    # Reads and parses a JSON file, returning its contents as a dictionary
    def _read_json(self, path: Path) -> dict[str, Any]:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Could not parse {path}: {exc}") from exc

    # Detects the technology stack (Node.js, Express, Mongoose) from package.json and directory structure
    def _detect_stack(self, root: Path, package_data: dict[str, Any], dependencies: dict[str, str]) -> str:
        if not package_data:
            return "Unknown stack"

        framework_names = [label for key, label in FRAMEWORKS.items() if key in dependencies]
        has_frontend = any((root / name).exists() for name in ["public", "views"]) or any(
            (root / name).exists()
            for name in ["vite.config.js", "webpack.config.js", "next.config.js"]
        )

        parts = ["Node.js"]
        if "Express" in framework_names:
            parts.append("Express")
        if "Mongoose" in framework_names:
            parts.append("Mongoose")
        api_kind = "REST API"
        frontend = "frontend present" if has_frontend else "no frontend"
        return " / ".join(parts) + f", {api_kind}, {frontend}"

    # Identifies important files based on framework conventions (models, controllers, routes, config)
    def _discover_important_files(
        self,
        root: Path,
        files: list[Path],
        package_path: Path | None,
        entry_point: str | None,
    ) -> list[ImportantFile]:
        important: dict[str, ImportantFile] = {}

        if package_path:
            relative = self._rel(root, package_path)
            important[relative] = ImportantFile(
                path=relative,
                role="package",
                description="Package metadata, scripts, dependency list, and Node entry point.",
            )

        if entry_point:
            candidate = root / entry_point
            if candidate.exists() and candidate.is_file():
                relative = self._rel(root, candidate)
                important[relative] = ImportantFile(
                    path=relative,
                    role="entry",
                    description="Application entry point and Express/server bootstrap.",
                )

        for path in files:
            relative = self._rel(root, path)
            parts = path.relative_to(root).parts
            if "config" in parts:
                important[relative] = ImportantFile(
                    path=relative,
                    role="config",
                    description="Configuration file used by the application.",
                )
            elif "models" in parts:
                important[relative] = ImportantFile(
                    path=relative,
                    role="model",
                    description=self._describe_model(path),
                )
            elif "controllers" in parts:
                important[relative] = ImportantFile(
                    path=relative,
                    role="controller",
                    description=self._describe_controller(path),
                )
            elif "routes" in parts:
                important[relative] = ImportantFile(
                    path=relative,
                    role="routes",
                    description=self._describe_routes(path),
                )

        return [important[key] for key in sorted(important)]

    # Fallback method: ranks source files by size when framework conventions aren't found
    def _fallback_important_files(self, root: Path, files: list[Path]) -> list[ImportantFile]:
        source_files = [path for path in files if path.suffix in SOURCE_EXTENSIONS]
        source_files.sort(key=lambda path: (path.stat().st_size, self._rel(root, path)))
        return [
            ImportantFile(
                path=self._rel(root, path),
                role="source",
                description="Source file selected by fallback scan.",
            )
            for path in source_files[:8]
        ]

    # Parses a Mongoose model file to extract field names and types for description
    def _describe_model(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8", errors="replace")
        fields = []
        # Track consumed character spans to skip nested object properties
        consumed_spans = []
        
        for match in re.finditer(r"^\s*(\w+)\s*:\s*([^,\n]+)", text, flags=re.MULTILINE):
            name = match.group(1)
            value = match.group(2).strip()
            
            # Skip timestamps
            if name == "timestamps":
                continue
            
            # Skip if this match is inside a previously consumed span
            if any(span[0] <= match.start() <= span[1] for span in consumed_spans):
                continue
            
            # Check if this is the start of a nested object
            if value.startswith("{"):
                # Find the closing brace for this nested object
                nested_start = match.start()
                nested_end = text.find("}", nested_start)
                if nested_end != -1:
                    # Mark this span as consumed
                    consumed_spans.append((nested_start, nested_end))
                    # Extract type from the nested object
                    type_match = re.search(r"type\s*:\s*(\w+)", text[nested_start:nested_end])
                    if type_match:
                        field_type = type_match.group(1)
                        # Check for default value
                        default_match = re.search(r"default\s*:\s*['\"]([^'\"]+)['\"]", text[nested_start:nested_end])
                        if default_match:
                            kind = f"{field_type}, default: '{default_match.group(1)}'"
                        else:
                            kind = field_type
                        fields.append((name, kind))
                    else:
                        # Fallback if type not found
                        fields.append((name, "{...}"))
                else:
                    # No closing brace found, treat as simple field
                    value = value.rstrip(",")
                    fields.append((name, value))
            else:
                # Simple field like title: String
                # Remove trailing commas if present
                value = value.rstrip(",")
                fields.append((name, value))
        
        field_text = ", ".join(f"{name} ({kind.strip()})" for name, kind in fields)
        suffix = f" fields: {field_text}" if field_text else ""
        if "timestamps" in text:
            suffix += ", timestamps"
        return f"Mongoose schema -{suffix}" if suffix else "Mongoose schema."

    # Extracts exported function names from a controller file for description
    def _describe_controller(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8", errors="replace")
        exports = re.findall(r"exports\.(\w+)\s*=", text)
        return "Controller/business logic exports: " + ", ".join(exports) if exports else "Controller/business logic."

    # Extracts Express route definitions (method and path) from a routes file
    def _describe_routes(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8", errors="replace")
        routes = re.findall(r"app\.(get|post|put|delete|patch)\(['\"]([^'\"]+)['\"]", text)
        route_text = ", ".join(f"{method.upper()} {route}" for method, route in routes)
        return "Express route registrations: " + route_text if route_text else "Express route registrations."

    # Returns the relative path from root to the given path, using forward slashes
    def _rel(self, root: Path, path: Path) -> str:
        return path.relative_to(root).as_posix()
