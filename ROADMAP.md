# DevHub Roadmap

DevHub is the Home Assistant development portfolio, feedback, roadmap and release-management platform for projects maintained in GitHub.

## v0.1.0 Foundation

Completed foundation:

- Home Assistant add-on packaging and ingress support.
- Portfolio dashboard and project management.
- GitHub release metadata and project refresh.
- Per-project Markdown roadmap viewing.
- Defect and enhancement register.
- Mobile-friendly feedback capture with image/video attachments.
- Acceptance criteria and testing instructions.
- Next Release Builder and roadmap-aware development prompt generation.
- Release records, reconciliation, acceptance testing and history.
- SQLite/Alembic persistence, CI and security controls.

## v0.2.0 GitHub Synchronisation

Delivered:

- GitHub repository URL onboarding and validation.
- Automatic repository/release/open-PR/last-merged-PR/latest-commit/CI reconciliation.
- Project card dashboard focused on release and PR status.
- Project Details view with richer repository state.
- Project logo/icon upload stored in persistent runtime storage.
- Roadmap and changelog path detection during onboarding.
- Manual refresh and stale/error state handling.
- Public repository installation documentation.
- Database migration for synchronisation metadata.
- Preserved Raspberry Pi 5 / aarch64 image build validation.

## v0.3.0 Portfolio Dashboard

Delivered:

- Polished Portfolio dashboard as DevHub's primary day-to-day operational view.
- Responsive three/two/one-column project card layout for desktop, tablet and mobile.
- Clear project artwork, repository identity, release, open PR, last merged PR, CI and GitHub sync status.
- Direct Roadmap and Project Details actions on every project card.
- Portfolio-level GitHub synchronisation health summary.
- Backend periodic synchronisation for active projects, so refresh continues when no frontend is open.
- Real Refresh All behaviour with last-known-good metadata retained on failures.
- aarch64 add-on startup smoke testing that verifies migration/import/startup health, not just image build success.
- Preserved PR #4 `PYTHONPATH=/app` startup correction.

## v0.4.x Roadmap Intelligence

Delivered in v0.4.0:

- Deterministic Markdown roadmap parser for common version, phase, milestone and Future structures.
- Structured Roadmap view while preserving Raw Markdown as the authoritative source view.
- Persistent roadmap snapshots, phases and roadmap items with Alembic migration support.
- Automatic current/next roadmap phase resolution.
- Register item association with roadmap phases and roadmap-aware filtering.
- Project Details roadmap summary and phase/item visibility.
- Roadmap-aware Next Release Builder suggestions without automatic scope selection.
- Structured roadmap context included in generated release prompts.
- GitHub Release to Git tag version fallback with recorded version source.
- Richer CI aggregation using GitHub check-runs plus combined commit status.
- Roadmap cache reuse when the source file SHA has not changed.
- Manual Reparse Roadmap support.

Lifecycle completion delivered in v0.4.1:

- User-confirmed or overridden current and next roadmap phases, clearly distinguished from automatic detection and reversible back to automatic detection.
- Reversible ignored roadmap phases that remain parsed but are excluded from planning selectors and automatic current/next phase resolution.
- Release-to-roadmap-phase association independent of individual Register item associations.
- Structured roadmap reconciliation that compares detected versions, DevHub release records, roadmap phase state and linked Register scope.
- Explicit reconciliation reasoning with Reconciled, Reconciliation recommended, Reconciliation required and Unable to determine states.
- Read-only suggested roadmap update previews without automatic `ROADMAP.md` editing.
- Deterministic changelog version parsing and reconciliation without automatic `CHANGELOG.md` editing.
- Release history and Release Builder roadmap/reconciliation context while preserving manual scope selection.
- Focused release prompts containing relevant structured roadmap, reconciliation and changelog context instead of dumping entire documents.
- Project Details version-source and CI/check diagnostics.
- GitHub synchronisation diagnostics, rate-limit visibility and per-project retry/backoff while retaining last-known-good data.
- API request coalescing for unchanged roadmap/changelog content where source SHAs can be reused.
- Expanded deterministic parser, reconciliation, phase-selection and migration regression tests.

