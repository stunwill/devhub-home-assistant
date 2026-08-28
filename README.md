# DevHub

DevHub is a Home Assistant add-on for managing a portfolio of GitHub-developed applications. It combines release visibility, pull-request status, structured roadmaps, a defect/enhancement register, feedback evidence, acceptance criteria, release planning and deterministic roadmap/release reconciliation.

## v0.4.1 capabilities

- Home Assistant add-on packaging with ingress.
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
- GitHub Release to Git tag version fallback with version-source tracking.
- CI aggregation using GitHub check-runs and combined commit status.
- GitHub synchronisation diagnostics with rate-limit and retry/backoff visibility.
- Backend GitHub synchronisation approximately every 15 minutes, including when no browser is open.
- Manual Refresh All, per-project refresh and Reparse Roadmap actions.
- Raspberry Pi 5/aarch64 Home Assistant image build validation plus add-on startup smoke testing in CI.

## Architecture

```text
Home Assistant
  -> DevHub add-on / ingress
      -> React frontend
      -> FastAPI REST API
      -> SQLite + attachments + project artwork under /config
      -> GitHub REST API
      -> backend synchronisation task
      -> deterministic roadmap/changelog parsers
      -> reconciliation service
```

Runtime state is stored under the Home Assistant add-on configuration mapping (`/config` inside the add-on), so database, project icons, roadmap snapshots and feedback attachments survive container replacement/upgrades.

## Home Assistant installation

This repository is public and can be added to Home Assistant as a custom add-on repository.

Use the repository URL:

```text
https://github.com/stunwill/devhub-home-assistant
```

In Home Assistant, add the repository to the Add-on Store, refresh the store, then install DevHub. Updates are offered when the add-on version in `devhub/config.yaml` increases in a released repository state.

### Add-on configuration

DevHub accepts these Home Assistant add-on options:

- `github_token`: optional GitHub token. Public repositories work without a token but are subject to lower unauthenticated API rate limits. A token is required for private repositories.
- `github_owner`: optional default GitHub owner/account.

The token is consumed from Home Assistant add-on options at runtime. It is never committed to this repository and is not returned by the DevHub API.

## Portfolio dashboard

Portfolio remains the main operational view. Each project card shows project identity, latest detected release/version, open PRs, last merged PR, CI and GitHub sync state. Project Details contains the richer reconciliation and diagnostics information so the Portfolio cards remain compact.

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

Possible roadmap reconciliation states are:

- **Reconciled**
- **Reconciliation recommended**
- **Reconciliation required**
- **Unable to determine**

Project Details explains the reasons and provides a read-only suggested roadmap reconciliation preview. Free-form roadmap bullets are not treated as perfect implementation mappings, and uncertain evidence remains explicit. DevHub never edits or commits `ROADMAP.md` as part of reconciliation.

## Changelog reconciliation

`CHANGELOG.md` remains authoritative. DevHub deterministically recognises common headings such as:

```text
## [0.4.1]
## v0.4.1
## 0.4.1
```

`Unreleased` headings are skipped when looking for the latest documented release. Semantic `v` prefixes are normalised for comparison.

Changelog states are:

- **Current**
- **Changelog may require reconciliation**
- **Ahead of detected release**
- **Unable to determine**
- **Missing changelog**

DevHub does not automatically modify `CHANGELOG.md`.

## Register and roadmap association

Register items may reference a parsed roadmap phase while retaining a separate target release. Release records may also reference a roadmap phase independently of individual Register-item associations.

This keeps planning relationships explicit without forcing every roadmap bullet to correspond to a Register item.

## Roadmap-aware release planning

The Next Release Builder shows:

- current detected release;
- current roadmap phase and whether it is detected or user-confirmed;
- next roadmap phase;
- an explicit target roadmap phase for the planned release;
- suggested Register scope.

Suggested scope prioritises work explicitly assigned to the selected roadmap phase, then approved/planned items, then relevant unassigned work. Nothing is automatically selected.

Generated release prompts include the detected release and source, current/next phase state, selected release phase, relevant roadmap items, selected Register items, acceptance criteria, known reconciliation warnings and changelog state. Prompts explicitly instruct the development workflow to reconcile `ROADMAP.md` and `CHANGELOG.md` after implementation.

## Release history

