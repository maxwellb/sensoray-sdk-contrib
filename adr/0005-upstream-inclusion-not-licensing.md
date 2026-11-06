# 5. Upstream SDK core is included, not licensed: the "fundamental four"

- Status: accepted
- Date: 2026-11-06
- Supersedes in part: [0004](0004-sdk-core-tracked-unmodified.md)

## Context

ADR 0004 establishes that `src/common/` holds the unmodified upstream core and
is treated as read-only. (It originally left those files untracked; as revised it
tracks them unmodified so a fresh checkout builds. That change does not affect
the licensing analysis below — tracked is not licensed.)

What 0004 did not settle is the *provenance and permission basis* for the four
files in that directory:

| File | Header notice |
|---|---|
| `s26core.c` | `Copyright (C) 2008 Sensoray. Author: Jim Lamberson.` |
| `app2600.h` | `Copyright : (C) 2008 Sensoray` |
| `s26modf.h` | `Copyright : (C) 2008 Sensoray. Author: Jim Lamberson` |
| `tctable.h` | `Copyright (C) Sensoray Company 2004` |

The SDK distribution archive (`sdk_2600_1.1.18.zip`) contains **no license,
EULA, or copying terms of any kind**. There is no document to point at, no
license identifier to place in metadata, and no grant that can be represented in
an SPDX expression. The only statements of intent are the notices inside these
four source files.

## Decision

Treat these files as **expressly contemplated, permitted inclusion** on the
basis of the SDK's own statements, not as fair use and not as a license grant.

`s26core.c` states three things that directly govern this project:

1. *"Depends on OS-specific code that must be supplied by these external files
   … Your project must include these files."* Shipping the core as part of a
   project that supplies the OS layer is the documented, intended use.
2. *"Don't modify any files except the three 0S-specific source files mentioned
   above [s26app.h, s26mod.h, s26mod.c]. The core … [is] designed to work with
   any operating system and with any cpu, WITHOUT MODIFICATION."* This project
   modifies exactly those three files and nothing else.
3. *"We will be happy to quote a fee for porting the API to another operating
   system or cpu."* Sensoray offers porting as a paid *service*. There is no
   assertion of a right to control independent ports, and no licensing market
   for a contributed UCRT64 port that this project displaces.

Therefore:

- The four files are included **unmodified**, satisfying the stated condition.
- Only the three permitted OS-specific files are modified.
- Copies of the four notices are reproduced verbatim in
  [`src/python/LICENSES/Sensoray-2600-SDK-NOTICE.txt`](../src/python/LICENSES/Sensoray-2600-SDK-NOTICE.txt),
  and attribution is recorded in `LICENSE`, `NOTICE.md` and this ADR.
- The project does **not** relicense the Sensoray material and claims no rights
  in it. `src/common/` remains untracked.

## Why not fair use

Fair use is a defence to infringement, not a permission. It cannot be asserted
in package metadata, cannot be relied on to warrant redistribution rights to an
index, and would frame the project as taking something rather than doing what
the SDK asks. The permitted-inclusion reading is both stronger and more
accurate.

## Consequences

- Binary distributions combine licensed (this project) and non-licensed
  (Sensoray) code; see [0006](0006-binary-redistribution.md) for the mechanism
  used to make that coherent.
- If Sensoray ever publishes terms, this ADR must be revisited. Until then the
  notices are the authoritative statement.
- A written confirmation from Sensoray would convert a well-founded position
  into a settled one and should be sought before any large-scale binary
  distribution.
