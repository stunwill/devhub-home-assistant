from backend.app.roadmap_parser import parse_roadmap


def test_version_sections_and_future():
    parsed = parse_roadmap("""# Roadmap
## v1.2.0 Dashboard
- Feature A
- [x] Feature B
## v1.3.x Reporting
- Report A
## Future
- Feature C
""")
    assert parsed["status"] == "Parsed"
    assert [p["version"] for p in parsed["phases"][:2]] == ["v1.2.0", "v1.3.x"]
    assert parsed["phases"][0]["items"][1]["completed"] is True
    assert parsed["phases"][2]["status"] == "Future"


def test_phase_and_nested_version():
    parsed = parse_roadmap("""# Roadmap
## Phase 1
### v2.0 Core
- A
## Planned
### Version 2.1
- B
""")
    assert len(parsed["phases"]) >= 3
    assert any(p["version"] == "v2.0" for p in parsed["phases"])
    assert any((p["version"] or "").endswith("2.1") for p in parsed["phases"])


def test_empty_and_unstructured():
    assert parse_roadmap("")["status"] == "Missing"
    assert parse_roadmap("# Notes\nJust prose")["status"] == "Unsupported structure"


def test_completed_checkbox_phase():
    parsed = parse_roadmap("""## v1.0.0 Release
- [x] Done A
- [x] Done B
""")
    assert parsed["phases"][0]["status"] == "Completed"
