---
version: 0.5.0
released: 2026-11-10
---

# Structure version

The version of the rules this snapshot holds. Written only by Ross's `tools/release.py`.

## The version check

The `release:` line in the Doc you read on a start (a coach's `<slug>.me`, the head coach's `hub/start`) is the latest
version Ross has released, copied from `factory/release`. If it's newer than this file's `version:`, this snapshot is
behind. Don't open `factory/release` to check. Say so once, in one line, the next time you speak to the person:

> System update ready. Next time you're at a computer: claude.ai → your project → settings → Sync.

Then carry on normally. Never refuse work because the snapshot is behind. If there's no `release:` line, or it's blank, say nothing.

## What changed

- 0.1.0 (2026-11-06): first public release.
- 0.2.0 (2026-11-06): First-run setup; scripts come from the public repo
- 0.2.1 (2026-11-09): The whole repo is attached to every Project; agents work only from workspace/
- 0.3.0 (2026-11-09): Guided onboarding; blank-slate wording; any bank's CSV or PDF statements; <slug>.me Docs; scripts via git
- 0.3.1 (2026-11-09): Only the Project instruction and the drive say who Claude works for
- 0.3.2 (2026-11-09): Rand by default; work quietly; Error 500 for anything outside the system
- 0.3.3 (2026-11-09): Setup offers to create the business folder
- 0.4.0 (2026-11-10): Lower usage, tighter lock, tagged releases
- 0.5.0 (2026-11-10): System changes go to the system provider; request logging removed
