from __future__ import annotations

from schemas.models import Plan, Patch, PatchApplicationResult, ValidationReport, RepoSummary


def _example_curl_calls(plan: Plan) -> str:
    # Generates example curl commands from the plan's API changes for documentation
    """Generate example curl commands from the Plan's api_changes, best-effort."""
    if not plan.api_changes:
        return "  (no new API endpoints to demonstrate)"

    lines = []
    for change in plan.api_changes:
        method = change.method.upper()
        path = change.path
        if method in ("POST", "PUT", "PATCH"):
            lines.append(
                f'  curl -X {method} http://localhost:3000{path} '
                f'-H "Content-Type: application/json" -d \'{{"title":"Groceries","content":"Milk, eggs","tags":["home"]}}\''
            )
        else:
            lines.append(f"  curl http://localhost:3000{path}")
    return "\n".join(lines)


def summarize(
    # Assembles a Markdown summary from the plan, patch result, and validation report
    repo_summary: RepoSummary,
    plan: Plan,
    patch_result: PatchApplicationResult,
    validation_report: ValidationReport,
    *,
    llm_provider_note: str | None = None,
) -> str:
    """
    Assemble the final Markdown summary from structured facts produced by
    earlier pipeline stages. Never invents new facts -- everything here is
    pulled directly from RepoSummary, Plan, PatchApplicationResult, and
    ValidationReport (spec Section 11).
    """
    sections: list[str] = []

    # --- Header ---
    sections.append(f"# AI Coding Agent — Run Summary\n")
    sections.append(f"**Feature implemented:** {plan.feature_name}\n")

    # --- Execution plan ---
    sections.append("## Execution Plan")
    sections.append(f"{plan.rationale}\n")
    sections.append(f"**User-facing behavior:** {plan.user_facing_behavior}\n")

    if plan.schema_changes:
        sections.append("**Schema changes:**")
        for sc in plan.schema_changes:
            sections.append(f"- `{sc.file}`: {sc.description}")
        sections.append("")

    if plan.api_changes:
        sections.append("**API changes:**")
        for ac in plan.api_changes:
            sections.append(f"- `{ac.method} {ac.path}`: {ac.description}")
        sections.append("")

    # --- Files explored ---
    sections.append("## Files Explored")
    sections.append(f"Detected stack: **{repo_summary.stack}**\n")
    sections.append("The following files were identified as relevant during repository exploration:")
    for f in repo_summary.important_files:
        sections.append(f"- `{f.path}` ({f.role}): {f.description}")
    sections.append("")

    # --- Files modified ---
    sections.append("## Files Modified")
    for patch in patch_result.applied_patches:
        status = "✅ applied" if patch.applied else f"❌ not applied ({patch.error or 'unknown error'})"
        sections.append(f"- `{patch.path}` ({patch.action}) — {status}")
        sections.append(f"  - {patch.change_summary}")
    sections.append("")
    sections.append(f"**Git commit:** `{patch_result.commit_hash or 'not created'}`")
    sections.append(f"**Backups:** `{patch_result.backup_dir}`")
    sections.append(f"**Diff:** `{patch_result.git_diff_path}`\n")

    # --- Example requests ---
    sections.append("## Example Requests")
    sections.append(_example_curl_calls(plan))
    sections.append("")

    # --- Validation performed ---
    sections.append("## Validation Performed")
    sections.append(f"**Overall status:** `{validation_report.overall_status}`\n")
    for check in validation_report.checks:
        icon = {"pass": "✅", "fail": "❌", "skipped": "⏭️"}.get(check.status, "•")
        sections.append(f"- {icon} **{check.name}**: {check.status} — {check.details}")
    sections.append("")

    # --- Assumptions ---
    sections.append("## Assumptions")
    all_assumptions = list(plan.assumptions)
    if llm_provider_note:
        all_assumptions.append(llm_provider_note)
    for a in all_assumptions:
        sections.append(f"- {a}")
    if not all_assumptions:
        sections.append("- none")
    sections.append("")

    # --- Next steps ---
    sections.append("## Next Steps")
    if plan.out_of_scope:
        for item in plan.out_of_scope:
            sections.append(f"- {item}")
    else:
        sections.append("- none identified")

    if patch_result.errors:
        sections.append("")
        sections.append("## Errors Encountered")
        for error in patch_result.errors:
            sections.append(f"- {error}")

    return "\n".join(sections)