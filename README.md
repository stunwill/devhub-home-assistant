# DevHub

DevHub is a Home Assistant app for managing a portfolio of GitHub-developed applications. It combines release visibility, pull-request status, structured roadmaps, a defect/enhancement register, feedback evidence, acceptance criteria, release planning, deterministic roadmap/release reconciliation and optional Assisted Requirements.

## v0.5.0 capabilities

- Home Assistant app packaging with ingress.
- FastAPI backend, React/Vite frontend and SQLite persistence.
- GitHub repository URL onboarding and project discovery.
- Responsive Portfolio dashboard with release, PR, CI and sync state.
- Project logo/icon upload stored in persistent runtime storage.
- Deterministic Roadmap Intelligence for common Markdown roadmap structures.
- Structured and Raw Markdown roadmap views.
- Automatic current/next phase detection plus user confirmation/override controls.
- Reversible ignored roadmap phases without changing `ROADMAP.md`.
- Roadmap snapshots, phases and items stored relationally.
- Register-item and release associations with roadmap phases.
- Deterministic roadmap reconciliation with reasons and read-only update previews.
- Deterministic `CHANGELOG.md` version parsing and reconciliation.
- Roadmap-aware filtering and Next Release Builder suggestions without automatic scope selection.
- Focused release prompts using current/next/selected phase, reconciliation and changelog context.
- Optional Assisted Requirements workflow that converts feedback into an editable structured requirement draft.
- Screenshot/photo evidence analysis for compatible multimodal providers, plus retained image/video evidence on confirmed Register items.
- Deterministic duplicate/related candidate narrowing against same-project Register items.
- Suggested acceptance criteria, testing instructions, priority, item type and optional roadmap phase with explicit user review.
- GitHub Release to Git tag version fallback with version-source tracking.
- CI aggregation using GitHub check-runs and combined commit status.
- GitHub synchronisation diagnostics with rate-limit and retry/backoff visibility.
- Backend GitHub synchronisation approximately every 15 minutes, including when no browser is open.
- Manual Refresh All, per-project refresh and Reparse Roadmap actions.
- Raspberry Pi 5/aarch64 Home Assistant image build validation plus startup smoke testing in CI.

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
      -> reconciliation service
      -> optional Assisted Requirements provider service
```

Runtime state is stored under the Home Assistant app configuration mapping (`/config` inside the app), so database, project icons, roadmap snapshots and feedback attachments survive container replacement/upgrades.

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

The v0.5.0 workflow is deliberately assisted rather than autonomous:

```text
Feedback
  -> optional screenshots/photos/video evidence
  -> Analyse & Draft Requirement
  -> structured suggestion
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

Every suggested field remains editable. Acceptance criteria can be added, removed and reordered. The user can discard the draft, cancel, choose a different roadmap phase, or continue without AI.

Analysis alone never creates a Register item. It also never approves work, assigns release scope, changes roadmap state, edits `ROADMAP.md`/`CHANGELOG.md`, executes GitHub writes or performs a release.

### Evidence handling

Screenshot/photo evidence is sent to compatible OpenAI-style multimodal chat providers as image input, within a bounded analysis payload. Multiple selected files remain browser-side until the user explicitly creates the Register item, at which point the original files are uploaded through the existing attachment API.

Video evidence is accepted and retained with the final Register item. Direct video understanding is not enabled in the initial v0.5.0 provider path. DevHub reports that limitation explicitly instead of claiming the recording was analysed.

The analysis context is intentionally bounded to the supplied feedback, relevant project metadata, current/next roadmap context and a small local set of potential related Register items. DevHub does not send entire repositories, roadmaps, changelogs or the full Register to the AI provider.

### Duplicate and related detection

Before model analysis, DevHub performs deterministic same-project token-overlap matching against structured Register fields. Stronger matches are shown as **Possible duplicate** and weaker matches as **Possibly related**.

These are advisory only in v0.5.0. DevHub does not automatically merge, reject or link work, and no database migration is introduced solely for relationships.

## Portfolio dashboard

