import re
from dataclasses import dataclass, field
from typing import Iterable

VERSION_RE = re.compile(r"\b(v?\d+\.\d+(?:\.\d+|\.x)?(?:[-+][A-Za-z0-9.-]+)?)\b", re.I)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
ITEM_RE = re.compile(r"^\s*[-*+]\s+(?:\[( |x|X)\]\s+)?(.+?)\s*$")
SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:[-+][A-Za-z0-9.-]+)?$", re.I)
VERSION_BAND_RE = re.compile(r"^v?(\d+)\.(\d+)\.x$", re.I)

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


def semantic_version(value: str | None) -> tuple[int, int, int] | None:
    if not value:
        return None
    match = SEMVER_RE.match(value.strip())
    return tuple(map(int, match.groups())) if match else None


def version_order_key(value: str | None) -> tuple[int, int, int] | None:
    exact = semantic_version(value)
    if exact:
        return exact
    if not value:
        return None
    band = VERSION_BAND_RE.match(value.strip())
    return (int(band.group(1)), int(band.group(2)), 0) if band else None


def version_contains(phase_version: str | None, detected_version: str | None) -> bool:
    phase_exact = semantic_version(phase_version)
    detected = semantic_version(detected_version)
    if phase_exact and detected:
        return phase_exact == detected
    if not phase_version or not detected:
        return False
    band = VERSION_BAND_RE.match(phase_version.strip())
    return bool(band and (int(band.group(1)), int(band.group(2))) == detected[:2])


def lifecycle_status(phase, detected_version: str | None) -> str:
    if getattr(phase, "ignored", False):
        return "Ignored"
    if getattr(phase, "phase_type", None) == "Future":
        return "Future"
    phase_version = getattr(phase, "version", None)
    detected = semantic_version(detected_version)
    if detected and version_contains(phase_version, detected_version):
        return "Current / Released"
    phase_key = version_order_key(phase_version)
    if phase_key and detected:
        if phase_key < detected:
            return "Historical / Released"
        if phase_key > detected:
            return "Future / Planned"
    explicit = getattr(phase, "status", "Unknown") or "Unknown"
    if explicit == "Completed":
        return "Historical / Delivered"
    if explicit == "In Progress":
        return "Current"
    if explicit == "Planned":
        return "Future / Planned"
    return "Unable to determine"


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
