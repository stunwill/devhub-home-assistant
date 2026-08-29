# DevHub

DevHub is a Home Assistant app for managing a portfolio of GitHub-developed applications. It combines release visibility, pull-request status, structured roadmaps, a defect/enhancement register, feedback evidence, acceptance criteria, release planning, deterministic roadmap/release reconciliation and optional Assisted Requirements.

## v0.5.6 capabilities

- Home Assistant app packaging with ingress.
- FastAPI backend, React/Vite frontend and SQLite persistence.
- GitHub repository URL onboarding and project discovery.
- Compact responsive Portfolio dashboard with scan-first release, PR, CI, roadmap-next-phase and sync state.
- Portfolio summary metrics for total projects, CI attention, open PRs and release metadata gaps.
- Compact mobile application header with hamburger navigation beside the DevHub brand.
- Mobile navigation drawer for Portfolio, Projects, Register, Releases and Settings, while desktop retains the persistent sidebar.
- Header-level refresh icon plus a single Create `+` action for Add Project and Add Feedback.
- Expandable project-card details retaining repository metadata, release source, merged PR and existing Roadmap / Project Details actions.
- Project logo/icon upload stored in persistent runtime storage.
- Deterministic Roadmap Intelligence for common Markdown roadmap structures.
- Structured and Raw Markdown roadmap views.
- Semantic lifecycle-aware current/next phase detection that separates roadmap source order from release order.
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
- Optional Assisted Requirements workflow that converts feedback into an editable structured requirement draft.
- Screenshot/photo evidence analysis for compatible multimodal providers.
- Evidence Intelligence for screen recordings using bounded local FFmpeg/ffprobe preprocessing and representative frame extraction.
- Structured evidence summaries, timestamped observations, confidence labels and ambiguity warnings displayed separately from the requirement draft.
- Original image/video evidence uploaded only after explicit Register-item creation; transient extracted video frames are not persisted under `/config`.
- Deterministic duplicate/related candidate narrowing with weighted structured-field matching and user-visible match explanations.
- Suggested acceptance criteria, testing instructions, priority, item type and optional roadmap phase with explicit user review.
- Non-secret AI provider capability reporting for text, image, multiple-image, direct-video, frame-based video and structured output support.
- GitHub Release to Git tag version fallback with version-source tracking.
- CI aggregation using GitHub check-runs and combined commit status.
- GitHub synchronisation diagnostics with rate-limit and retry/backoff visibility.
- Backend GitHub synchronisation approximately every 15 minutes, including when no browser is open.
- Manual portfolio refresh, per-project refresh and Reparse Roadmap actions.
- Raspberry Pi 5/aarch64 Home Assistant image build validation, media-processing smoke tests and startup smoke testing in CI.

## Architecture

```text
Home Assistant
  -> DevHub app / ingress
      -> React frontend
      -> FastAPI REST API
      -> SQLite + attachments + project artwork under /config
      -> GitHub REST API
      -> backend synchronisation task
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

Runtime state is stored under the Home Assistant app configuration mapping (`/config` inside the app), so database, project icons, roadmap snapshots and feedback attachments survive container replacement/upgrades.

Derived frames used during video analysis are temporary processing artefacts. They are created in a temporary directory, sent only as bounded image evidence where supported, and removed automatically when processing ends.

## Home Assistant installation

This repository can be added to Home Assistant as a custom app/add-on repository.

Use the repository URL:

```text
https://github.com/stunwill/devhub-home-assistant
```

In Home Assistant, add the repository, refresh the store, then install DevHub. Updates are offered when the version in `devhub/config.yaml` increases in a released repository state.
