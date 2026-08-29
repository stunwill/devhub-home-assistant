# DevHub Home Assistant Changelog

This changelog is packaged with the DevHub Home Assistant app so release notes are visible from the Home Assistant app/add-on store. The repository-level `CHANGELOG.md` remains the detailed product changelog.

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

- Added the first Assisted Requirements workflow for converting feedback and evidence into an editable requirement draft.
- Added optional AI-assisted analysis while keeping the normal non-AI workflow available.
