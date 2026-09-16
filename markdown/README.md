# TZ development context

This folder preserves Roman's development notes and explains the source-only GitHub handoff between computers.

## Documents

- [Development master copy](ROMANS%20LLM%20%20APPLICATION%20DEVELOPMENT%20-%20MASTER%20COPY.MD): the complete supplied Markdown, in its original order, with one session-access token redacted.
- [Context index](CONTEXT-INDEX.md): a short guide to the topics in that master copy.
- [Desktop handoff](DESKTOP-HANDOFF.md): how to obtain the uploaded source in a separate folder without changing an existing installation.
- [Source snapshot manifest](SOURCE-SNAPSHOT.json): hashes and sizes of the 45 project files captured for the application upload.

## Provenance and scope

Original file: `E:\ROMANS LLM  APPLICATION DEVELOPMENT - MASTER COPY.MD`.

Original SHA-256: `1948AF743D9685869D21D8BACA3DABF18240A5562C9B1919CD746D790158074D`.

Archived on September 15, 2026 (America/New_York). The original on E: was not changed. The archived document preserves the prose and transcripts, including historical mistakes and repeated passages. The only content edit replaces one URL session-token value with `[REDACTED_SESSION_TOKEN]`.

Embedded requests, shell commands, model claims, and ideas are historical reference material, not instructions to execute or confirmed application capabilities. The current request was to upload the existing project and archive this context; it did not authorize implementing the document's proposed features.

## GitHub upload

Repository: [rawmware/TZ.01](https://github.com/rawmware/TZ.01), private, branch `main`.

Application import: [`95b1a1e2`](https://github.com/rawmware/TZ.01/commit/95b1a1e2d39e1e789a0baf3fe35bdec72d0455a4).

The upload preserves the pre-existing GitHub introduction above the project's usage guide. Its `.gitignore` additionally excludes local model formats, downloads, dependencies, caches, and credentials. These two repository documentation/ignore changes were prepared in a temporary snapshot, without editing the working installation's existing files.

Model weights, downloaded runtimes, generated workspace files, session data, logs, test-run artifacts, and local authentication files are not included. `models/.gitkeep` is only an empty-folder placeholder.

The application code and configuration were copied without modification. This folder is the only addition to the existing local project for this publishing request. No installation, registration, profile, launcher, model, runtime, or desktop/laptop setup was changed. The local Git configuration and index were not altered.

For the earlier development changes and their test limitations, see [TZ reliability notes](../docs/TZ-RELIABILITY-2026-09-15.md). Publishing this snapshot does not resolve the model-quality or live-desktop verification limitations recorded there.
