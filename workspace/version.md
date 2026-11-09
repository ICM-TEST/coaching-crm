---
version: 0.3.3
released: 2026-11-09
---

# Structure version

The version of the rules this snapshot holds. Written only by Ross's `tools/release.py`.

## The version check

The `factory/release` Doc holds the latest version Ross has released. If its `version:` is newer than this file's, this
snapshot is behind. Say so once, in one line, the next time you speak to the person:

> System update ready. Next time you're at a computer: claude.ai → your project → settings → Sync.

Then carry on normally. Never refuse work because the snapshot is behind. If `factory/release` is missing, say nothing.

## What changed

- 0.1.0 (2026-11-06): first public release.
- 0.2.0 (2026-11-06): First-run setup; scripts come from the public repo
- 0.2.1 (2026-11-09): The whole repo is attached to every Project; agents work only from workspace/
- 0.3.0 (2026-11-09): Guided onboarding; blank-slate wording; any bank's CSV or PDF statements; <slug>.me Docs; scripts via git
- 0.3.1 (2026-11-09): Only the Project instruction and the drive say who Claude works for
- 0.3.2 (2026-11-09): Rand by default; work quietly; Error 500 for anything outside the system
- 0.3.3 (2026-11-09): Setup offers to create the business folder
