from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(path: Path) -> None:  # type: ignore[no-redef]
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

PROMPTS_DIR = PROJECT_ROOT / "prompts"
RUNS_DIR = PROJECT_ROOT / "runs"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("LLM_API_KEY")
GEMINI_BASE_URL = (
    os.getenv("GEMINI_BASE_URL")
    or os.getenv("OPENAI_BASE_URL")
    or os.getenv("LLM_BASE_URL")
    or "https://generativelanguage.googleapis.com/v1beta/openai/"
)
GEMINI_MODEL = os.getenv("GEMINI_MODEL") or os.getenv("OPENAI_MODEL") or os.getenv("LLM_MODEL") or "gemini-flash-latest"
REASONING_EFFORT = os.getenv("REASONING_EFFORT") or "high"

OPENAI_API_KEY = GEMINI_API_KEY
OPENAI_BASE_URL = GEMINI_BASE_URL
OPENAI_MODEL = GEMINI_MODEL

IGNORED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "coverage",
    ".next",
    "__pycache__",
}

IGNORED_FILES = {
    "package-lock.json",
    "yarn.lock",
}

TOP_K_CONTEXT_FILES = 8
MAX_CONTEXT_TOKENS = 6000

STAGE_NAMES = [
    "RepoExplorer",
    "ContextSelector",
    "Planner",
    "CodeGenerator",
    "PatchApplier",
    "Validator",
    "Summarizer",
]
