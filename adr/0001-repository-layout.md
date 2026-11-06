# 1. Repository layout: target-triple source ports and a shared Python package

- Status: accepted
- Date: 2026-10-13

## Context

The Sensoray 2600 SDK ships OS-independent core sources plus per-OS support
modules. Multiple target platforms must coexist in one repository, and the
Windows port must be usable both as a C library and from Python.

## Decision

The repository keeps a `src/` tree where:

- `src/common/` holds the unmodified, OS-independent Sensoray core (tracked
  unmodified; see [0004](0004-sdk-core-tracked-unmodified.md)).
- Each OS port lives in a directory named by its target triple, e.g.
  `src/x86_64-w64-mingw32/`, matching the output of `gcc -dumpmachine`.
- `src/python/` holds a `ctypes` wrapper package (`s26`) and its demo/smoke
  scripts, independent of any single C port.

## Consequences

- Adding a new platform means adding a sibling directory named by its target
  triple, with no changes to shared code.
- The Python package is decoupled from the C build tree and locates the DLL via
  the `S26_DLL` environment variable or a default path relative to the package.