Corrective lifecycle delivered in v0.4.2:

- Restored Home Assistant ingress-safe production assets through relative Vite paths.
- Updated Home Assistant app metadata to modern `app_config` mapping and current architecture declarations.
- Added regression protection around ingress asset paths.

Ongoing validation work:

- Continue broadening representative parser fixtures as additional real-world roadmap and changelog structures are encountered.
- Continue refining version-evidence diagnostics where repositories expose multiple legitimate metadata sources.

## v0.5.x Assisted Requirements

First Assisted Requirements capability delivered in v0.5.0:

- Optional AI-assisted analysis of written feedback plus screenshot/photo evidence.
- Structured requirement drafts covering title, type, description, actual/expected behaviour, priority, acceptance criteria and test instructions.
- Explicit review/edit step before any Register item is created.
- Editable and reorderable acceptance criteria.
- Optional roadmap-phase suggestion using bounded current/next Roadmap Intelligence context.
- Deterministic same-project duplicate and related-item candidate narrowing before AI analysis.
- Multiple image and video evidence selection, with original evidence attached only after explicit Register creation.
- Clear AI disabled, not-configured, failed and partial-evidence states while retaining the non-AI workflow.
- Provider/service abstraction and Home Assistant configuration without exposing credentials to the frontend.
- Validated structured model output and focused model context rather than whole roadmap/changelog/register dumps.
- Mobile-responsive assisted review UI and explicit CI regression checks for ingress-safe frontend assets.

Evidence Intelligence delivered in v0.5.1:

- Bounded local preprocessing for uploaded screen recordings using FFmpeg/ffprobe.
- Representative frame extraction with explicit limits on duration, payload size, frame count and frame dimensions.
- Structured evidence summaries, source-aware observations, timestamps, confidence labels and ambiguity warnings shown separately from the editable requirement draft.
- Frame-based video analysis through image-capable providers without claiming undocumented native video support.
- Provider capability reporting for text, image, multiple-image, direct-video, frame-based video and structured output support.
- Transient derived frames that are not persisted under `/config`; original evidence remains authoritative and is attached only after explicit Register creation.
- Evidence-aware prompting that treats visible screenshot/video text as untrusted source material and avoids unsupported root-cause claims.
- Improved deterministic duplicate/related-item ranking with weighted structured fields and user-visible match explanations.
- ARM64 production-image validation for FFmpeg/ffprobe and a tiny end-to-end frame extraction smoke test.

Corrective ingress release delivered in v0.5.2:

- Completed the Home Assistant ingress API-routing correction introduced after v0.5.1 so frontend `/api/...` requests remain inside the active DevHub ingress path.
- Restored GitHub project onboarding and configured-project loading through ingress, including the reported Fynvo onboarding case.
- Preserved ingress-safe project-logo/API resource handling.
- Added explicit CI regression protection for both static asset paths and API routing under `/api/hassio_ingress/<token>/`.
- Bumped backend, frontend and Home Assistant app version metadata together so Home Assistant can recognise and install the corrected image.

Mobile responsive UX delivered in v0.5.3:

- Reworked the Home Assistant mobile shell so Portfolio, Projects, Register, Releases and Settings remain fully reachable without clipped navigation.
- Added responsive action layouts across headers, Project Details, cards, Roadmap Intelligence and Assisted Requirements so controls remain inside narrow viewports.
- Improved wrapping for repository names, project titles, roadmap labels, error messages and other long content that previously forced the page wider.
- Converted dense desktop-oriented Register and diagnostic tables to stacked mobile records at narrow breakpoints.
- Improved touch target sizing, mobile form width, mobile modal behaviour and compact phone spacing while preserving desktop layouts.
- Added CI regression checks for responsive breakpoint rules and retained all Home Assistant ingress routing protections.

Roadmap lifecycle correction delivered in v0.5.4:

