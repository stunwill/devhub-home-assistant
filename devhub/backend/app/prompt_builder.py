from .models import Project, Release

def build_release_prompt(project: Project, release: Release, roadmap_text: str | None, changelog_text: str | None) -> str:
    items = [link.item for link in release.scope]
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
        "Before making changes:",
        "1. Inspect the latest merged branch state, current release/development version, latest releases, recent merged PRs and currently open PRs.",
        "2. Review the existing architecture, relevant integrations, tests and CI.",
        f"3. Read the configured roadmap at `{project.roadmap_path}` and changelog at `{project.changelog_path}`.",
        "4. Map every approved DevHub item below to the current roadmap and identify affected phases, milestones, dependencies or sequencing.",
        "5. Preserve existing functionality and avoid regressions.",
        "",
        "Approved DevHub release scope:",
    ]
    for item in items:
        lines += [
            "",
            f"## {item.item_key} | {item.item_type} | {item.priority}",
            item.title,
            "",
            f"Description: {item.description or 'Not provided'}",
            f"Actual behaviour: {item.actual_behaviour or 'Not provided'}",
            f"Expected behaviour: {item.expected_behaviour or 'Not provided'}",
            "Acceptance criteria:",
        ]
        lines += [f"- {criterion.description}" for criterion in item.criteria] or ["- No explicit criteria recorded. Define appropriate measurable criteria before implementation."]
        lines += ["Testing instructions:", item.testing_instructions or "Define and execute practical verification steps for this item."]
        if item.attachments:
            lines.append("Evidence attachments: " + ", ".join(a.original_name for a in item.attachments))
    lines += [
        "",
        "Implementation and release requirements:",
        "- Implement the selected items completely and keep scope focused.",
        "- Create or update automated tests and run the complete relevant suite.",
        "- Determine the next semantic version from the actual current repository state and scope.",
        "- Update version metadata, CHANGELOG and relevant README/documentation.",
        "- Update the roadmap after implementation. Mark items complete only when genuinely delivered, add newly delivered capability where required, preserve valid future work, and revise future sequencing only where dependencies or scope truly changed.",
        "- Ensure implementation, roadmap, changelog and release version remain consistent.",
        "- Create a focused branch and PR. Include the DevHub item IDs in the PR summary.",
        "- Do not create a separate GitHub Issue unless explicitly requested.",
        "- Do not merge while CI is failing.",
        "",
        "Current roadmap context retrieved by DevHub:",
        roadmap_text or "Roadmap could not be retrieved. Investigate before implementation.",
        "",
        "Current changelog context retrieved by DevHub:",
        changelog_text or "Changelog could not be retrieved. Investigate before implementation.",
    ]
    return "\n".join(lines)