Release history retains lifecycle traceability rather than replacing GitHub Releases. Release records can contain planned/actual version information, roadmap phase association, GitHub/PR links where recorded, selected scope and roadmap/changelog reconciliation states.

## Version detection

DevHub currently prefers:

1. latest GitHub Release;
2. semantic Git tag;
3. Unknown when neither can be determined safely.

The selected source is recorded and displayed. DevHub does not invent semantic meaning for arbitrary tag or changelog headings.

## CI status

CI combines GitHub check-run data with combined commit status where available. Project Details shows lightweight check counts. A known failing or running relevant check prevents DevHub from reporting the overall CI state as Passing.

## GitHub synchronisation diagnostics

Settings provides operational diagnostics for each project, including:

- last successful and attempted sync;
- sync state and last error;
- latest commit SHA;
- roadmap source SHA and parse time/state;
- detected version and source;
- CI state;
- changelog reconciliation state;
- GitHub API rate-limit remaining/limit/reset data where provided;
- active retry/backoff window.

DevHub coalesces roadmap/changelog content and metadata requests where practical, caches source SHAs and parsed state, and avoids reparsing unchanged files. Temporary GitHub failures trigger per-project backoff. One failing project does not block other projects from refreshing.

## Adding a project

1. Open **Projects** or select **Add Project** from Portfolio.
2. Paste a GitHub repository URL, for example `https://github.com/stunwill/mathquest-home-assistant`.
3. DevHub validates the URL and retrieves repository metadata.
4. Review the detected repository, default branch, roadmap and changelog paths.
5. Optionally upload a project logo/icon.
6. Save the project.

## Home Assistant ingress and mobile behaviour

Frontend/API paths remain relative so DevHub continues to operate through Home Assistant ingress instead of assuming the application is hosted at `/` externally. New roadmap, reconciliation, release and diagnostics layouts are responsive, wrap long phase titles and avoid page-level horizontal scrolling on portrait mobile. Dense tabular data may scroll locally where appropriate.

## Persistent data

Runtime data that must not be committed includes:

- SQLite database;
- roadmap/changelog cache metadata;
- project logos/icons;
- uploaded screenshots/photos/videos;
- API credentials and tokens.

DevHub stores feedback attachments in `/config/uploads`, project artwork in `/config/project-logos`, and the SQLite database at `/config/devhub.db` inside the add-on.

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

Alembic is configured under `devhub/migrations`. Add-on startup runs:

```bash
alembic upgrade head
```

before starting FastAPI. The runtime image preserves `PYTHONPATH=/app` so Alembic and Uvicorn resolve `backend.app` consistently.

v0.4.1 adds a forward migration from the v0.4.0 Roadmap Intelligence schema for phase overrides, changelog metadata, release-to-roadmap associations, reconciliation state and synchronisation/rate-limit/backoff diagnostics. Existing data is retained.

## CI and startup protection

CI runs:

- all backend tests, including roadmap parser, changelog parser, reconciliation, phase-selection and migration tests;
- frontend type/lint checks;
- frontend tests;
- frontend production build;
- aarch64 Home Assistant image build;
- aarch64 container startup smoke test against `/api/health`.

The startup smoke test proves the built image starts, migrations complete, FastAPI starts and `/api/health` responds.

## Release process

DevHub uses semantic versioning.

1. Create a focused release branch from latest merged `main`.
2. Implement and test the release scope.
3. Add a forward Alembic migration when the schema changes.
4. Reconcile `ROADMAP.md`, `CHANGELOG.md`, README and version metadata.
5. Open a PR into `main`.
6. Require backend, frontend, aarch64 build and startup smoke checks to pass before merge.
7. Finalise the appropriate tag/GitHub release after merge when release tooling is available.

## Security

- Secrets are excluded from Git.
- GitHub repository URLs are restricted to validated `github.com/owner/repository` URLs.
- Uploaded filenames are sanitised.
- Project artwork and feedback uploads have file type and size validation.
- Attachments and project artwork are restricted to DevHub runtime directories.
- Markdown returned by GitHub is sanitised before backend HTML rendering.
- Database access uses SQLAlchemy.
- Home Assistant ingress is the expected access boundary for the add-on.

## Project documents

- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)

## Version

Current development release: **0.4.1**
