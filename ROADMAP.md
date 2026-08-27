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
- Manual refresh and periodic in-app refresh with stale/error state handling.
- Public repository installation documentation.
- Database migration for synchronisation metadata.
- Preserved Raspberry Pi 5 / aarch64 image build validation.

Remaining v0.2.x follow-up work:

- Move periodic synchronisation from browser-session polling to a backend scheduler so refresh continues when no DevHub UI is open.
- Improve CI/check aggregation beyond the combined commit status endpoint, including richer GitHub Actions/check-run state.
- Improve API request coalescing and conditional refresh/rate-limit telemetry for larger project portfolios.
- Add richer release/tag fallback detection for repositories that do not publish GitHub Releases.

## v0.3.x Roadmap Intelligence

- Parse common roadmap structures into phases and milestones.
- Relate backlog items to roadmap work automatically.
- Surface roadmap sequencing and dependency impacts during release planning.

## v0.4.x Assisted Requirements

- AI-assisted analysis of feedback evidence.
- Suggested defect/enhancement descriptions.
- Suggested acceptance criteria and test instructions.
- Duplicate and related-item detection.

## v0.5.x Release Execution

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
