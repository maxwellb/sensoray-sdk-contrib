# 6. Binary redistribution: one platform per wheel, combined-work licensing

- Status: accepted
- Date: 2026-11-06
- Related: [0005](0005-upstream-inclusion-not-licensing.md), [0003](0003-licensing.md)

## Context

ADR 0005 establishes that the Sensoray core is included under the SDK's own
stated intent and is **not** licensed by this project. ADR 0003 licenses this
project's own code as `AGPL-3.0-only OR GPL-3.0-or-later`.

The shipped `s2600.dll` is a single linked object containing both. A wheel
therefore cannot honestly claim either license *alone*, and the two licenses
cannot be applied to the same artifact without addressing the interaction:

- GPL-3.0 §6 requires conveying the complete corresponding source of anything
  distributed in object form. The Sensoray core is deliberately **not** in this
  repository (ADR 0004), so a plain GPL reading would be self-contradictory.
- The Sensoray core carries no grant at all, so it cannot simply be
  "relicensed" into the GPL.

Additionally, the package is intended to grow across targets: 1.0.0 ships the
Windows x86_64 library; later versions add further targets without invalidating
earlier ones.

## Decision

### Licensing of the combined binary

1. The distribution's `License-Expression` describes **what is inside the
   artifact**, using a conjunction rather than a claim of coverage:

   ```
   (AGPL-3.0-only OR GPL-3.0-or-later) AND LicenseRef-Sensoray-2600-SDK
   ```

   `LicenseRef-Sensoray-2600-SDK` is a PEP 639 custom identifier, valid for
   index upload, denoting material that is present but not licensed here.

2. Both license options carry an **additional permission** under AGPL-3.0 §7 /
   GPL-3.0 §7 (recorded in `COPYING`) permitting combination of this project's
   code with the SDK core. This resolves the GPL §6 conflict *for combiners*
   without asserting any right over the Sensoray material — the same mechanism
   GCC uses for its runtime library exception.

3. The upstream notices ship **inside** the wheel at
   `.dist-info/licenses/LICENSES/Sensoray-2600-SDK-NOTICE.txt`, so attribution
   travels with the binary.

### One platform per wheel

- Each wheel contains exactly one target's native library, placed at the fixed
  runtime path `sensoray/s2600/lib/<library>`, so `_bindings` needs no
  per-platform branching beyond a filename list.
- Build inputs live at `_libs/<platform>/` in the source tree and are injected
  by `hatch_build.py`; `_libs` is excluded from wheel selection and included in
  the sdist.
- The wheel is tagged `py3-none-<platform>` and sets `Root-Is-Purelib: false`.
  `none` ABI is correct: this is a ctypes-loaded plain C library, not a CPython
  extension module.
- A wheel carrying a native library must **never** be tagged `py3-none-any`.

### Versioning across targets

Each version ships whichever targets were built for it; a target added later
appears in a later version alongside all earlier targets. Because PyPI filenames
are immutable and wheels are selected by tag, adding a target creates no
conflict with earlier releases. A user who pins an older version on a newer
target correctly gets "no matching distribution".

## Consequences

- `license-files` must list every file that carries terms or notices, and every
  listed file must be present in the wheel: PyPI rejects uploads where a
  `License-File` entry is missing from the archive.
- The sdist is platform neutral and remains installable on any host; importing
  the package without a native library warns (`ImportWarning`) rather than
  failing, and `S26_DLL` can point at a locally built library.
- Adding a target requires: an `_libs/<platform>/` directory, a `PAYLOADS` and
  `DESTINATIONS` entry in `hatch_build.py`, and a `_candidate_library_names()`
  entry in `_bindings.py`.
- The build hook only selects and tags; it never compiles. Compilation stays
  outside packaging so the sdist build remains reproducible off Windows.
