from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from core.config import STAGE_NAMES
from core.code_generator import CodeGenerator
from core.context_selector import ContextSelector
from core.llm_client import LLMClient
from core.patch_applier import PatchApplier
from core.planner import Planner
from core.repo_explorer import RepoExplorer
from core.validator import Validator
from core.summarizer import summarize


def parse_args() -> argparse.Namespace:
    # Parses command line arguments for repo path and user request
    parser = argparse.ArgumentParser(description="Single-pass AI coding agent")
    parser.add_argument("--repo-path", required=True, help="Path to the target git repository")
    parser.add_argument("--request", required=True, help="User request to implement")
    return parser.parse_args()


def main() -> int:
    # Main entry point: runs the complete agent pipeline (explore, select, plan, generate, apply, validate, summarize)
    args = parse_args()
    repo_path = Path(args.repo_path).resolve()
    run_dir = Path(__file__).resolve().parent / "runs" / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"Repo path: {repo_path}")
    print(f"Request: {args.request}")
    print(f"Run dir: {run_dir}")

    repo_summary = RepoExplorer().explore(repo_path)
    print(repo_summary.pretty())

    context_bundle = ContextSelector().select(repo_summary, args.request)
    print(context_bundle.pretty())

    validator = Validator()
    baseline_routes = validator.extract_routes_from_file(repo_path / "app" / "routes" / "note.routes.js")

    plan = Planner(LLMClient(run_dir=run_dir)).create_plan(
        request=args.request,
        repo_summary=repo_summary,
        context_bundle=context_bundle,
    )
    print(plan.pretty())

    patches = CodeGenerator(LLMClient(run_dir=run_dir), run_dir=run_dir).generate_patches(
        repo_path=repo_path,
        repo_summary=repo_summary,
        plan=plan,
    )
    for patch in patches:
        print(patch.pretty())

    application_result = PatchApplier(run_dir=run_dir).apply(
        repo_path=repo_path,
        plan=plan,
        patches=patches,
    )
    print(application_result.pretty())

    validation_report = validator.validate(
        repo_path=repo_path,
        patches=application_result.applied_patches,
        baseline_routes=baseline_routes,
    )
    print(validation_report.pretty())

    final_summary = summarize(
            repo_summary=repo_summary,
            plan=plan,
            patch_result=application_result,
            validation_report=validation_report,
            llm_provider_note=(
                "LLM provider was substituted from OpenAI/GPT-5.6 (per original spec) to "
                "Google Gemini free tier (model: gemini-flash-latest, reasoning_effort: high), "
                "since paid billing for OpenAI/DeepSeek was not available in this environment."
            ),
        )
    print(final_summary)

    summary_path = run_dir / "summary.md"
    summary_path.write_text(final_summary, encoding="utf-8")
    print(f"\nSummary saved to: {summary_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
