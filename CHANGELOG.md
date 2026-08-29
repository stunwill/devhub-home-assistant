# Changelog

All notable changes to DevHub are documented here.

## [0.5.1] - 2026-08-29

### Added

- Evidence Intelligence for Assisted Requirements, including bounded local video preprocessing and representative frame extraction.
- FFmpeg/ffprobe support in the Home Assistant image for screen-recording metadata inspection and frame extraction.
- Structured evidence summaries, observations, timestamps, confidence labels and ambiguity warnings kept separate from the editable requirement draft.
- Provider capability reporting for text, image, multiple-image, direct-video, frame-based video and structured-output support without exposing credentials.
- Bounded video limits for duration, payload size, image dimensions and extracted frame count.
- Evidence-aware requirement prompting that explicitly treats visible screenshot/video text as untrusted source material and avoids unsupported root-cause claims.
- More explainable deterministic duplicate/related-item ranking with weighted title/description/behaviour matching and human-readable match reasons.
- Frontend Evidence analysis review section and clearer processing states for evidence preparation and analysis.
- ARM64 CI smoke checks confirming ffmpeg/ffprobe are present and can generate, inspect and extract a frame from a tiny video fixture.

### Changed

- Video evidence is now analysed through bounded locally extracted frames when the configured provider supports images. Direct native provider video is not claimed by the current OpenAI/OpenAI-compatible path.
- Assisted Requirements status now exposes non-secret provider capabilities.
- The analysis request continues to remain synchronous because the bounded 120-second/6-frame pipeline fits the existing Home Assistant ingress request model without adding job infrastructure.
- Application, frontend and Home Assistant app version metadata updated to 0.5.1.

### Security and control

- Original evidence remains authoritative and is uploaded to the Register item only after explicit user confirmation.
- Extracted frames are transient and created only in temporary directories; they are not persisted under `/config`.
- Model output remains validated by Pydantic and cannot execute commands, perform GitHub writes, change roadmap state or create Register items.
- Video payloads are size/duration/frame bounded and malformed media returns explicit warnings rather than crashing analysis.

### Not included

- Persisted `duplicate of` / `related to` relationship records remain future v0.5.x work.
- Native provider video input remains disabled until a documented provider path justifies it.
- No database migration is required for this release.

## [0.5.0] - 2026-08-28

### Added

- First Assisted Requirements workflow from feedback and evidence through to an editable requirement draft and explicit Register-item creation.
- Optional AI provider service abstraction with Home Assistant configuration for enablement, provider, model, credential and base URL.
- Structured AI suggestions for title, item type, description, actual/expected behaviour, priority, acceptance criteria, testing instructions and roadmap phase.
- Screenshot/photo evidence support for compatible OpenAI-style multimodal chat providers, with original attachments retained for the final Register item.
- Deterministic same-project duplicate and related-item candidate narrowing before AI analysis.
- Roadmap-aware requirement context limited to relevant current/next phase information.
- Editable and reorderable acceptance criteria plus explicit roadmap-phase selection in the assisted review UI.
- AI disabled/not-configured states and a non-AI requirement creation path so core DevHub remains fully usable without AI.
- Regression CI checks for Home Assistant manifest metadata and ingress-safe Vite production asset paths.
- Backend coverage for successful mocked analysis, provider failure, invalid model output, candidate detection, roadmap validation and evidence warnings.

### Security and control

- AI drafts never create, approve, prioritise, schedule or release work automatically.
- Provider credentials remain server-side and are not returned by the status API.
- Model output is validated through Pydantic before it reaches the UI.
- Repository, roadmap, feedback and evidence content are treated as untrusted model context rather than executable instructions.
- OpenAI-compatible custom provider URLs require HTTPS and reject local/private literal IP addresses.
- No database migration is required because duplicate/related relationships remain advisory in this focused release.

### Limitations

- Video files are retained as Register evidence, but direct video understanding is not enabled in the initial provider path; DevHub reports this explicitly rather than pretending the video was analysed.
- Persisted duplicate/related-item relationship records remain future v0.5.x work if real usage shows they are valuable.

### Preserved

- v0.4.x Roadmap Intelligence, roadmap/changelog reconciliation and manual planning controls.
- v0.4.2 relative Vite asset base required for Home Assistant ingress.
- Modern `app_config` mapping and aarch64/amd64 Home Assistant app support.
- Existing GitHub synchronisation, Portfolio Dashboard, Release Builder, persistence and aarch64 startup smoke test.

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
- Reversible ignored roadmap phases that remain parsed but are excluded from planning selectors and automatic current/next phase resolution.
- Deterministic roadmap reconciliation states, reasoning and read-only update previews.
- Deterministic `CHANGELOG.md` semantic-version parsing and reconciliation for common semantic-version headings.
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
