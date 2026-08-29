# DevHub

DevHub is a Home Assistant app for managing a portfolio of GitHub-developed applications. It combines release visibility, pull-request status, structured roadmaps, a defect/enhancement register, feedback evidence, acceptance criteria, release planning, deterministic roadmap/release reconciliation and optional Assisted Requirements.

## v0.5.5 capabilities

- Home Assistant app packaging with ingress.
- FastAPI backend, React/Vite frontend and SQLite persistence.
- GitHub repository URL onboarding and project discovery.
- Compact responsive Portfolio dashboard with scan-first release, PR, CI, roadmap-next-phase and sync state.
- Portfolio summary metrics for total projects, CI attention, open PRs and release metadata gaps.
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

### App configuration

DevHub accepts these Home Assistant options:

- `github_token`: optional GitHub token. Public repositories work without a token but are subject to lower unauthenticated API rate limits. A token is required for private repositories.
- `github_owner`: optional default GitHub owner/account.
- `ai_enabled`: enables Assisted Requirements analysis. Defaults to `false`.
- `ai_provider`: `openai` or `openai-compatible`.
- `ai_model`: model identifier supplied by the configured provider. DevHub deliberately does not hard-code a default model.
- `ai_api_key`: provider API credential.
- `ai_base_url`: only used for `openai-compatible`; custom URLs must use HTTPS.

Credentials are consumed from Home Assistant options at runtime. GitHub and AI API keys are never committed to this repository and are never returned by the DevHub API.

If AI is disabled or not configured, all existing DevHub functionality remains available and the feedback flow offers a non-AI requirement creation path.

## Assisted Requirements

The workflow is deliberately assisted rather than autonomous:

```text
Feedback
  -> optional screenshots/photos/screen-recording evidence
  -> bounded evidence preprocessing
  -> evidence summary and observations
  -> structured requirement suggestion
  -> user review/edit
  -> explicit Create Register Item
```

DevHub may suggest:

- title;
- item type;
- description;
- actual and expected behaviour;
- priority;
- acceptance criteria;
- testing instructions;
- a relevant current/next roadmap phase;
- possible duplicate or related Register items.

Every suggested requirement field remains editable. Acceptance criteria can be added, removed and reordered. The user can discard the draft, cancel, choose a different roadmap phase, or continue without AI.

Analysis alone never creates a Register item. It also never approves work, assigns release scope, changes roadmap state, edits `ROADMAP.md`/`CHANGELOG.md`, executes GitHub writes or performs a release.

### Evidence Intelligence

Images and screen recordings are handled as untrusted evidence rather than instructions.

For screenshots/photos, DevHub sends a bounded set of image inputs to compatible multimodal providers. Multiple images can be analysed as a related evidence set.

For supported screen recordings (`video/mp4`, QuickTime/MOV and WebM), DevHub does not send the full video to the provider. Instead it:

1. validates and decodes the bounded analysis payload;
2. inspects video metadata locally with `ffprobe`;
3. analyses at most the first 120 seconds;
4. extracts at most six representative frames with `ffmpeg`;
5. scales extracted frames to at most 1280 pixels wide;
6. sends those representative frames to an image-capable provider;
7. asks for structured evidence observations and a concise evidence summary;
8. deletes transient video/frame processing artefacts when analysis finishes.

The video analysis payload is capped at 50 MB. Original Register attachments still use the existing attachment API and may be up to the normal 100 MB attachment limit.

The current OpenAI/OpenAI-compatible Chat Completions path deliberately reports native/direct video support as unavailable. Video is analysed through bounded extracted frames instead of depending on undocumented direct-video behaviour.

Evidence analysis is shown separately from the editable requirement draft. Observations may include a source filename, timestamp, confidence label and whether the statement is direct, inferred or ambiguous. DevHub explicitly instructs the model not to infer a technical root cause from symptoms unless the evidence actually supports it.

Visible text in screenshots and video frames is treated as untrusted source material. It cannot trigger shell commands, GitHub writes, roadmap changes, Register creation or release execution.

### Duplicate and related detection

Before model analysis, DevHub performs deterministic same-project matching against structured Register fields including title, description, actual behaviour and expected behaviour. Matching uses weighted local similarity and returns a short explanation such as `similar title` or `similar actual behaviour`.

Stronger matches are shown as **Possible duplicate** and weaker matches as **Possibly related**. These remain advisory. DevHub does not automatically merge, reject or link work.

## Portfolio dashboard

Portfolio remains the main operational view, but the default presentation is deliberately compact. Each collapsed project card surfaces project identity, current release, CI status, next roadmap phase, open PR count and sync freshness. Missing release metadata and unhealthy states are visually emphasised while normal zero/healthy states remain quiet.

The Portfolio header contains an icon-only refresh action plus a single Create `+` action. Create opens Add Project and Add Feedback without duplicating their underlying workflows.

Project cards can be expanded in place to show repository identity and description, release source, current roadmap phase, last merged PR and the existing Roadmap and Project Details actions. On mobile, the dashboard targets two cards across where practical, with a single-column fallback below narrow phone widths.

If GitHub refresh fails, DevHub retains last-known-good metadata and marks the project degraded instead of clearing useful data.

## Roadmap Intelligence

`ROADMAP.md` remains authoritative. DevHub parses common version, phase, milestone, planned/current/completed/future and bullet/task-list structures into relational roadmap snapshots, phases and items.

