# Sensoray 2600 — Windows port (MSYS2 UCRT64)

Builds the 2600 SDK for Windows using the MSYS2 **UCRT64** toolchain
(`x86_64-w64-mingw32`).

## Prerequisites

- MSYS2 with the UCRT64 environment (`gcc`, `make`).
- The SDK core at `../common` (see [`../README.md`](../README.md)).

## Build

From a Windows command prompt:

```bat
build.cmd
```

Or from an MSYS2 UCRT64 shell:

```sh
make          # library + demo
make lib      # library only
make repro    # build twice and verify byte-identical output
make clean    # remove build/
```

Artifacts are written to `build/`: `lib2600.a`, `s2600.dll`, `libs2600.dll.a`,
and `demo.exe`.

`build.cmd` assumes MSYS2 is installed at `C:\msys64`; set `MSYS2_ROOT` to
override. The `SIO_FLUSH` warning emitted during compilation is harmless.

## Reproducible builds

Builds are **byte-reproducible**: the same commit produces identical artifacts,
regardless of when or where it is built. Verify with:

```sh
make repro
```

That compiles the tree twice into separate directories and compares every
artifact, failing on the first mismatch.

Three things had to be pinned, each of which is documented in the `Makefile`:

| Cause | Fix |
|---|---|
| PE timestamp written by `ld` | `-Wl,--no-insert-timestamp` |
| PE image base (MSYS2 enables `--enable-auto-image-base`, which is not stable here) | explicit `-Wl,--image-base` per artifact |
| Absolute build paths in `-g` debug info | `-ffile-prefix-map` to stable placeholders |

GCC's `-frandom-seed` and `ar`'s deterministic mode (`D`) are also set
explicitly, so the guarantee does not depend on toolchain defaults.

`SOURCE_DATE_EPOCH` is derived from `git log -1 --format=%ct` and exported, so
timestamp-aware tools agree on a single build time. `LC_ALL=C` and `TZ=UTC` are
exported so locale and timezone cannot leak into output either.

If the `s2600.dll` you rebuild does not match the committed payload under
`../python/_libs/win_amd64/`, that means either the sources changed or the
toolchain differs — which is exactly the signal this is meant to provide.

To opt out (for example, to reproduce a historical timestamped build when
debugging), pass `REPRODUCIBLE=0`:

```sh
make REPRODUCIBLE=0
```

## Publishing the Python wheel

The Python package ships this port's DLL as its native payload. After building,
copy it into the payload directory:

```sh
mkdir -p ../python/_libs/win_amd64
cp build/s2600.dll ../python/_libs/win_amd64/
```

Then build the wheel from `../python` (see
[`../python/README.md`](../python/README.md)).