Portfolio remains the main operational view. Each project card shows project identity, latest detected release/version, open PRs, last merged PR, CI and GitHub sync state. Project Details contains richer reconciliation and diagnostics information so Portfolio cards remain compact.

Use **Refresh All** to immediately refresh all active projects. If GitHub refresh fails, DevHub retains last-known-good metadata and marks the project degraded instead of clearing useful data.

## Roadmap Intelligence

`ROADMAP.md` remains authoritative. DevHub parses common version, phase, milestone, planned/current/completed/future and bullet/task-list structures into relational roadmap snapshots, phases and items.

The Roadmap workflow provides:

- **Structured** and **Raw Markdown** views;
- automatic current and next phase detection;
- explicit current/next phase selection with clear **Detected**, **User confirmed** or **User override** labelling;
- clearing an override to return to automatic detection;
- reversible **Ignore in DevHub planning** controls for false-positive or non-planning sections;
- linked Register items and planned/completed releases for phase context;
- manual **Reparse Roadmap** support.

Ignoring or overriding a phase changes only DevHub-managed metadata. DevHub does not automatically modify `ROADMAP.md`.

## Roadmap reconciliation

DevHub compares available deterministic evidence including the detected GitHub version, version source, DevHub release records, associated roadmap phase, parsed roadmap items and linked/selected Register scope.

Possible roadmap reconciliation states are **Reconciled**, **Reconciliation recommended**, **Reconciliation required** and **Unable to determine**.

Project Details explains the reasons and provides a read-only suggested roadmap reconciliation preview. Free-form roadmap bullets are not treated as perfect implementation mappings, and uncertain evidence remains explicit. DevHub never edits or commits `ROADMAP.md` as part of reconciliation.

## Changelog reconciliation

`CHANGELOG.md` remains authoritative. DevHub recognises common semantic-version headings, skips `Unreleased` when resolving the latest documented release, and reports Current/Ahead/Reconciliation/Unable-to-determine states without automatically editing the file.

## Register and roadmap association

Register items may reference a parsed roadmap phase while retaining a separate target release. Release records may also reference a roadmap phase independently of individual Register-item associations.

## Roadmap-aware release planning

The Next Release Builder shows the current detected release, current/next roadmap phase, explicit target roadmap phase and suggested Register scope. Nothing is automatically selected.

Generated release prompts include relevant roadmap, reconciliation and changelog context while preserving manual scope selection.

## GitHub synchronisation diagnostics

Settings provides operational diagnostics including sync attempts, latest commit/roadmap SHAs, version source, CI state, changelog state, rate-limit information, backoff state and last error.

## Home Assistant ingress and mobile behaviour

Frontend production assets use Vite `base: './'` so JS/CSS remain relative to the Home Assistant ingress path. CI explicitly rejects root-absolute `/assets/...` paths. The Assisted Requirements modal and existing dashboard layouts avoid page-level horizontal scrolling on portrait mobile.

## Persistent data

Runtime data that must not be committed includes SQLite data, roadmap/changelog cache metadata, project logos, uploaded screenshots/photos/videos and API credentials.

DevHub stores feedback attachments in `/config/uploads`, project artwork in `/config/project-logos`, and SQLite at `/config/devhub.db`.

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

Alembic is configured under `devhub/migrations`, and app startup runs `alembic upgrade head` before FastAPI. v0.5.0 does not require a new migration because Assisted Requirements drafts are non-persistent until explicit Register creation and duplicate/related relationships remain advisory.

## CI and startup protection

CI verifies:

- backend tests including Assisted Requirements deterministic/mocked-provider tests;
- frontend type/lint checks and tests;
- frontend production build;
- ingress-safe relative production asset paths;
- Home Assistant manifest keeps `app_config`, aarch64 support and no deprecated `armv7` declaration;
- aarch64 image build;
- aarch64 container startup and `/api/health` reporting the release version.

## Release process

DevHub uses semantic versioning. Releases are developed on focused branches from latest merged `main`, fully tested in a PR, and merged only when required checks are green. Schema changes require forward Alembic migrations; releases without schema changes do not add empty migrations.