Roadmap source order is preserved for display, but lifecycle planning is resolved separately. For concrete semantic versions, automatic next-phase candidates must be greater than the current detected release. A lower version cannot become the next phase merely because it appears later in the Markdown document. Version bands such as `v0.5.x` are matched to concrete releases in that minor line, and later bands such as `v0.6.x` remain valid future candidates. If no later versioned phase exists, a planned `Future` section may become the next planning bucket.

The Roadmap workflow provides:

- **Structured** and **Raw Markdown** views;
- automatic current released phase and next planned phase detection;
- deterministic lifecycle badges for historical/released, current/released, future/planned, Future, ignored and unable-to-determine states;
- explicit current/next phase selection with clear **Detected**, **User confirmed** or **User override** labelling;
- clearing an override to return to automatic detection;
- reversible **Ignore in DevHub planning** controls for false-positive or non-planning sections;
- automatic exclusion of ordinary historical phases from planning without requiring them to be ignored;
- linked Register items and planned/completed releases for phase context;
- manual **Reparse Roadmap** support.

Ignoring or overriding a phase changes only DevHub-managed metadata. Historical lifecycle classification is not the same as ignoring a phase. DevHub does not automatically modify `ROADMAP.md`.

## Roadmap reconciliation

DevHub compares available deterministic evidence including the detected GitHub version, version source, DevHub release records, associated roadmap phase, parsed roadmap items and linked/selected Register scope.

Possible roadmap reconciliation states are **Reconciled**, **Reconciliation recommended**, **Reconciliation required** and **Unable to determine**.

Project Details separates repository state from DevHub's internal release-history completeness. A matching GitHub release, roadmap phase and current changelog can be shown as repository-reconciled while separately reporting that DevHub has no matching release record. This does not cause DevHub to create a release record automatically.

Project Details explains the reasons and provides a read-only suggested reconciliation preview. Free-form roadmap bullets are not treated as perfect implementation mappings, and uncertain evidence remains explicit. DevHub never edits or commits `ROADMAP.md` or `CHANGELOG.md` as part of reconciliation.

## Changelog reconciliation

`CHANGELOG.md` remains authoritative. DevHub recognises common semantic-version headings, skips `Unreleased` when resolving the latest documented release, and reports Current/Ahead/Reconciliation/Unable-to-determine states without automatically editing the file.

## Register and roadmap association

Register items may reference a parsed roadmap phase while retaining a separate target release. Release records may also reference a roadmap phase independently of individual Register-item associations.

## Roadmap-aware release planning

The Next Release Builder shows the current detected release, current/next roadmap phase, explicit target roadmap phase and suggested Register scope. Historical phases are excluded from ordinary planning choices. Nothing is automatically selected.

Generated release prompts include relevant roadmap, reconciliation and changelog context while preserving manual scope selection.

## GitHub synchronisation diagnostics

Settings provides operational diagnostics including sync attempts, latest commit/roadmap SHAs, version source, CI state, changelog state, rate-limit information, backoff state and last error.

## Home Assistant ingress and mobile behaviour

Frontend production assets use Vite `base: './'` so JS/CSS remain relative to the Home Assistant ingress path. CI explicitly rejects root-absolute `/assets/...` paths. The Assisted Requirements modal and existing dashboard layouts avoid page-level horizontal scrolling on portrait mobile.

Portfolio cards use a responsive two-column phone layout where practical, fall back to one column below 420 px, clamp long card content, and use a safe-area-aware Create bottom sheet. Roadmap lifecycle cards, evidence file names, capability notices, observation cards and requirement controls also wrap within narrow mobile viewports rather than forcing page-level horizontal scrolling.

## Persistent data

Runtime data that must not be committed includes SQLite data, roadmap/changelog cache metadata, project logos, uploaded screenshots/photos/videos and API credentials.

DevHub stores feedback attachments in `/config/uploads`, project artwork in `/config/project-logos`, and SQLite at `/config/devhub.db`.

Evidence-processing frames are transient and are not stored under `/config`.

## Development

### Backend

```bash
cd devhub
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python -m pytest backend/tests -q
uvicorn backend.app.main:app --reload --port 8099
```

Video Evidence Intelligence requires `ffmpeg` and `ffprobe` at runtime. They are installed in the production Home Assistant image.

### Frontend

```bash
cd devhub/frontend
npm install --no-audit --no-fund
npm run lint
npm test
npm run build
npm run dev
```

## Database migrations

Alembic is configured under `devhub/migrations`, and app startup runs `alembic upgrade head` before FastAPI. v0.5.5 does not require a database migration because the Portfolio redesign reuses existing project, GitHub and roadmap metadata.

## CI and startup protection

CI verifies:

- backend tests including Roadmap Intelligence lifecycle, Assisted Requirements and Evidence Intelligence deterministic/mocked-provider tests;
- frontend type/lint checks and tests;
- frontend production build;
- ingress-safe relative production asset paths;
- compact Portfolio header, summary, accordion and responsive-grid source safeguards;
- Home Assistant manifest keeps `app_config`, aarch64 support and no deprecated `armv7` declaration;
- aarch64 image build;
- `ffmpeg` and `ffprobe` availability inside the production aarch64 image;
- tiny deterministic video generation, metadata inspection and representative-frame extraction inside the aarch64 image;
- aarch64 container startup and `/api/health` reporting the release version.

## Release process

DevHub uses semantic versioning. Releases are developed on focused branches from latest merged `main`, fully tested in a PR, and merged only when required checks are green. Schema changes require forward Alembic migrations; releases without schema changes do not add empty migrations.
