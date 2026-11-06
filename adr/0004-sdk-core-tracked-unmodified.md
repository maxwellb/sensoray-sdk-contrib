# 4. SDK core is tracked unmodified; re-sourced from the upstream archive

- Status: accepted
- Date: 2026-10-13
- Revised: 2026-11-06 — the core is now committed rather than git-ignored.

## Context

The OS-independent Sensoray core (`s26core.c`, `app2600.h`, `s26modf.h`,
`tctable.h`) is required to build any port, but it is unmodified upstream
material owned by Sensoray Co., Inc.

Originally these files were git-ignored and had to be extracted before building.
That made a fresh checkout unable to compile without a manual download step.

## Decision

`src/common/` **is committed**, containing the four upstream files exactly as
they appear in the official SDK archive
(`https://www.sensoray.com/downloads/sdk_2600_1.1.18.zip`).

The files are treated as **read-only vendored inputs**:

- They are never edited, reformatted, or patched. Fixes belong in the OS layer
  (`src/x86_64-w64-mingw32/`), which is this project's own code.
- They can be replaced wholesale from the SDK archive at any time; because they
  are unmodified, re-sourcing produces no diff.
- `.gitattributes` marks them `-text` so Git never rewrites their CRLF line
  endings, preserving byte fidelity with the archive.
- `src/common/README.md` states the rule prominently for contributors and
  agents, and documents the re-sourcing procedure.

## Consequences

- A fresh checkout builds without downloading the SDK.
- The repository now redistributes upstream SDK **sources**, not just compiled
  binaries. The licensing basis for that is recorded in
  [0005](0005-upstream-inclusion-not-licensing.md): the SDK ships no license or
  EULA, and its own headers state that the core "must be included" in projects
  and must not be modified except for the three OS-specific files.
- **A drift risk replaces the old download friction.** An edited core file would
  silently diverge from upstream and undermine that inclusion basis. This is
  mitigated by the `-text` pin, the README rule, and the zero-diff re-sourcing
  check (`git status --short src/common/`).
- Compiled binaries that combine the core with a port's own code are also
  redistributed; see [0006](0006-binary-redistribution.md).
- `src/python/NOTICE.md` and the wheel's `License-File` entries still describe
  the core as "not licensed here" — that remains correct: *tracked* is not
  *licensed*.

## Superseded in part

This decision reverses the "not committed / git-ignored" portion of the original
ADR 0004. The original rationale — that the project should not imply ownership of
upstream material — is preserved by keeping the files unmodified, retaining their
copyright notices, and documenting their provenance, rather than by withholding
them.
