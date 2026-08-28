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

## v0.4.0 Roadmap Intelligence

Delivered:

- Deterministic Markdown roadmap parser for common version, phase, milestone and Future structures.
- Structured Roadmap view while preserving Raw Markdown as the authoritative source view.
- Persistent roadmap snapshots, phases and roadmap items with Alembic migration support.
- Current/next roadmap phase resolution with user-overridable selection endpoints.
- Register item association with roadmap phases and roadmap-aware filtering.
- Project Details roadmap summary and phase/item visibility.
- Roadmap-aware Next Release Builder suggestions without automatic scope selection.
- Structured roadmap context included in generated release prompts.
- GitHub Release to Git tag version fallback with recorded version source.
- Richer CI aggregation using GitHub check-runs plus combined commit status.
- Roadmap cache reuse when the source file SHA has not changed.
- Manual Reparse Roadmap support.

Remaining Roadmap Intelligence follow-up work:

- Richer roadmap reconciliation preview after releases, including clearer completed/outstanding recommendations.
- Changelog version comparison and explicit reconciliation warnings.
- More advanced current/next phase confirmation controls in the frontend.
- Wider parser validation against additional roadmap styles from the project portfolio.
- Better API request coalescing, retry/backoff telemetry and rate-limit diagnostics for larger portfolios.

## v0.5.x Assisted Requirements

- AI-assisted analysis of feedback evidence.
- Suggested defect/enhancement descriptions.
- Suggested acceptance criteria and test instructions.
- Duplicate and related-item detection.

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
