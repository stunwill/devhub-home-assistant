# DevHub

DevHub is a Home Assistant app for managing a portfolio of GitHub-developed applications. It combines release visibility, pull-request status, structured roadmaps, a defect/enhancement register, feedback evidence, acceptance criteria, release planning, supervised release execution, deterministic roadmap/release reconciliation and optional Assisted Requirements.

## v0.6.0 capabilities

- Home Assistant app packaging with ingress.
- FastAPI backend, React/Vite frontend and SQLite persistence.
- GitHub repository URL onboarding and project discovery.
- User-editable friendly project display names that remain separate from GitHub repository identity.
- User-managed project logos with upload, replacement and removal controls in Project Details; custom artwork is displayed in rounded app-style icon frames, with initials retained as the fallback.
- Compact responsive Portfolio dashboard with scan-first release, PR, CI, roadmap-next-phase and sync state.
- Portfolio summary metrics for total projects, CI attention, open PRs and release metadata gaps.
- Compact mobile application header with hamburger navigation beside the DevHub brand.
- Mobile navigation drawer for Portfolio, Projects, Register, Releases and Settings, while desktop retains the persistent sidebar.
- Header-level refresh icon plus a single Create `+` action for Add Project and Add Feedback.
- Manual refresh feedback with active spinner state, success/failure messaging, partial-failure visibility and immediate Portfolio/roadmap data reload.
- Portfolio ordering that prioritises projects with open PRs, oldest waiting PR activity first, then projects without open PRs by oldest last-merged activity.
- Prominent amber OPEN PR attention chips while zero-PR states remain visually muted; a single open PR chip links directly to that GitHub PR.
- UTC-aware API timestamps for accurate local relative-time rendering.
- Deterministic release-version evidence hierarchy using GitHub Release, Git tag, Home Assistant manifest, CHANGELOG, frontend package metadata and backend APP_VERSION.
- Version source and all discovered version evidence retained for diagnostics and conflict visibility.
- Expandable project-card details retaining repository metadata, release source, version evidence, open PR details, merged PR and existing Roadmap / Project Details actions.
- Project logo/icon upload stored in persistent runtime storage.
- Deterministic Roadmap Intelligence for common Markdown roadmap structures.
- Structured and Raw Markdown roadmap views.
- Semantic lifecycle-aware current/next phase detection that separates roadmap source order from release order and prevents stale historical phases from driving Next Phase.
- Historical, current, future/planned and non-versioned Future-bucket classification using deterministic release evidence.
- Semantic version-band support such as `v0.5.x` and `v0.6.x`.
- User confirmation/override controls that remain authoritative until automatic detection is restored.
- Reversible ignored roadmap phases without changing `ROADMAP.md`.
- Roadmap snapshots, phases and items stored relationally.
- Register-item and release associations with roadmap phases.
- Deterministic roadmap reconciliation with reasons and read-only update previews.
- Reconciliation diagnostics that distinguish repository consistency from missing DevHub internal release history.
- Deterministic `CHANGELOG.md` version parsing and reconciliation.
- Roadmap-aware filtering and Next Release Builder suggestions without automatic scope selection.
- Focused release prompts using current/next/selected phase, reconciliation and changelog context.
- Supervised Release Execution for active release plans, connecting approved scope to implementation PR, PR-head CI, merge readiness, merge detection, GitHub release publication and reconciliation.
- Deterministic implementation-PR suggestions using planned-version, branch and roadmap-title evidence, with explicit user confirmation for ambiguous associations.
- PR-specific merge readiness that requires an open non-draft PR, confirmed passing CI and confirmed GitHub mergeability before reporting Ready to Merge.
- Separate source-version, Git tag and published GitHub Release evidence so merged/versioned code is not misrepresented as a published release.
- Approved Register scope and acceptance-result progress visible within Release Execution.
- Execution-aware implementation prompt generation with explicit instructions not to merge or publish automatically.
- Compact Portfolio execution attention states for PR OPEN, CI RUNNING, READY TO MERGE, MERGED / RELEASE PENDING and RELEASE ATTENTION.
- Optional Assisted Requirements workflow that converts feedback into an editable structured requirement draft.
- Screenshot/photo evidence analysis for compatible multimodal providers.
- Evidence Intelligence for screen recordings using bounded local FFmpeg/ffprobe preprocessing and representative frame extraction.
- Structured evidence summaries, timestamped observations, confidence labels and ambiguity warnings displayed separately from the requirement draft.
- Original image/video evidence uploaded only after explicit Register-item creation; transient extracted video frames are not persisted under `/config`.
- Deterministic duplicate/related candidate narrowing with weighted structured-field matching and user-visible match explanations.
- Suggested acceptance criteria, testing instructions, priority, item type and optional roadmap phase with explicit user review.
- Non-secret AI provider capability reporting for text, image, multiple-image, direct-video, frame-based video and structured output support.
- CI aggregation using GitHub check-runs and combined commit status, tied to the latest commit SHA so stale Pending results are not shown as authoritative.
- GitHub synchronisation diagnostics with rate-limit and retry/backoff visibility.
- Backend GitHub synchronisation approximately every 15 minutes, including when no browser is open.
- Manual portfolio refresh, per-project refresh and Reparse Roadmap actions.
- Raspberry Pi 5/aarch64 Home Assistant image build validation, media-processing smoke tests and startup smoke testing in CI.

Release Execution is intentionally supervised. DevHub may detect and recommend lifecycle state, but it does not automatically merge pull requests, publish GitHub Releases, deploy applications, change release scope, mark requirements complete or edit roadmap state.

## Architecture

```text
Home Assistant
  -> DevHub app / ingress
      -> React frontend
          -> Release Execution panel
      -> FastAPI REST API
          -> supervised Release Execution service
              -> PR association/detection
              -> PR-head CI + merge readiness
              -> release publication evidence
              -> reconciliation
      -> SQLite + attachments + project artwork under /config
      -> GitHub REST API
      -> backend synchronisation task
      -> deterministic version-evidence discovery
      -> deterministic roadmap/changelog parsers
      -> roadmap lifecycle resolver
      -> reconciliation service
      -> Assisted Requirements service
          -> EvidenceService
              -> image preparation
              -> FFmpeg/ffprobe video metadata + bounded frame extraction
          -> deterministic duplicate/related candidate retrieval
          -> optional AI provider service
```

Runtime state is stored under the Home Assistant app configuration mapping (`/config` inside the app), so database, project icons, roadmap snapshots and feedback attachments survive container replacement/upgrades. Release Execution reuses the existing Release model for stable user decisions such as explicitly associated PR URLs, while volatile GitHub PR, CI and publication state is refreshed from GitHub rather than duplicated in SQLite.

Derived frames used during video analysis are temporary processing artefacts. They are created in a temporary directory, sent only as bounded image evidence where supported, and removed automatically when processing ends.

## Home Assistant installation

This repository can be added to Home Assistant as a custom app/add-on repository.

Use the repository URL:

```text
https://github.com/stunwill/devhub-home-assistant
```

In Home Assistant, add the repository, refresh the store, then install DevHub. Updates are offered when the version in `devhub/config.yaml` increases in a released repository state.
