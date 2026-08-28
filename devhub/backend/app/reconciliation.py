import re
from dataclasses import dataclass

SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+][A-Za-z0-9.-]+)?$", re.I)
CHANGELOG_HEADING_RE = re.compile(r"^#{1,6}\s+(?:\[)?(v?\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?)(?:\])?(?:\s+[-–:].*)?$", re.I)


def normalise_version(value: str | None) -> str | None:
    if not value:
        return None
    match = SEMVER_RE.match(value.strip())
    if not match:
        return None
    return ".".join(match.groups())


def parse_changelog_latest(markdown_text: str | None) -> dict:
    if markdown_text is None:
        return {"status": "Missing changelog", "version": None, "reason": "Configured changelog file was not found"}
    if not markdown_text.strip():
        return {"status": "Unable to determine", "version": None, "reason": "Changelog is empty"}
    for raw in markdown_text.splitlines():
        line = raw.strip()
        if not line.startswith("#"):
            continue
        if "unreleased" in line.lower():
            continue
        match = CHANGELOG_HEADING_RE.match(line)
        if match:
            return {"status": "Parsed", "version": normalise_version(match.group(1)), "raw_version": match.group(1), "reason": None}
    return {"status": "Unable to determine", "version": None, "reason": "No recognisable semantic version heading was found"}


def compare_changelog(changelog_text: str | None, detected_version: str | None) -> dict:
    parsed = parse_changelog_latest(changelog_text)
    if parsed["status"] == "Missing changelog":
        return {**parsed, "detected_version": normalise_version(detected_version)}
    release = normalise_version(detected_version)
    changelog = parsed.get("version")
    if parsed["status"] != "Parsed" or not release:
        return {**parsed, "status": "Unable to determine", "detected_version": release}
    if changelog == release:
        status = "Current"
    elif tuple(map(int, changelog.split("."))) > tuple(map(int, release.split("."))):
        status = "Ahead of detected release"
    else:
        status = "Changelog may require reconciliation"
    return {**parsed, "status": status, "detected_version": release}


def reconcile_release(project_version: str | None, release, phase, changelog_state: dict) -> dict:
    detected = normalise_version(project_version)
    planned = normalise_version(getattr(release, "planned_version", None)) if release else None
    actual = normalise_version(getattr(release, "actual_version", None)) if release else None
    release_match = "Unable to determine"
    reasons: list[str] = []
    if detected and release:
        candidate = actual or planned
        if candidate == detected:
            release_match = "Matched"
        elif candidate:
            release_match = "Review required"
            reasons.append(f"DevHub release {candidate} does not match detected GitHub version {detected}.")
    elif detected:
        reasons.append(f"Detected GitHub version {detected} has no matching DevHub release record.")

    roadmap_items = list(getattr(phase, "items", []) or []) if phase else []
    linked = list(getattr(phase, "register_items", []) or []) if phase else []
    completed_linked = [i for i in linked if getattr(i, "status", "") in {"Released", "Passed"} or getattr(i, "completed_release", None)]
    incomplete_roadmap = [i for i in roadmap_items if not getattr(i, "completed", False)]

    if not detected:
        overall = "Unable to determine"
        reasons.append("No reliable released version could be detected.")
    elif release_match == "Review required":
        overall = "Reconciliation required"
    elif phase and incomplete_roadmap:
        overall = "Reconciliation required"
        reasons.append("The associated roadmap phase still contains items not marked complete in ROADMAP.md.")
    elif changelog_state.get("status") in {"Changelog may require reconciliation", "Ahead of detected release"}:
        overall = "Reconciliation recommended"
        reasons.append(f"CHANGELOG.md state is {changelog_state.get('status')}.")
    elif release_match == "Matched" and phase:
        overall = "Reconciled"
    else:
        overall = "Reconciliation recommended"

    preview = {
        "mark_completed": [i.text for i in roadmap_items if getattr(i, "completed", False)],
        "still_outstanding": [i.text for i in incomplete_roadmap],
        "potential_phase_complete": bool(phase and roadmap_items and not incomplete_roadmap),
    }
    return {
        "status": overall,
        "detected_version": detected,
        "planned_version": planned,
        "actual_version": actual,
        "release_match": release_match,
        "phase_id": getattr(phase, "id", None),
        "phase": f"{getattr(phase, 'version', '') or ''} {getattr(phase, 'title', '') or ''}".strip() if phase else None,
        "roadmap_items": len(roadmap_items),
        "delivered_register_items": len(completed_linked),
        "potentially_outstanding": len(incomplete_roadmap),
        "reasons": reasons or ["Available release, roadmap and changelog evidence is consistent."],
        "preview": preview,
        "changelog": changelog_state,
    }
