# Source

Ports of the Sensoray 2600 middleware to various targets, plus a Python package.

## Layout

| Directory | Description |
|---|---|
| `common/` | OS-independent SDK core — tracked unmodified; do not edit. |
| `x86_64-w64-mingw32/` | Windows build via MSYS2 UCRT64. |
| `python/` | Python `ctypes` wrapper, payloads, and daemon. |

## The SDK core

`common/` contains the OS-independent SDK core (`s26core.c`, `app2600.h`,
`s26modf.h`, `tctable.h`), committed exactly as shipped in the official SDK
archive:

```
https://www.sensoray.com/downloads/sdk_2600_1.1.18.zip
```

**Do not modify these files.** They are read-only inputs; port fixes belong in
the OS-specific layer. See [`common/README.md`](common/README.md) for the rule
and the procedure for re-sourcing them from the archive (which should always
produce a zero diff).

These four files remain Copyright (C) Sensoray Co., Inc. and are not licensed by
this project. See [`../LICENSE`](../LICENSE) and
[`../adr/0005-upstream-inclusion-not-licensing.md`](../adr/0005-upstream-inclusion-not-licensing.md).

## Native payloads for the Python package

Built libraries are collected under `python/_libs/<platform>/` and are committed
so that packaging needs no compiler:

```
python/_libs/win_amd64/s2600.dll
```

`python/hatch_build.py` injects exactly one payload per wheel at the runtime path
`sensoray/s2600/lib/`, and tags the wheel `py3-none-<platform>`. Select a target
with `S26_WHEEL_PLATFORM` (default `win_amd64`). See
[`../adr/0006-binary-redistribution.md`](../adr/0006-binary-redistribution.md).
