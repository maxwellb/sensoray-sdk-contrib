# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-11-06

First public release.

### Added

- MSYS2 UCRT64 (`x86_64-w64-mingw32`) port of the Sensoray 2600 middleware:
  `s26app.h`, `s26mod.h`, `s26mod.c` supply the system layer using Winsock and
  Win32 threads; the OS-independent core is compiled unmodified.
- Canonical `Makefile` and `build.cmd` wrapper, emitting `lib2600.a`,
  `s2600.dll`, `libs2600.dll.a` and `demo.exe` into `build/`.
- Python `ctypes` bindings (`sensoray.s2600`) exposing every exported `S26_*`
  function, SDK constants, `S26Error`, and `err_name()`.
- `sensorayd` telemetry daemon and console script, including a raw `ws2_32.dll`
  AF_UNIX stream transport for Windows.
- Per-platform wheel packaging: `hatch_build.py` injects one native payload per
  wheel at `sensoray/s2600/lib/` and tags it `py3-none-<platform>`.
- Test suite covering symbol binding, error decoding, wheel tagging, payload
  placement, and license metadata completeness.
- Licensing documentation: root `LICENSE`, `NOTICE.md`, verbatim upstream
  notices, and a §7 additional permission permitting combination with the
  Sensoray core.
- Reproducible builds: `make` produces byte-identical artifacts, verifiable with
  `make repro`. PE timestamps, image bases and debug-info paths are pinned, and
  `SOURCE_DATE_EPOCH` is derived from the commit.

[Unreleased]: https://github.com/maxwellb/sensoray-sdk-contrib/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/maxwellb/sensoray-sdk-contrib/releases/tag/v1.0.0
