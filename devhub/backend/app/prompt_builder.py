from .models import Project, Release


def build_release_prompt(project: Project, release: Release, roadmap_text: str | None, changelog_text: str | None, roadmap_context: dict | None = None) -> str:
    items = [link.item for link in release.scope]
    roadmap_context = roadmap_context or {}
    current = roadmap_context.get("current")
    next_phase = roadmap_context.get("next")
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
        "Roadmap intelligence:",
        f"- Parse status: {roadmap_context.get('parse_status', 'Unknown')}",
        f"- Current phase: {((current or {}).get('version') or '')} {((current or {}).get('title') or 'Unknown')}`".replace('`',''),
        f"- Next phase: {((next_phase or {}).get('version') or '')} {((next_phase or {}).get('title') or 'Unknown')}`".replace('`',''),
        "",
        "Before making changes:",
        "1. Inspect the latest merged branch state, current release/development version, latest releases, recent merged PRs and currently open PRs.",
        "2. Review the existing architecture, relevant integrations, tests and CI.",
        f"3. Read the configured roadmap at `{project.roadmap_path}` and changelog at `{project.changelog_path}`.",
        "4. Use the structured roadmap context below where reliable and retain uncertainty when the parser reports ambiguity.",
        "5. Map every approved DevHub item below to the current/next roadmap phase and identify affected sequencing.",
        "6. Preserve existing functionality and avoid regressions.",
        "",
        "Approved DevHub release scope:",
    ]
    for item in items:
        phase_label = "Unassigned"
        if item.roadmap_phase:
            phase_label = f"{item.roadmap_phase.version or ''} {item.roadmap_phase.title}".strip()
        lines += [
            "",
            f"## {item.item_key} | {item.item_type} | {item.priority}",
            item.title,
            "",
            f"Roadmap phase: {phase_label}",
            f"Target release: {item.target_release or 'Not set'}",
            f"Description: {item.description or 'Not provided'}",
            f"Actual behaviour: {item.actual_behaviour or 'Not provided'}",
            f"Expected behaviour: {item.expected_behaviour or 'Not provided'}",
            "Acceptance criteria:",
        ]
        lines += [f"- {criterion.description}" for criterion in item.criteria] or ["- No explicit criteria recorded. Define appropriate measurable criteria before implementation."]
        lines += ["Testing instructions:", item.testing_instructions or "Define and execute practical verification steps for this item."]
        if item.attachments:
            lines.append("Evidence attachments: " + ", ".join(a.original_name for a in item.attachments))

    if next_phase:
        lines += ["", "Relevant next roadmap phase items:"]
        lines += [f"- {'[x]' if i.get('completed') else '[ ]'} {i.get('text')}" for i in next_phase.get("items", [])] or ["- No parsed roadmap items in the next phase."]

    lines += [
        "",
        "Implementation and release requirements:",
        "- Implement the selected items completely and keep scope focused.",
        "- Create or update automated tests and run the complete relevant suite.",
        "- Determine the next semantic version from the actual current repository state and scope.",
        "- Update version metadata, CHANGELOG and relevant README/documentation.",
        "- Reconcile the roadmap after implementation. Mark work complete only when genuinely delivered and retain still-outstanding items.",
        "- Do not silently rewrite roadmap scope or remove valid future work.",
        "- Ensure implementation, roadmap, changelog and release version remain consistent.",
        "- Create a focused branch and PR. Include the DevHub item IDs in the PR summary.",
        "- Do not create a separate GitHub Issue unless explicitly requested.",
        "- Do not merge while CI is failing.",
        "",
        "Raw roadmap context retrieved by DevHub:",
        roadmap_text or "Roadmap could not be retrieved. Investigate before implementation.",
        "",
        "Current changelog context retrieved by DevHub:",
        changelog_text or "Changelog could not be retrieved. Investigate before implementation.",
    ]
    return "\n".join(lines)
