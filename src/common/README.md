# DO NOT MODIFY THESE FILES

This directory holds the unmodified, OS-independent core of the Sensoray 2600
middleware SDK:

| File | Role |
|---|---|
| `s26core.c` | Middleware core (protocols, API implementation) |
| `app2600.h` | Public API declarations and constants |
| `s26modf.h` | Definitions shared by `s26core.c` and the OS module |
| `tctable.h` | Thermocouple calibration tables (generated upstream) |

**These files are upstream material owned by Sensoray Co., Inc. They are not
ours to change, and they are not licensed by this project.**

## The rule

**Do not edit, reformat, re-indent, fix warnings in, or "clean up" any file in
this directory.**

The SDK's own header states the condition under which the core may be used:

> "Don't modify any files except the three 0S-specific source files mentioned
> above. The core and other OS-independent source files are designed to work
> with any operating system and with any cpu, WITHOUT MODIFICATION."

If you have found a bug or a portability problem here, fix it in
[`../x86_64-w64-mingw32/`](../x86_64-w64-mingw32/) (the OS-specific layer, which
*is* ours) or raise it with Sensoray. Do not patch the core.

## Why the line endings are unusual

`*.c`/`*.h` are normally normalized to LF by `.gitattributes`. These four files
are explicitly marked `-text` instead, because the SDK archive ships them with
CRLF and the whole point of this directory is byte-for-byte fidelity. Do not
change that.

## Re-sourcing is always allowed

These files can be replaced wholesale from the official SDK at any time. That is
a normal, safe operation precisely *because* they are never modified:

```sh
# Unpack the SDK archive and copy the core straight over the tracked copies.
unzip -o sdk_2600_1.1.18.zip 'src/common/*' -d /tmp/sdk2600
cp /tmp/sdk2600/src/common/* src/common/
git status --short src/common/    # expected: no changes
```

If that `git status` reports changes, something in this directory was modified
by mistake — restore it from the archive rather than editing it back by hand.

## Licensing

These files remain Copyright (C) 2004–2008 Sensoray Co., Inc. (authors include
Jim Lamberson). The SDK archive distributes them with no license, EULA, or
copying terms; only the copyright notices in the file headers. This project does
not relicense them and claims no rights in them.

See:

- [`../../LICENSE`](../../LICENSE) — the two sets of terms in this repository
- [`../../src/python/LICENSES/Sensoray-2600-SDK-NOTICE.txt`](../python/LICENSES/Sensoray-2600-SDK-NOTICE.txt) — the notices, verbatim
- [`../../adr/0005-upstream-inclusion-not-licensing.md`](../../adr/0005-upstream-inclusion-not-licensing.md) — the basis for inclusion
