# sensoray-sdk-contrib

Ports and projects related to the [Sensoray 2600](https://www.sensoray.com/products/2600/)
middleware SDK — the client library for the model 2601 Ethernet I/O gateway and
its input-output modules (IOMs).

## What's here

| Contents | &zwj;
| -- | --
| MSYS2-UCRT64 build of the SDK | [src/x86_64-w64-mingw32](src/x86_64-w64-mingw32/README.md)
| Python wrapper for the SDK | [src/python](src/python/README.md)

## Getting started

Consult the linked README files for extended details.

**1. Build the SDK**

- Download the Sensoray 2600 SDK and extract the _common_ folder from the SDK into _src/common_.
- Run **build.cmd**, or **make** from a MSYS2-UCRT64 environment.
- Copy the resulting `build/s2600.dll` to `src/python/_libs/win_amd64/` to package the Python wheel.

**2. Use the Python wrapper**

```sh
pip install sensoray-sdk-contrib
```

## License

This repository contains material under **two separate sets of terms**.

- **This project's code** — the Windows (MSYS2 UCRT64) port, the Python package,
  and future platform ports — is original work by Maxwell Bloch, dual-licensed at
  your option under **AGPL-3.0-only** *or* **GPL-3.0-or-later**. See
  [`COPYING`](COPYING).
- **The upstream Sensoray 2600 SDK core** (`s26core.c`, `app2600.h`,
  `s26modf.h`, `tctable.h`) is **Copyright (C) Sensoray Co., Inc.** and is *not*
  licensed here. The SDK archive ships no license or EULA; this project relies on
  the SDK's own stated intent that the core "must be included" and that only the
  three OS-specific files may be modified. See
  [`adr/0005`](adr/0005-upstream-inclusion-not-licensing.md).

Built binaries such as `s2600.dll` combine both and require compliance with both
sets of terms. See [`LICENSE`](LICENSE) and
[`src/python/NOTICE.md`](src/python/NOTICE.md).

This is an independent community project, not affiliated with or endorsed by
Sensoray Co., Inc.

Architectural decisions are recorded in [`adr/`](adr/), following
[Architectural Decision Records](https://adr.github.io/) using the
[MADR template](https://raw.githubusercontent.com/adr/madr/refs/tags/4.0.0/template/adr-template.md).
