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

Remaining v0.5.x opportunities:

- Direct provider-supported video understanding rather than retaining video only as review evidence.
- Richer evidence preprocessing where it materially improves reliability.
- User-confirmed persisted `duplicate of` / `related to` relationships if advisory detection proves valuable in real usage.
- More sophisticated local similarity ranking and confidence explanation based on representative Register data.
- Additional AI providers where demand justifies them.

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
