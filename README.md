# DevHub

DevHub is a Home Assistant add-on for managing a portfolio of GitHub-developed applications. It combines release visibility, pull-request status, per-project roadmaps, a defect/enhancement register, feedback evidence, acceptance criteria, release planning and roadmap-aware development prompts.

## v0.3.0 capabilities

- Home Assistant add-on packaging with ingress.
- FastAPI backend, React/Vite frontend and SQLite persistence.
- GitHub repository URL onboarding and project discovery.
- Polished responsive Portfolio dashboard with project cards for release, open PR, last merged PR, CI and sync state.
- Project logo/icon upload stored in persistent runtime storage.
- Per-project Markdown roadmap viewing and changelog detection.
- Backend GitHub synchronisation approximately every 15 minutes, including when no browser is open.
- Manual Refresh All plus per-project refresh and stale/error retention.
- Defect and enhancement register.
- Mobile-friendly feedback capture with multiple image/video uploads.
- Acceptance criteria and testing instructions.
- Next Release Builder and release prompt preview/copy.
- Release records, GitHub reconciliation and acceptance testing foundation.
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
```

Runtime state is stored under the Home Assistant add-on configuration mapping (`/config` inside the add-on) so database, project icons and feedback attachments survive container replacement/upgrades.

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

Portfolio is the main operational view. Each project card shows:

- project artwork and repository;
- latest detected GitHub release;
- open PR count and latest open PR;
- most recently merged PR and relative merge age;
- current CI state;
- GitHub sync state and age;
- Roadmap and Project Details actions.

Use **Refresh All** to immediately reconcile all active projects with GitHub. If GitHub refresh fails, DevHub keeps the last successfully cached metadata and marks the project as stale/degraded instead of blanking the card.

The dashboard uses real GitHub/project data. Mock values are limited to automated tests.

## Adding a project

1. Open **Projects** or select **Add Project** from Portfolio.
2. Paste a GitHub repository URL, for example `https://github.com/stunwill/mathquest-home-assistant`.
3. DevHub validates the URL and retrieves repository metadata.
4. Review the detected repository, default branch, roadmap and changelog paths.
5. Optionally upload a project logo/icon.
6. Save the project.

GitHub-managed metadata is refreshed rather than manually maintained. This includes repository description, visibility, release information, open PRs, last merged PR, latest commit and CI status where GitHub exposes it.

## Synchronisation

DevHub refreshes GitHub metadata:

- through a backend scheduler approximately every 15 minutes for active projects;
- when **Refresh All** is selected;
- when Project Details requests a project refresh.

The last successful GitHub data is retained if a later refresh fails, and the project displays a stale/error state rather than blanking known information.

## Roadmaps and changelogs

During onboarding DevHub checks common locations such as:

- `ROADMAP.md`
- `docs/ROADMAP.md`
- `CHANGELOG.md`
- `docs/CHANGELOG.md`

Paths can be overridden for repositories that use another structure.

## Project artwork

Project logos/icons support SVG, PNG, WebP and JPEG. Uploaded artwork is stored under DevHub runtime storage and is not committed to Git.

## Persistent data

The following are runtime data and must not be committed:

- SQLite database
- project logos/icons
- uploaded screenshots/photos
- uploaded videos/screen recordings
- API credentials and tokens

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

## CI and startup protection

CI runs:

- backend tests;
- frontend type/lint checks;
- frontend tests;
- frontend production build;
- aarch64 Home Assistant image build;
- aarch64 container startup smoke test against `/api/health`.

The startup smoke test is intended to catch failures that only appear after the Docker image is launched, including migration/import regressions.

## Release process

DevHub uses semantic versioning.

1. Create a focused development/release branch from latest `main`.
2. Implement and test the release scope.
3. Add forward-only Alembic migrations where the schema changes.
4. Update `ROADMAP.md`, `CHANGELOG.md`, README and version metadata.
5. Open a PR into `main`.
6. Require backend, frontend, aarch64 add-on build and startup smoke CI to pass before merge.
7. Finalise the tag/GitHub release after merge.
8. Home Assistant should only offer an update from an explicit new add-on version, not from every arbitrary merged commit.

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

Current development release: **0.3.0**
