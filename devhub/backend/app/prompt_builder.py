from .models import Project, Release


def _phase_label(phase: dict | None) -> str:
    if not phase:
        return "Unknown"
    return f"{phase.get('version') or ''} {phase.get('title') or ''}".strip() or "Unknown"


def build_release_prompt(project: Project, release: Release, roadmap_text: str | None, changelog_text: str | None, roadmap_context: dict | None = None) -> str:
    items = [link.item for link in release.scope]
    ctx = roadmap_context or {}
    current = ctx.get("current")
    next_phase = ctx.get("next")
    selected_phase = ctx.get("selected_release_phase")
    reconciliation = ctx.get("reconciliation") or {}
    changelog = ctx.get("changelog") or {}
    lines = [
        f"Act as the lead developer for {project.name}.",
        "",
        f"Repository: `{project.github_owner}/{project.github_repo}`",
        f"Default branch: `{project.default_branch}`",
        f"Roadmap: `{project.roadmap_path}`",
        f"Changelog: `{project.changelog_path}`",
        "",
        "Use the latest merged main/default branch as the authoritative starting point. Do not assume repository state or version numbers in advance.",
        "",
        "DevHub release context:",
        f"- Current detected release: {ctx.get('detected_release') or 'Unknown'}",
        f"- Version source: {ctx.get('version_source') or 'Unknown'}",
        f"- Current roadmap phase: {_phase_label(current)} ({ctx.get('current_source') or 'Detected'})",
        f"- Next roadmap phase: {_phase_label(next_phase)} ({ctx.get('next_source') or 'Detected'})",
        f"- Selected release roadmap phase: {_phase_label(selected_phase)}",
        f"- Roadmap parse status: {ctx.get('parse_status') or 'Unknown'}",
        f"- Roadmap reconciliation: {reconciliation.get('status') or 'Unknown'}",
        f"- Changelog state: {changelog.get('status') or 'Unknown'}",
        "",
        "Before making changes:",
        "1. Inspect the latest merged branch state, current release/development version, latest releases/tags, recent merged PRs, open PRs and CI.",
        f"2. Read `{project.roadmap_path}` and `{project.changelog_path}` as authoritative Markdown documents.",
        "3. If this is a Home Assistant app/add-on repository, also inspect the packaged Home Assistant changelog (normally the add-on-local `CHANGELOG.md` beside `config.yaml`).",
        "4. Inspect all authoritative version locations used by this repository and reconcile them before release, including Home Assistant config, frontend package metadata, backend application version and health/version endpoints where present.",
        "5. Use the focused structured roadmap context below where reliable, but retain uncertainty when mapping free-form roadmap bullets to implementation.",
        "6. Preserve existing functionality and avoid regressions.",
        "",
        "Selected DevHub release scope:",
    ]
    for item in items:
        phase_label = f"{item.roadmap_phase.version or ''} {item.roadmap_phase.title}".strip() if item.roadmap_phase else "Unassigned"
        lines += ["", f"## {item.item_key} | {item.item_type} | {item.priority}", item.title, "", f"Roadmap phase: {phase_label}", f"Target release: {item.target_release or 'Not set'}", f"Description: {item.description or 'Not provided'}", "Acceptance criteria:"]
        lines += [f"- {criterion.description}" for criterion in item.criteria] or ["- No explicit criteria recorded. Define appropriate measurable criteria before implementation."]
        lines += ["Testing instructions:", item.testing_instructions or "Define and execute practical verification steps for this item."]

    if selected_phase:
        lines += ["", "Relevant selected roadmap phase items:"]
        lines += [f"- {'[x]' if i.get('completed') else '[ ]'} {i.get('text')}" for i in selected_phase.get("items", [])] or ["- No parsed roadmap items in the selected phase."]
    if reconciliation.get("reasons"):
        lines += ["", "Known reconciliation warnings/context:"] + [f"- {reason}" for reason in reconciliation["reasons"]]

    lines += [
        "",
        "Implementation and release requirements:",
        "- Implement only the selected scope and keep the release focused.",
        "- Do not automatically select additional scope.",
        "- Create or update automated tests and run the complete relevant suite.",
        "- Determine the semantic version from the actual repository state and delivered scope.",
        "- Reconcile all authoritative version locations so they agree before merge; do not leave the Home Assistant manifest, frontend package, backend version or health/version endpoint on different releases where those locations exist.",
        "- Reconcile ROADMAP.md after implementation, marking only genuinely delivered work complete and carrying unfinished items forward.",
        "- Reconcile the repository-level CHANGELOG.md so the latest documented version matches the actual release and contains accurate user-facing release notes.",
        "- For Home Assistant app/add-on repositories, update the packaged add-on-local CHANGELOG.md beside config.yaml for every release so Home Assistant displays the release notes to users.",
        "- Keep the Home Assistant changelog concise and user-facing, while the repository-level changelog may contain fuller technical detail.",
        "- Never rewrite roadmap or changelog scope merely to make reconciliation appear clean.",
        "- Keep release record, roadmap association, changelog and GitHub version evidence consistent.",
        "- Create a focused branch and PR. Do not create a separate GitHub Issue unless explicitly requested.",
        "- Do not merge while any required CI check is failing.",
        "- Before merge, ensure CI verifies the release version consistently across required metadata and verifies both repository and Home Assistant changelogs when applicable.",
        "- After merge, inspect post-merge CI before considering the release complete.",
        "- After successful post-merge CI, verify the semantic Git tag and GitHub Release state for the released version.",
        "- Create or update the GitHub Release/tag for the released version when tooling and permissions allow, using the exact released commit as appropriate.",
        "- Use the final repository changelog entry as the basis for GitHub Release notes, edited into a concise user-facing summary rather than leaving the GitHub Release blank.",
        "- If GitHub Release or tag creation is not possible with the available tooling, report that explicitly instead of claiming publication succeeded.",
    ]
    return "\n".join(lines)
