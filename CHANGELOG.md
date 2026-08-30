# Changelog

All notable changes to DevHub are documented here.

## [0.5.9] - 2026-08-30

### Fixed

- Corrected Home Assistant version discovery for repositories whose packaged add-on/app manifest lives inside a product directory that cannot be derived from the GitHub repository slug.
- DevHub now inspects bounded top-level repository directories for packaged `config.yaml` manifests in addition to its existing known manifest paths.
- When multiple valid Home Assistant manifests are found, DevHub selects the highest semantic version rather than stopping at the first stale manifest candidate.
- This fixes the MediaHub case where `mediahub/config.yaml` reports `0.10.0-dev` but DevHub previously surfaced stale `0.1.1-dev` metadata.
- Once the correct `0.10.0-dev` evidence is synchronised, existing semantic Roadmap Intelligence correctly resolves `v0.10.0 Television Requests and Sonarr Workflow` as the active phase and `Future` as the following planning bucket, rather than presenting delivered `v0.9.0 Plex Library Intelligence` as next.

### Regression protection

- Added version-evidence tests for product-directory Home Assistant manifests and multiple competing manifest candidates.
- Added a representative MediaHub lifecycle test covering delivered `v0.9.0`, in-progress `v0.10.0`, `0.10.0-dev` detected metadata and the Future bucket.
- Preserved GitHub Release/tag precedence when those authoritative sources exist.
- Preserved Portfolio refresh, CI commit association, mobile/ingress safeguards, Evidence Intelligence and aarch64 startup testing.

### Release scope

- Application, frontend and Home Assistant app metadata updated consistently to 0.5.9.
- No database migration is required.
- No Release Execution functionality is included.

## [0.5.8] - 2026-08-30

### Fixed

- Corrected automatic roadmap Next Phase selection so stale historical `In Progress` phases cannot become the lifecycle baseline when the detected release is newer.
- Automatic next-phase detection now uses the detected release as the minimum semantic lifecycle position, while preserving explicit user overrides and Future-bucket fallback.
- Corrected CI aggregation so completed successful check-runs are no longer left as Pending solely because a stale combined commit status still reports pending.
- CI cache entries are now associated with the latest commit SHA, and the Portfolio treats mismatched cached CI as stale rather than authoritative.
- Manual Portfolio refresh now waits for refreshed project and roadmap intelligence data, surfaces partial failures, and no longer completes visually before the displayed data has been replaced.

### Project identity and Portfolio UX

- Added editable friendly project display names while keeping GitHub owner/repository identity unchanged.
- New projects default to a human-readable name derived from the repository slug when a custom display name is not supplied.
- Project Details now provides an Edit name workflow and additional sync/CI commit diagnostics.
- A single amber `OPEN PR` chip now links directly to its GitHub pull request; multiple-PR counts remain non-arbitrary summary chips with individual links in expanded details.
- Replaced the refresh `…` state with a rotating refresh indicator plus explicit `Refreshing projects`, `Updated just now`, failure and partial-failure feedback.

### Regression protection

- Added roadmap lifecycle coverage for stale historical In Progress phases against newer detected releases.
- Added CI aggregation tests for completed success, in-progress, failed and no-CI states.
- Added project rename regression coverage proving repository identity is unchanged.
- Extended frontend and CI safeguards for project editing, direct single-PR links, refresh feedback and commit-associated CI state.
- Preserved ingress routing, compact Portfolio cards, mobile hamburger navigation, release-version evidence, Evidence Intelligence and aarch64 startup protections.

### Release scope

- Application, frontend and Home Assistant app version metadata updated consistently to 0.5.8.
- No database migration is required because friendly display names reuse the existing `Project.name` field.
- No Release Execution functionality is included.

## [0.5.7] - 2026-08-30

### Fixed

- Corrected GitHub synchronisation timestamps so API responses serialise UTC timestamps with an explicit `Z` suffix instead of exposing timezone-naive values that browsers could interpret as local time.
- Newly added or refreshed projects now report relative sync times such as `just now` instead of appearing approximately ten hours old in UTC+10 environments.
- Preserved timezone-naive SQLite storage where required while making API boundaries unambiguously UTC, avoiding mixed aware/naive datetime comparison errors.

### Portfolio Intelligence

- Expanded release detection from GitHub Release / Git tag only to a deterministic evidence hierarchy covering GitHub Release, semantic Git tag, Home Assistant manifest, CHANGELOG heading, frontend package version and backend `APP_VERSION`.
- Retained the selected release source plus all discovered version evidence in the project GitHub cache for diagnostics and conflict visibility.
- Portfolio ordering now prioritises projects with open pull requests, oldest open PR activity first, followed by projects without open PRs ordered by oldest last-merged PR activity.
- Projects with no known PR history sort after projects with known merged-PR history, with project name as the deterministic tie-breaker.
- Open pull request counts now render as a prominent amber `OPEN PR` attention chip while zero-PR projects remain visually muted.
- Expanded project-card details expose individual open PR links and version evidence without increasing the collapsed card footprint.
- Project Details and synchronisation diagnostics now expose version evidence alongside the detected version source.

### Regression protection

- Added backend coverage for explicit UTC serialisation and version-evidence parsers.
- Added frontend coverage for UTC and offset-aware relative time calculations plus PR-priority Portfolio sorting.
- Extended UI contract and CI source safeguards for version evidence, PR sorting and prominent open-PR styling.
- Preserved existing ingress, mobile hamburger navigation, compact Portfolio layout, Roadmap Intelligence, Evidence Intelligence and aarch64 startup protections.

### Release scope

- Application, frontend and Home Assistant app version metadata updated consistently to 0.5.7.
- No database migration is required.
- No Release Execution functionality is included.

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

## [0.5.3] - 2026-08-29

### Fixed

- Mobile responsive corrections and ingress-safe interaction fixes.
