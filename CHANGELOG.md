# Changelog

All notable changes to DevHub are documented here.

## [0.4.2] - 2026-08-28

### Fixed

- Home Assistant ingress now loads Vite production assets using relative paths instead of root-relative `/assets/...` URLs.
- Home Assistant app manifest now uses `app_config` instead of the legacy `addon_config` mapping.
- Removed deprecated `armv7` support declaration while retaining aarch64 and amd64 support.

### Changed

- Application, frontend and Home Assistant app version metadata bumped to 0.4.2.

## [0.4.1] - 2026-08-28

### Added

- User-controlled current and next roadmap phase confirmation/overrides, with automatic detection retained as the default.
- Reversible **Ignore in DevHub planning** handling for parsed roadmap phases without modifying `ROADMAP.md`.
- Deterministic roadmap reconciliation states, reasoning and read-only update previews.
- Deterministic `CHANGELOG.md` version parsing and reconciliation for common semantic-version headings.
- Release-to-roadmap-phase association and reconciliation state in release history.
- Roadmap-aware Release Builder context with manual scope selection preserved.
- Focused release prompts containing detected version source, roadmap phase context, reconciliation warnings and changelog state.
- GitHub synchronisation diagnostics including commit/roadmap SHAs, parse state, version source, CI state, changelog state and last error.
- GitHub API rate-limit telemetry and per-project retry/backoff state.
- Forward Alembic migration for reconciliation metadata and release-roadmap associations.
- Backend tests for changelog parsing, roadmap reconciliation, phase overrides, ignored phases and migration safety.

### Changed

- Roadmap refresh now coalesces content and metadata retrieval and reuses unchanged source SHAs.
- Background GitHub synchronisation now backs off after failures while allowing other projects to continue refreshing.
- Last-known-good project data remains visible during temporary GitHub failures.
- Project Details now shows version source, CI check counts, changelog state and roadmap reconciliation.
- Roadmap phase details now include linked register items and planned/completed releases.
- Application, frontend and Home Assistant add-on version metadata bumped to 0.4.1.

### Preserved

- `ROADMAP.md` and `CHANGELOG.md` remain authoritative and are never automatically rewritten.
- Repository URL onboarding, project artwork and Portfolio dashboard design.
- GitHub release/tag fallback, PR retrieval and CI/check aggregation.
- Structured and Raw Markdown roadmap views and roadmap caching.
- `PYTHONPATH=/app`, `alembic upgrade head`, aarch64 image support and startup smoke testing.

## [0.4.0] - 2026-08-28

### Added

- Deterministic Roadmap Intelligence parser for common Markdown version, phase, milestone and Future structures.
- Persistent roadmap snapshots, structured phases and roadmap items.
- Structured Roadmap view with Raw Markdown retained as the authoritative source view.
- Current and next roadmap phase resolution with manual reparse support.