- Separated roadmap source order from lifecycle order so descending roadmaps cannot move automatic planning backwards.
- Added deterministic historical/current/future classification using semantic release evidence while preserving source order for display.
- Preserved semantic version-band roadmaps such as `v0.5.x` and `v0.6.x`.
- Prefer a planned `Future` bucket when no later concrete or version-band phase exists.
- Excluded historical phases from ordinary automatic release planning without treating them as ignored.
- Improved Project Details lifecycle badges and reconciliation messaging for missing DevHub release history.
- Added regression coverage for the MathQuest-style descending-roadmap failure.

Portfolio density and scanability delivered in v0.5.5:

- Replaced the large Portfolio action buttons with a compact refresh icon and one Create `+` action.
- Consolidated Add Project and Add Feedback into a desktop popover / mobile bottom sheet while preserving their existing workflows.
- Added compact portfolio summary metrics for total projects, CI attention, open PRs and release metadata gaps.
- Reworked project cards so release, CI, next roadmap phase, PR count and sync freshness are visible without expanding the card.
- Added expandable per-project details for repository metadata, release source, last merged PR and existing Roadmap / Project Details actions.
- Shifted visual emphasis toward missing/failed states and away from normal zero/healthy values.
- Added responsive two-column mobile cards where practical, with a narrow single-column fallback and three-to-four-column desktop layouts.
- Preserved existing Roadmap Intelligence, release planning, ingress routing, Evidence Intelligence and aarch64 startup protections.

Compact mobile navigation delivered in v0.5.6:

- Replaced the permanently expanded mobile navigation grid with a hamburger-triggered drawer beside the DevHub brand.
- Kept Portfolio refresh and Create actions in the compact mobile application header.
- Moved Portfolio, Projects, Register, Releases and Settings into the mobile drawer while preserving the desktop sidebar.
- Removed the persistent mobile subtitle/navigation block so Portfolio summary data begins significantly higher on phone screens.
- Added Escape, backdrop-dismissal, active-page indication, focus return and safe-area support for the mobile drawer.
- Preserved compact two-column Portfolio cards, Home Assistant ingress behaviour and existing page workflows.

Portfolio data accuracy delivered in v0.5.7:

- Corrected timezone-naive GitHub sync timestamps at the API boundary so relative sync times are accurate in local browser time zones.
- Expanded deterministic release-version evidence from GitHub Release / Git tag to Home Assistant manifest, CHANGELOG heading, frontend package metadata and backend APP_VERSION fallbacks.
- Retained the selected release source plus all discovered version evidence for diagnostics and conflict visibility.
- Prioritised Portfolio cards by actionable pull-request activity, with projects containing open PRs first and oldest waiting work first.
- Ordered projects without open PRs by oldest last-merged PR activity while keeping no-history projects behind known activity.
- Added prominent amber OPEN PR attention chips and open-PR detail links while keeping zero-PR states visually muted.
- Preserved compact mobile cards, CI state distinctions, mobile navigation, ingress behaviour and existing Roadmap / Project Details workflows.

Remaining v0.5.x opportunities:

- User-confirmed persisted `duplicate of` / `related to` relationships if advisory detection proves valuable in real usage.
- Additional refinement of similarity ranking based on representative Register data.
- Additional AI providers where demand justifies them.
- Direct native provider video input only where a documented, reliable provider path justifies it over bounded frame extraction.
- User-confirmed import/reconciliation of historical DevHub release records from trusted GitHub release evidence.

## v0.6.x Release Execution

- Direct release execution/integration where technically appropriate.
- Safer release lifecycle automation with explicit review gates.
- Automated post-release reconciliation into DevHub.

## Future

- Cross-project analytics and release health.
- Dependency awareness across projects.
- Notifications and release reminders.
- Richer Home Assistant integrations.
- Portfolio-level trends for defects, enhancements and delivery throughput.

The roadmap is a living product document. Future version allocation may change when actual usage, dependencies or implementation discoveries make another sequence more appropriate.