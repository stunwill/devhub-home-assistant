# DevHub

DevHub is a private Home Assistant add-on for managing a portfolio of GitHub-developed applications. It combines release visibility, per-project roadmaps, a defect/enhancement register, feedback evidence, acceptance criteria, release planning and roadmap-aware development prompts.

## v0.1.0 capabilities

- Home Assistant add-on packaging with ingress.
- FastAPI backend, React/Vite frontend and SQLite persistence.
- Project portfolio with GitHub release metadata.
- Per-project Markdown roadmap viewing.
- Defect and enhancement register.
- Mobile-friendly feedback capture with multiple image/video uploads.
- Acceptance criteria and testing instructions.
- Next Release Builder and release prompt preview/copy.
- Release records, GitHub reconciliation and acceptance testing foundation.

## Architecture

```text
Home Assistant
  -> DevHub add-on / ingress
      -> React frontend
      -> FastAPI REST API
      -> SQLite + attachment storage under /config
      -> GitHub REST API
```

Runtime state is stored under the Home Assistant add-on configuration mapping (`/config` inside the add-on) so database and attachment data survive container replacement/upgrades.

## Home Assistant installation

This repository is private. Home Assistant's standard unauthenticated custom add-on repository flow is intended for repositories it can fetch directly, so a private source repository may require an authenticated or local distribution approach.

For v0.1.0, the supported safe approach is to deploy/copy the `devhub` add-on directory into the Home Assistant local add-ons area, then reload the Add-on Store and install DevHub as a local add-on. This keeps source private and avoids embedding repository credentials into source control.

A future DevHub release will improve private repository distribution/update automation. See `ROADMAP.md`.

### Add-on configuration

DevHub accepts these Home Assistant add-on options:

- `github_token`: GitHub token used by the running DevHub app to access configured repositories. Store this only in add-on options.
- `github_owner`: optional default GitHub owner/account.

The token is never committed to this repository and is not returned by the DevHub API.

## GitHub token permissions

Use the least privilege required for repositories DevHub needs to read. v0.1.0 primarily reads repository metadata, releases, files and pull request metadata. Private repositories must be accessible to the supplied credential.

## Persistent data

The following are runtime data and must not be committed:

- SQLite database
- uploaded screenshots/photos
- uploaded videos/screen recordings
- API credentials and tokens

DevHub stores attachments in `/config/uploads` and the SQLite database at `/config/devhub.db` inside the add-on.

## Development

### Backend

```bash
cd devhub
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pytest backend/tests -q
uvicorn backend.app.main:app --reload --port 8099
```

### Frontend

```bash
cd devhub/frontend
npm install
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

before starting FastAPI.

## Release process

DevHub uses semantic versioning.

1. Create a focused development/release branch.
2. Implement and test the release scope.
3. Update `ROADMAP.md`, `CHANGELOG.md`, README and version metadata where required.
4. Open a PR into `main`.
5. Merge only when CI is passing.
6. Finalise tag/GitHub release after merge.
7. Home Assistant/local add-on deployment should occur from an explicit released version, not automatically from every merged PR.

A merge to `main` must not silently replace the running add-on.

## Security

- Secrets are excluded from Git.
- Uploaded filenames are sanitised.
- Upload types and size are validated.
- Attachments are restricted to DevHub's upload directory.
- Markdown returned by GitHub is sanitised before backend HTML rendering.
- Database access uses SQLAlchemy.
- Home Assistant ingress is the expected access boundary for the add-on.

## Project documents

- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)

## Version

Current foundation release: **0.1.0**
