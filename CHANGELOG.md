# Changelog

All notable changes to DevHub are documented here.

## [0.5.6] - 2026-08-29

### Changed

- Replaced the permanently expanded mobile navigation block with a compact hamburger-triggered navigation drawer.
- Added the hamburger control directly beside the DevHub brand in the mobile application header.
- Kept the Portfolio refresh icon and Create `+` action in the compact header so primary actions remain immediately available.
- Moved Portfolio, Projects, Register, Releases and Settings into the mobile navigation drawer while preserving the desktop sidebar.
- Removed the mobile Portfolio Dashboard subtitle from the persistent header and moved the Portfolio page title into content so dashboard data starts substantially higher on phone screens.

### Accessibility and responsive UX

- Added `aria-expanded`, `aria-controls`, labelled navigation, current-page state and visible focus treatment for mobile navigation.
- Mobile navigation closes when a destination is selected, when the backdrop is tapped and when Escape is pressed, with focus returned to the hamburger control after keyboard dismissal.
- The drawer respects mobile safe-area insets and remains above Home Assistant ingress content.
- Preserved the compact two-column Portfolio card layout on normal phone widths and the existing narrow-screen single-column fallback.

### Regression protection

- Updated frontend UI contract coverage for the hamburger navigation labels and navigation landmark.
- Replaced CI checks that required the old mobile navigation grid with safeguards for the mobile drawer, hamburger accessibility state and responsive breakpoint.
- Preserved frontend lint/test/build, ingress-safe asset/API routing, backend tests, Evidence Intelligence media checks and aarch64 build/startup smoke testing.

### Release scope

- Application, frontend and Home Assistant app version metadata updated consistently to 0.5.6.
- No database migration is required because this release changes only application-shell navigation and presentation.
- No Release Execution functionality is included.

## [0.5.5] - 2026-08-29

### Changed

- Redesigned the Portfolio Dashboard around compact, scan-first project cards instead of tall detail-heavy cards.
- Replaced the large Refresh All control with an accessible refresh icon in the Portfolio header.
- Consolidated Add Project and Add Feedback behind one Create `+` action with a compact desktop popover and mobile bottom sheet.
- Added portfolio-level summary metrics for total projects, CI attention, open pull requests and release metadata gaps.
- Added compact card summaries for release, CI status, next roadmap phase, open PR count and sync freshness.
- Added per-project accordion details for repository metadata, release source, last merged PR, roadmap context and existing Roadmap / Project Details actions.
- Missing release metadata and other attention states now receive stronger visual emphasis than normal zero/healthy states.
- Project display names remain sourced from DevHub project configuration instead of being hard-coded from repository names.

### Responsive UX

- Portfolio cards render three across on normal desktop widths and four on very wide screens.
- Tablet and medium desktop widths use two columns.
- Mobile widths use two compact cards across when there is sufficient room, with a single-column fallback below 420 px.
- Long project names, phase labels and PR titles are clamped or wrapped so the page cannot be widened by card content.
- Mobile Create uses a safe-area-aware bottom sheet and the compact summary strip can scroll horizontally if necessary.

### Regression protection

- Added frontend contract coverage for Portfolio header actions, summary metrics, missing-release warnings and accordion terminology.
- Added CI source safeguards for the compact Portfolio controls, responsive two-column grid and narrow-screen fallback.
- Preserved existing Home Assistant ingress asset/API routing checks, backend tests, Evidence Intelligence media checks and aarch64 build/startup smoke testing.

### Release scope

- Application, frontend and Home Assistant app version metadata updated consistently to 0.5.5.
- No database migration is required because this release reuses existing project, GitHub and roadmap data.
- No Release Execution functionality is included.

## [0.5.4] - 2026-08-29

### Fixed

- Corrected Roadmap Intelligence so roadmap source order is no longer treated as lifecycle order.
- Automatic next-phase detection now uses semantic-version progression and never selects a lower released version as future work.
- When the current concrete release is the latest semantic version and a `Future` roadmap bucket exists, DevHub now selects `Future` rather than walking backwards through historical releases.
- Historical roadmap versions are classified deterministically as historical/released instead of remaining `Unknown` when the detected repository release provides sufficient evidence.
- Semantic version bands such as `v0.5.x` remain supported, including resolving the current release into its matching band and progressing to a later band such as `v0.6.x`.
- Historical phases are excluded from automatic release-planning choices without requiring the user to mark them ignored.
- Preserved explicit user current/next phase overrides, including manual selection of unusual phases where required.

### Changed

- Project Details now labels the current released phase and next planned phase more clearly.
- Roadmap phase cards expose lifecycle status separately from raw parsed heading/task status.
- Historical cards no longer show a large planning-ignore action by default and are more compact on mobile.
- Next Release Builder excludes historical phases from ordinary planning choices.
- Reconciliation now distinguishes repository consistency from missing DevHub internal release history, so a valid GitHub release/roadmap/changelog combination is not presented as a roadmap defect merely because DevHub lacks a local release record.

### Regression protection

- Added lifecycle tests for descending and ascending roadmaps, future buckets, patch progression, version bands, no-future cases, user overrides and ignored phases.
- Added reconciliation coverage for a detected GitHub release with matching roadmap/changelog evidence but a missing DevHub release record.
- Preserved Home Assistant ingress routing, responsive/mobile safeguards, Evidence Intelligence media checks, aarch64 image build and startup smoke testing.

### Release scope

- Application, frontend and Home Assistant app version metadata updated consistently to 0.5.4.
- No database migration is required because lifecycle classification is derived from existing roadmap/release evidence.
- No Release Execution functionality is included.
