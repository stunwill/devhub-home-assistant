# DevHub Home Assistant Changelog

This changelog is packaged with the DevHub Home Assistant app so release notes are visible from the Home Assistant app/add-on store. The repository-level `CHANGELOG.md` remains the detailed product changelog.

## 0.5.9

- Fixed version discovery for Home Assistant projects whose add-on manifest lives in a product directory rather than a repository-name-derived path.
- DevHub now discovers top-level packaged `config.yaml` manifests and selects the highest valid manifest version when more than one exists.
- MediaHub-style repositories now resolve the active `0.10.0-dev` development version instead of stale `0.1.1-dev` metadata.
- Correct version evidence allows Roadmap Intelligence to resolve `v0.10.0` as the active phase and prevents delivered `v0.9.0` from appearing as the next phase.
- Added regression coverage for nested manifests and the MediaHub roadmap lifecycle case.
- Preserved ingress, Portfolio refresh/CI fixes, Evidence Intelligence and aarch64 startup protections.

## 0.5.8

- Added editable friendly project names while preserving GitHub repository identity.
- Linked a single OPEN PR Portfolio chip directly to its GitHub pull request.
- Fixed roadmap Next Phase detection so stale historical phases cannot override a newer detected release.
- Improved manual refresh with a rotating indicator, completion/failure feedback and immediate refreshed Portfolio/roadmap data.
- Fixed stale Pending CI by prioritising completed GitHub check-runs and associating cached CI with the latest commit SHA.
- Preserved Home Assistant ingress, compact mobile Portfolio navigation, Evidence Intelligence and aarch64 startup protections.

## 0.5.7

- Fixed synchronisation timestamps so newly refreshed projects display accurate relative times instead of appearing hours old in local time zones.
- Added deterministic release-version fallback through GitHub Release, Git tag, Home Assistant manifest, CHANGELOG, frontend package metadata and backend APP_VERSION evidence.
- Prioritised Portfolio cards by actionable pull-request activity, with open-PR projects first and oldest waiting work first.
- Added prominent amber OPEN PR chips while keeping zero-PR states visually muted.
- Added version evidence and open-PR detail to diagnostics while preserving the compact Portfolio layout.
- Preserved Home Assistant ingress, mobile navigation, Roadmap Intelligence, Evidence Intelligence and aarch64 startup protections.

## 0.5.6

- Replaced the permanently expanded mobile navigation block with a compact hamburger drawer beside the DevHub brand.
- Kept the Portfolio refresh and Create `+` actions in the compact mobile header.
- Preserved desktop sidebar navigation and the compact two-column mobile Portfolio cards.
- Added mobile navigation accessibility, Escape/outside-click dismissal and safe-area-aware drawer spacing.
- Preserved Home Assistant ingress, Roadmap Intelligence, Evidence Intelligence and aarch64 startup protections.

## 0.5.5

- Redesigned Portfolio around compact scan-first project cards with release, CI, next phase, PR and sync status visible at a glance.
- Replaced large Portfolio action buttons with a refresh icon and one Create `+` menu for Add Project and Add Feedback.
- Added compact portfolio summary metrics and expandable per-project details.
- Improved responsive card density with two-column mobile layouts where practical and a narrow-screen fallback.
- Preserved Home Assistant ingress, Roadmap Intelligence, Evidence Intelligence and aarch64 startup protections.

## 0.5.4

- Fixed Roadmap Intelligence lifecycle ordering so a lower released version can no longer become the automatically detected next phase.
- Added deterministic historical, current, future and Future-bucket lifecycle classification, including support for version bands such as `v0.5.x`.
- Improved Project Details lifecycle badges and reduced repetitive historical planning controls on mobile.
- Improved reconciliation messaging when GitHub release history is valid but the matching DevHub release record is missing.
- Preserved Home Assistant ingress, Evidence Intelligence and aarch64 startup protections.

## 0.5.3

- Optimised DevHub for phones and small tablets with responsive navigation, action groups, cards, forms, tables and project details.
- Prevented long repository names, project names, errors and roadmap content from forcing page-wide horizontal scrolling.
- Improved mobile touch targets and made Assisted Requirements use a full-screen mobile workflow.
- Preserved Home Assistant ingress-safe frontend assets and API routing.

## 0.5.2

- Fixed Home Assistant ingress API routing so project loading and GitHub repository onboarding stay inside the active ingress path.
- Restored adding projects such as `stunwill/fynvo-home-assistant` without the previous routing `404: Not Found`.
- Updated release metadata so Home Assistant can detect and install the corrected version.

## 0.5.1

- Added Evidence Intelligence for Assisted Requirements, including bounded FFmpeg/ffprobe video preprocessing and representative frame extraction.
- Added structured evidence summaries, observations and confidence information while retaining explicit user review before Register creation.

## 0.5.0
