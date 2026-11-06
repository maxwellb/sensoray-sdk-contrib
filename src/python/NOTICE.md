# Notices — sensoray-sdk-contrib

This file records the provenance and ownership of everything distributed in this
package. Read it alongside [`COPYING`](COPYING) and
[`LICENSES/Sensoray-2600-SDK-NOTICE.txt`](LICENSES/Sensoray-2600-SDK-NOTICE.txt).

---

## 1. This project's code — AGPL-3.0-only OR GPL-3.0-or-later

The following are original works by Maxwell Bloch, dual-licensed at your option
under **either** the GNU Affero General Public License v3.0 only **or** the GNU
General Public License v3.0 or later. See [`COPYING`](COPYING).

    src/sensoray/**                       Python ctypes bindings
    sensorayd/**                          Python telemetry daemon + CLI
    src/_utils/**                         demo / smoke-test scripts
    src/x86_64-w64-mingw32/s26mod.c       Winsock + Win32 threads system layer
    src/x86_64-w64-mingw32/s26mod.h
    src/x86_64-w64-mingw32/s26app.h
    src/x86_64-w64-mingw32/Makefile
    src/x86_64-w64-mingw32/build.cmd
    src/x86_64-w64-mingw32/demo.c
    hatch_build.py                        packaging hook
    <future per-target port directories>

The MSYS2 UCRT64 (`x86_64-w64-mingw32`) port is an original contribution: it
replaces the SDK's POSIX/Unix system module with a Winsock + Win32 threads
implementation, targeting the UCRT runtime. No other target had this port.

Both license options carry an **additional permission** (AGPL-3.0 §7 /
GPL-3.0 §7) permitting combination with the Sensoray core below. See the
"Additional permission" section of [`COPYING`](COPYING).

## 2. Upstream Sensoray 2600 SDK core — all rights reserved, not relicensed

    s26core.c    Copyright (C) 2008 Sensoray. Author: Jim Lamberson.
    app2600.h    Copyright (C) 2008 Sensoray.
    s26modf.h    Copyright (C) 2008 Sensoray. Author: Jim Lamberson.
    tctable.h    Copyright (C) Sensoray Company 2004.

These four files are the OS-independent middleware core. They are **unmodified
upstream material owned by Sensoray Co., Inc.** and are **not** licensed under
the AGPL or GPL. Verbatim notices are reproduced in
[`LICENSES/Sensoray-2600-SDK-NOTICE.txt`](LICENSES/Sensoray-2600-SDK-NOTICE.txt).

They are tracked in this repository exactly as shipped in the official SDK
archive, for build convenience only; they may be replaced from that archive at
any time. Being present in this repository grants no rights beyond what
Sensoray's own notices allow.

### Basis for inclusion and redistribution

The Sensoray SDK archive contains **no license, EULA, or copying terms**. The
four files carry copyright notices only. This project therefore relies on the
SDK's own expressly stated intent, which contemplates exactly the activities
performed here:

1. **Permitted inclusion.** `s26core.c` states the core "depends on OS-specific
   code that must be supplied by these external files", and that "your project
   must include these files". Shipping the core as part of a project is the
   documented, intended use.
2. **Permitted modification scope.** `s26core.c` directs developers to "not
   modify any files except the three OS-specific source files mentioned above".
   This port modifies exactly those three files (`s26app.h`, `s26mod.h`,
   `s26mod.c`) and nothing else.
3. **No adverse market effect asserted.** The same notice offers to "quote a fee
   for porting the API to another operating system or cpu" — an offer to sell
   porting *services*, not a restriction on independent ports.

See [`../../adr/0005-upstream-inclusion-not-licensing.md`](../../adr/0005-upstream-inclusion-not-licensing.md)
for the recorded decision.

## 3. The bundled binary — combined work

    sensoray/s2600/lib/s2600.dll

This shared library is a **compiled, linked work** that combines section 1 and
section 2 above. As a combined work it may only be used in compliance with
**both** Sensoray's terms (whatever they may be) **and** one of the two licenses
in section 1.

Nothing in the AGPL or GPL grants any right in the Sensoray portion, and nothing
in Sensoray's notices grants any right in this project's code beyond what those
licenses already grant. The §7 additional permission in [`COPYING`](COPYING)
exists solely to make that combination unambiguously distributable.

## 4. No affiliation, no warranty

This is an independent, community-contributed project. It is not affiliated with,
endorsed by, or sponsored by Sensoray Co., Inc. "Sensoray" and "2600" are used
only to identify the hardware and SDK this package interoperates with.

The software is provided "as is", without warranty of any kind. It has been
tested against specific hardware; it can command real analog, digital, counter
and relay outputs, and misuse can damage equipment or injure people.
