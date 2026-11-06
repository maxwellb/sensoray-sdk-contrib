# 7. Reproducible builds for the native library and the wheel

- Status: accepted
- Date: 2026-11-06
- Related: [0002](0002-canonical-build.md), [0006](0006-binary-redistribution.md)

## Context

The Python wheel ships a compiled `s2600.dll` that is committed under
`src/python/_libs/win_amd64/` (ADR 0006). A committed binary that nobody else
can reproduce is a black box: users cannot verify that the shipped DLL
corresponds to the published sources, and maintainers cannot tell a source
change from a toolchain change when the payload is refreshed.

The build was measured, not assumed. Two consecutive builds of the same tree
produced:

| Artifact | Deterministic before? |
|---|---|
| `s26core.o`, `s26mod.o` | yes |
| `lib2600.a` | yes |
| `libs2600.dll.a` | yes |
| `s2600.dll` | **no** |
| `demo.exe` | **no** |

So the problem was confined to PE linking, not compilation.

## Decision

Make `make` byte-reproducible, and make the guarantee verifiable rather than
asserted.

Three independent causes were eliminated:

1. **PE timestamp.** GNU `ld` writes the link time into the optional header.
   `-Wl,--no-insert-timestamp` writes zero instead, removing the clock from the
   output entirely.
2. **PE image base.** MSYS2's `gcc` specs enable `--enable-auto-image-base`,
   which is derived rather than fixed and was observed to vary between runs. The
   base is baked into the optional header and, via the relocation table, into
   `.data`. An explicit `-Wl,--image-base` per artifact removes the variance.
   *This was the non-obvious one:* `--no-insert-timestamp` alone was **not**
   sufficient, and the difference looked like a timestamp because the differing
   bytes include absolute VAs.
3. **Absolute paths in debug info.** `-g` records the compilation directory, so
   two checkouts at different paths would differ. `-ffile-prefix-map` rewrites
   the working tree to `.` and `src/common` to `/sensoray-common`.

Additionally pinned so the guarantee does not rest on toolchain defaults:

- `-frandom-seed` per translation unit, and `ar rcsD` (deterministic mode), even
  though both were already deterministic here.
- `SOURCE_DATE_EPOCH`, derived from `git log -1 --format=%ct` with a fixed
  fallback, exported for any tool that honours it (hatchling uses it for wheel
  and sdist timestamps).
- `LC_ALL=C` and `TZ=UTC`, so locale and timezone cannot leak into output.

`make repro` builds the tree twice into `build/repro-a` and `build/repro-b`,
compares all six artifacts byte-for-byte, cleans up, and exits non-zero on any
mismatch. `REPRODUCIBLE=0` opts out.

## Verification

Two independent checks were run, not one:

- **Same path, two builds** — all six artifacts identical.
- **Different checkout paths** — the tree was copied to a differently-named
  directory and built there; `s26core.o`, `s26mod.o`, `lib2600.a`, `s2600.dll`
  and `libs2600.dll.a` were identical. This is what proves the `-ffile-prefix-map`
  work is doing something.

`strings` on the resulting DLL contains no absolute build paths.

The Python artifacts were already reproducible (hatchling pins zip timestamps to
a fixed value and honours `SOURCE_DATE_EPOCH`), confirmed by building twice.
No packaging change was required.

## Consequences

- The committed payload was rebuilt with these flags and re-verified: the DLL
  loads, `S26_DriverVersion()` returns `2.0.5`, and all 20 tests pass.
- Rebuilding from a clean checkout should now reproduce the committed payload
  exactly. A mismatch is meaningful: sources changed, or the toolchain differs
  from the pinned one.
- **Reproducibility is toolchain-scoped.** Different `gcc`/`binutils` versions
  will still produce different bytes. The guarantee assumes the toolchain
  recorded by the maintainer at release time rather than claiming
  cross-version reproducibility.
- `demo.exe` is covered by the same flags but is not committed; it is a
  convenience binary.
- Anything that embeds a timestamp or absolute path in future port code will
  break `make repro`, which is the intended failure mode.
