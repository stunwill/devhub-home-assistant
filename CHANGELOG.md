# Changelog

All notable changes to DevHub are documented here.

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
- Register item association with roadmap phases and roadmap-aware filtering.
- Roadmap summary in Project Details.
- Roadmap-aware Next Release Builder suggestions.
- Structured roadmap context in generated release prompts.
- GitHub Release to Git tag version fallback with version-source tracking.
- Richer CI aggregation using GitHub check runs plus combined commit status.
- Alembic migration for Roadmap Intelligence data.

### Changed

- GitHub synchronisation now reuses roadmap snapshots when the source roadmap SHA has not changed.
- Project metadata records whether the current version came from a GitHub Release, Git tag or is unknown.
- Release planning now surfaces the next roadmap phase without automatically selecting scope.
- Application, frontend and Home Assistant add-on version metadata bumped to 0.4.0.

### Preserved

- v0.3.0 Portfolio dashboard and responsive card layout.
- Repository URL onboarding and project artwork.
- Backend background GitHub synchronisation.
- Last-known-good GitHub data on refresh failure.
- PR #4 `PYTHONPATH=/app` startup correction.
- Raspberry Pi 5 / aarch64 image build and startup smoke testing.

## [0.3.0] - 2026-08-27

### Added

- Polished Portfolio dashboard with responsive, information-dense project cards.
- Card-level latest release, open PR, last merged PR, CI and GitHub sync status.
- Sidebar GitHub synchronisation summary with real degraded/operational state.
- Backend GitHub synchronisation loop for active projects approximately every 15 minutes, independent of the browser session.
- `/api/projects/sync-summary` for Portfolio-level GitHub health information.
- aarch64 Home Assistant add-on startup smoke test that verifies migrations, FastAPI startup and `/api/health` availability.

### Changed

- Portfolio is now the main operational development view rather than a simple project listing.
- Mobile Portfolio layout now uses a dedicated single-column card design with no page-level horizontal scrolling.
- Project cards now use uploaded artwork where available and accessible fallback icons otherwise.
- Home Assistant and frontend version metadata bumped to 0.3.0.
- Documentation updated for background synchronisation and startup regression protection.

### Preserved

- Repository-URL onboarding and GitHub metadata discovery from v0.2.0.
- Last-known-good GitHub cache when refresh fails.
- PR #4 startup import-path fix using `PYTHONPATH=/app`.
- Raspberry Pi 5 / aarch64 image build protection.
- Existing Register, Feedback, Release Builder and Roadmap functionality.

## [0.2.0] - 2026-08-27

### Added

- GitHub repository URL onboarding with repository discovery and validation.
- Automatic retrieval of repository description, visibility, default branch, releases, open PRs, last merged PR, latest commit and CI state.
- Responsive project-card dashboard showing current release, open PRs, last merged PR, CI state and sync age.
- Project Details view with repository, PR, release and roadmap information.
- Project logo/icon upload stored in persistent runtime storage.
- Roadmap and changelog path detection during onboarding.
- Manual all-project refresh plus periodic 15-minute refresh while DevHub is open.
- Sync status/error tracking that preserves last known good GitHub data.
- Alembic migration for GitHub synchronisation and project artwork metadata.

### Changed

- Project setup now prioritises a GitHub repository URL instead of manual GitHub metadata entry.
- Updated public-repository Home Assistant installation guidance.
- Bumped DevHub application and add-on version to 0.2.0.

### Preserved

- Raspberry Pi 5 / aarch64 Home Assistant image build validation introduced by PR #2.
- Existing defect/enhancement register, feedback attachments, release builder and roadmap-aware prompt generation.

## [0.1.0] - 2026-08-26

### Added

- Initial Home Assistant add-on foundation with ingress support.
- React/Vite frontend and FastAPI backend architecture.
- SQLite persistence with Alembic migrations.
- Portfolio dashboard and project configuration.
- GitHub release metadata refresh and roadmap retrieval.
- Defect and enhancement register with acceptance criteria and testing instructions.
- Feedback capture with image and video attachment support.
- Next Release Builder with roadmap-aware development prompt generation.
- Release records, acceptance testing, readiness and release history foundations.
- GitHub Actions CI for backend and frontend validation.
- Security controls for secrets, uploads, Markdown and persistent runtime data.
