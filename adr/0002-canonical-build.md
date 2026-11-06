# 2. Canonical build: Makefile, with a convenience build.cmd

- Status: accepted
- Date: 2026-10-13

## Context

The Windows port must build out of the box on a standard MSYS2 UCRT64 install,
without requiring the user to remember the MSYS2 shell invocation.

## Decision

- `src/x86_64-w64-mingw32/Makefile` is the canonical build, emitting artifacts
  into a `build/` subdirectory (`lib2600.a`, `s2600.dll`, `libs2600.dll.a`,
  `demo.exe`).
- `src/x86_64-w64-mingw32/build.cmd` is a one-shot Windows wrapper that launches
  MSYS2 UCRT64 (default install path `C:\msys64`) and runs `make`, forwarding any
  target.

## Consequences

- `make` is the single source of truth for the build graph; `build.cmd` is a
  thin launcher.
- The historical `makelib` shell script was removed; the Makefile is the sole
  build recipe.
- All build products are isolated under `build/`, which is git-ignored, so the
  working tree stays clean and specific binaries can later be committed with a
  negation rule if needed.
- Builds are byte-reproducible and `make repro` verifies it; see
  [0007](0007-reproducible-builds.md).
