# DevHub

DevHub is a Home Assistant add-on for managing a portfolio of GitHub-developed applications. It combines release visibility, pull-request status, structured roadmaps, a defect/enhancement register, feedback evidence, acceptance criteria, release planning and roadmap-aware development prompts.

## v0.4.0 capabilities

- Home Assistant add-on packaging with ingress.
- FastAPI backend, React/Vite frontend and SQLite persistence.
- GitHub repository URL onboarding and project discovery.
- Responsive Portfolio dashboard with release, PR, CI and sync state.
- Project logo/icon upload stored in persistent runtime storage.
- Deterministic Roadmap Intelligence for common Markdown roadmap structures.
- Structured and Raw Markdown roadmap views.
- Roadmap snapshots, phases and items stored relationally.
- Optional register-item association with roadmap phases.
- Roadmap-aware filtering and Next Release Builder suggestions.
- Structured roadmap context in generated release prompts.
- GitHub Release to Git tag version fallback with source tracking.
- Richer CI aggregation using GitHub check-runs and combined commit status.
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
      -> deterministic roadmap parser
```

Runtime state is stored under the Home Assistant add-on configuration mapping (`/config` inside the add-on) so database, project icons, roadmap snapshots and feedback attachments survive container replacement/upgrades.

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

Portfolio remains the main operational view. Each project card shows:

- project artwork and repository;
- latest detected release/version and source where available;
- open PR count and latest open PR;
- most recently merged PR and relative merge age;
- current CI state;
- GitHub sync state and age;
- Roadmap and Project Details actions.

Use **Refresh All** to immediately reconcile all active projects with GitHub. If GitHub refresh fails, DevHub keeps the last successfully cached metadata and marks the project as stale/degraded instead of blanking the card.

## Roadmap Intelligence

DevHub keeps the configured `ROADMAP.md` file as the authoritative source. It retrieves that Markdown and parses common structures such as:

- version headings such as `v1.2.0 Dashboard`;
- version ranges such as `v1.3.x`;
- phase and milestone headings;
- planned/current/completed/future sections;
- bullet items and Markdown task-list items.

The Roadmap view provides:

- **Structured** view for parsed phases and roadmap items;
- **Raw Markdown** view for the original source;
- current and next phase summaries where they can be resolved reliably;
- parse status and warnings;
- **Reparse Roadmap** for manual parser refresh.

Roadmap snapshots are cached using the GitHub source-file SHA. DevHub reuses the existing parsed snapshot when the roadmap has not changed instead of repeatedly parsing the same content.

DevHub does not automatically rewrite `ROADMAP.md` in v0.4.0.

## Register and roadmap association

Register items may optionally reference a parsed roadmap phase while retaining their separate target-release value.

This allows a work item to have, for example:

```text
Roadmap phase: v0.4.x Roadmap Intelligence
Target release: v0.4.1
```

The Register can be filtered by project and roadmap phase. Unassigned work remains visible.

## Roadmap-aware release planning

The Next Release Builder shows the project's current release and next parsed roadmap phase. Items explicitly associated with that next phase are highlighted as suggested scope, but DevHub does not automatically select them.

Generated release prompts include structured current/next roadmap context and roadmap phase assignment for selected register items while still instructing the development workflow to verify the raw roadmap.

## Version detection

DevHub uses this hierarchy when detecting project versions:

1. latest GitHub Release;
2. semantic Git tag;
3. Unknown when neither can be determined safely.

The detected source is stored with the GitHub cache. DevHub does not invent a version.

## CI status

CI state combines GitHub check-run data with the combined commit-status endpoint where available. DevHub maps the result into Passing, Failing, Pending or Unknown without reporting Passing when a known check is failing or still running.

## Adding a project

1. Open **Projects** or select **Add Project** from Portfolio.
2. Paste a GitHub repository URL, for example `https://github.com/stunwill/mathquest-home-assistant`.
3. DevHub validates the URL and retrieves repository metadata.
4. Review the detected repository, default branch, roadmap and changelog paths.
5. Optionally upload a project logo/icon.
6. Save the project.

## Synchronisation

DevHub refreshes GitHub metadata through a backend scheduler approximately every 15 minutes for active projects, when **Refresh All** is selected, and when Project Details requests a project refresh.

The last successful GitHub data is retained if a later refresh fails. Roadmap snapshots are refreshed only when needed and are reused when the source SHA is unchanged.

## Persistent data

The following are runtime data and must not be committed:

- SQLite database;
- roadmap snapshots/cache;
- project logos/icons;
- uploaded screenshots/photos;
- uploaded videos/screen recordings;
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

Alembic is configured under `devhub/migrations`. The add-on startup runs:

```bash
alembic upgrade head
```

before starting FastAPI. The runtime image sets `PYTHONPATH=/app` so Alembic and Uvicorn resolve `backend.app` consistently.

v0.4.0 adds a forward migration for roadmap snapshots, phases, items and register-item phase associations. Existing v0.3.x data is retained.

## CI and startup protection

CI runs:

- backend tests, including deterministic roadmap parser tests;
- frontend type/lint checks;
- frontend tests;
- frontend production build;
- aarch64 Home Assistant image build;
- aarch64 container startup smoke test against `/api/health`.

The startup smoke test verifies that migrations complete and FastAPI starts inside the built ARM64 image.

## Release process

DevHub uses semantic versioning.

1. Create a focused development/release branch from latest `main`.
2. Implement and test the release scope.
3. Add forward-only Alembic migrations where the schema changes.
4. Update `ROADMAP.md`, `CHANGELOG.md`, README and version metadata.
5. Open a PR into `main`.
6. Require backend, frontend, aarch64 add-on build and startup smoke CI to pass before merge.
7. Finalise the tag/GitHub release after merge.

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

Current development release: **0.4.0**
