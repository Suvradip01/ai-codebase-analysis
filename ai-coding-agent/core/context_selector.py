from __future__ import annotations

import re
from pathlib import Path

from core.config import MAX_CONTEXT_TOKENS, TOP_K_CONTEXT_FILES
from schemas.models import ContextBundle, FileContext, ImportantFile, RepoSummary


ROLE_BONUSES = {
    "model": 44.0,
    "controller": 38.0,
    "routes": 36.0,
    "entry": 8.0,
    "package": 2.0,
    "config": 1.0,
    "source": 8.0,
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "application",
    "as",
    "be",
    "better",
    "can",
    "for",
    "in",
    "of",
    "so",
    "the",
    "their",
    "to",
    "users",
    "with",
}


class ContextSelector:
    # Selects and ranks relevant files from the repo based on the user request using keyword matching and role bonuses
    def select(self, repo_summary: RepoSummary, request: str) -> ContextBundle:
        root = Path(repo_summary.repo_path)
        request_tokens = self._tokens(request)
        ranked: list[FileContext] = []

        for important_file in repo_summary.important_files:
            file_path = root / important_file.path
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            score, reason = self._score_file(
                important_file=important_file,
                content=content,
                request_tokens=request_tokens,
                entry_point=repo_summary.entry_point,
            )
            estimated_tokens = max(1, len(content) // 4)
            ranked.append(
                FileContext(
                    path=important_file.path,
                    content=content,
                    score=score,
                    reason=reason,
                    estimated_tokens=estimated_tokens,
                )
            )

        if not ranked:
            ranked = self._fallback_rank(root, repo_summary, request_tokens)

        ranked.sort(key=lambda item: (-item.score, item.estimated_tokens, item.path))
        selected = ranked[:TOP_K_CONTEXT_FILES]
        selected = self._enforce_token_budget(selected)
        return ContextBundle(
            files=selected,
            total_estimated_tokens=sum(item.estimated_tokens for item in selected),
        )

    # Scores a file's relevance based on role, keyword overlap with request, entry point status, and size
    def _score_file(
        self,
        important_file: ImportantFile,
        content: str,
        request_tokens: set[str],
        entry_point: str | None,
    ) -> tuple[float, str]:
        role_bonus = ROLE_BONUSES.get(important_file.role, 0.0)
        candidate_tokens = self._tokens(important_file.path)
        candidate_tokens.update(self._tokens(important_file.description))
        candidate_tokens.update(self._extract_identifiers(content))
        overlap = request_tokens & candidate_tokens
        keyword_score = float(len(overlap) * 8)

        entry_bonus = 0.0
        if important_file.path == entry_point or important_file.role == "routes":
            entry_bonus = 6.0

        size_penalty = min(len(content) / 20000.0, 5.0)
        score = role_bonus + keyword_score + entry_bonus - size_penalty
        reason = (
            f"role={important_file.role} (+{role_bonus:g}); "
            f"keyword_overlap={sorted(overlap) or []} (+{keyword_score:g}); "
            f"entry_bonus=+{entry_bonus:g}; size_penalty=-{size_penalty:.2f}"
        )
        return score, reason

    # Fallback ranking method when no important files are found, using keyword overlap on all source files
    def _fallback_rank(
        self,
        root: Path,
        repo_summary: RepoSummary,
        request_tokens: set[str],
    ) -> list[FileContext]:
        ranked: list[FileContext] = []
        for relative in repo_summary.files:
            path = root / relative
            if path.suffix not in {".js", ".ts", ".py", ".java", ".rb", ".go", ".php"}:
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            candidate_tokens = self._tokens(relative) | self._extract_identifiers(content)
            overlap = request_tokens & candidate_tokens
            estimated_tokens = max(1, len(content) // 4)
            score = len(overlap) * 8 - min(len(content) / 20000.0, 5.0)
            ranked.append(
                FileContext(
                    path=relative,
                    content=content,
                    score=score,
                    reason=f"fallback keyword_overlap={sorted(overlap) or []}",
                    estimated_tokens=estimated_tokens,
                )
            )
        return ranked

    # Ensures selected files don't exceed the maximum token budget for LLM context
    def _enforce_token_budget(self, selected: list[FileContext]) -> list[FileContext]:
        kept: list[FileContext] = []
        total = 0
        for item in selected:
            if total + item.estimated_tokens > MAX_CONTEXT_TOKENS and kept:
                continue
            kept.append(item)
            total += item.estimated_tokens
        return kept

    # Tokenizes text into normalized words, removing stopwords and handling singular/plural variants
    def _tokens(self, text: str) -> set[str]:
        raw_tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9]*", text.lower())
        normalized: set[str] = set()
        for token in raw_tokens:
            if token in STOPWORDS:
                continue
            normalized.add(token)
            if token.endswith("s") and len(token) > 3:
                normalized.add(token[:-1])
            if token == "organise":
                normalized.add("organize")
            if token == "organize":
                normalized.add("organise")
        return normalized

    # Extracts code identifiers and route paths from file content for keyword matching
    def _extract_identifiers(self, content: str) -> set[str]:
        identifiers = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", content))
        routes = re.findall(r"['\"](/[A-Za-z0-9_:/-]+)['\"]", content)
        tokens: set[str] = set()
        for item in identifiers:
            tokens.update(self._tokens(item))
        for route in routes:
            tokens.update(self._tokens(route))
        return tokens
