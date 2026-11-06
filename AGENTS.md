# Agent guidelines and constraints

## General

- Use the file-editing tools for edits; do not modify files via shell commands.
- For shell commands and filesystem operations, use Git Bash.
- For Python, use the interpreter found by `uv python find`; install packages
  with `uv run pip` (or `pip` from the active virtual environment).
- For Node.js, use `bun` / `bunx`.

## Building the C library

The Windows port compiles with the MSYS2 **UCRT64** toolchain. The canonical
build is the `Makefile` in `src/x86_64-w64-mingw32`. Build it from an MSYS2
UCRT64 shell:

```sh
make -C src/x86_64-w64-mingw32
```

Or, from a Windows command prompt, run the one-shot wrapper (assumes MSYS2 is
installed at `C:\msys64`):

```bat
src\x86_64-w64-mingw32\build.cmd
```

To run a raw command in the MSYS2 UCRT64 environment, use:

```
C:\msys64\msys2_shell.cmd -ucrt64 -here -no-start -defterm -c "your_command"
```

Add `-where "C:\path"` instead of `-here` to run from a specific directory.

Builds are **byte-reproducible**. Verify with `make repro`, which builds twice
and compares every artifact. Do not add flags, generated files, or code that
embeds timestamps or absolute paths — it will fail the check. See
`adr/0007-reproducible-builds.md`.

## SDK core

The files in `src/common/` are the **unmodified** OS-independent Sensoray core
and must never be edited, reformatted, or patched. They are tracked in Git
exactly as shipped in the official SDK archive, and can be re-sourced from it at
any time with zero diff. Port fixes belong in `src/x86_64-w64-mingw32/`.

See `src/common/README.md` for the rule and the re-sourcing procedure.

They remain Copyright (C) Sensoray Co., Inc. and are not licensed by this
project — see `LICENSE` and `adr/0005-upstream-inclusion-not-licensing.md`.

## Python packaging

The Python package lives in `src/python`. Native libraries are committed under
`src/python/_libs/<platform>/` and injected into the wheel by
`src/python/hatch_build.py`, one platform per wheel. Select a target with
`S26_WHEEL_PLATFORM` (default `win_amd64`).

```sh
cd src/python
uv run --with pytest --with build --with hatchling pytest tests -q
uv build --no-sources
```

A wheel carrying a native library must never be tagged `py3-none-any`.
Never edit `_libs/**` by hand — copy build output there from the C build.
