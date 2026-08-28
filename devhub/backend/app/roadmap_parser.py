import re
from dataclasses import dataclass, field
from typing import Iterable

VERSION_RE = re.compile(r"\b(v?\d+\.\d+(?:\.\d+|\.x)?(?:[-+][A-Za-z0-9.-]+)?)\b", re.I)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ITEM_RE = re.compile(r"^\s*[-*+]\s+(?:\[( |x|X)\]\s+)?(.+?)\s*$")

@dataclass
class ParsedItem:
    text: str
    completed: bool = False
    sort_order: int = 0

@dataclass
class ParsedPhase:
    heading: str
    title: str
    version: str | None
    heading_level: int
    phase_type: str
    status: str
    sort_order: int
    raw_heading: str
    items: list[ParsedItem] = field(default_factory=list)


def _status_for_heading(text: str, items: Iterable[ParsedItem]) -> str:
    lowered = text.lower()
    if "future" in lowered:
        return "Future"
    if "completed" in lowered or "delivered" in lowered or "done" in lowered:
        return "Completed"
    if "in progress" in lowered or "current" in lowered:
        return "In Progress"
    values = list(items)
    if values and all(item.completed for item in values):
        return "Completed"
    if "planned" in lowered or "upcoming" in lowered or "next" in lowered:
        return "Planned"
    return "Unknown"


def _phase_type(text: str, version: str | None) -> str:
    lowered = text.lower()
    if "future" in lowered:
        return "Future"
    if "phase" in lowered or "milestone" in lowered:
        return "Phase"
    if version:
        return "Release"
    return "Section"


def _title_without_version(text: str, version: str | None) -> str:
    if not version:
        return text.strip()
    return re.sub(re.escape(version), "", text, flags=re.I).strip(" -:–—") or version


def parse_roadmap(markdown_text: str) -> dict:
    if not markdown_text.strip():
        return {"status": "Missing", "phases": [], "warnings": ["Roadmap is empty"]}

    phases: list[ParsedPhase] = []
    current: ParsedPhase | None = None
    parent_context: str | None = None
    warnings: list[str] = []

    for raw_line in markdown_text.splitlines():
        heading = HEADING_RE.match(raw_line)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2).strip()
            version_match = VERSION_RE.search(text)
            version = version_match.group(1) if version_match else None
            lowered = text.lower()
            meaningful = bool(version) or any(k in lowered for k in ("phase", "milestone", "future", "planned", "upcoming", "current", "completed", "delivered"))
            if level <= 2 and not meaningful:
                parent_context = text
                current = None
                continue
            if level >= 3 and parent_context and not meaningful:
                combined = f"{parent_context} {text}"
                version_match = VERSION_RE.search(combined)
                version = version_match.group(1) if version_match else None
                meaningful = bool(version)
            if meaningful:
                title = _title_without_version(text, version)
                current = ParsedPhase(
                    heading=text,
                    title=title,
                    version=version,
                    heading_level=level,
                    phase_type=_phase_type(text, version),
                    status="Unknown",
                    sort_order=len(phases),
                    raw_heading=raw_line,
                )
                phases.append(current)
            else:
                current = None
            continue

        item_match = ITEM_RE.match(raw_line)
        if item_match and current:
            check = item_match.group(1)
            current.items.append(ParsedItem(text=item_match.group(2).strip(), completed=bool(check and check.lower() == "x"), sort_order=len(current.items)))

    for phase in phases:
        phase.status = _status_for_heading(phase.heading, phase.items)

    if not phases:
        return {"status": "Unsupported structure", "phases": [], "warnings": ["No recognised roadmap phases were found"]}

    recognised = sum(1 for phase in phases if phase.version or phase.phase_type in {"Phase", "Future"})
    status = "Parsed" if recognised == len(phases) else "Partially parsed"
    if status == "Partially parsed":
        warnings.append("Some roadmap sections could not be classified confidently")

    return {
        "status": status,
        "warnings": warnings,
        "phases": [
            {
                "heading": phase.heading,
                "title": phase.title,
                "version": phase.version,
                "heading_level": phase.heading_level,
                "phase_type": phase.phase_type,
                "status": phase.status,
                "sort_order": phase.sort_order,
                "raw_heading": phase.raw_heading,
                "items": [item.__dict__ for item in phase.items],
            }
            for phase in phases
        ],
    }
