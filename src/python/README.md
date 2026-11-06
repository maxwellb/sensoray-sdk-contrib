# sensoray-sdk-contrib

Python `ctypes` bindings for `s2600.dll`, the Sensoray 2600 middleware — the
client library for the Sensoray 2601 Ethernet I/O gateway and its modular IOMs.

All exported `S26_*` C functions are available directly on the module
namespace, so calls look and feel like the underlying C API. Constants such as
`MODID_GATEWAY`, `IOM_2608`, and `SIO_BR_9600` are re-exported alongside the
functions they parameterize.

## Requirements

- Windows (the bundled native library binds Winsock and Win32 threads)
- Python ≥ 3.11

## Installation

```sh
pip install sensoray-sdk-contrib
```

Or with [uv](https://docs.astral.sh/uv/):

```sh
uv add sensoray-sdk-contrib
```

The native `s2600.dll` ships inside the wheel under `sensoray/s2600/lib` and is
loaded automatically on import. To use a different DLL, point the `S26_DLL`
environment variable at its path.

Wheels are built **per platform**: each one carries a single target's native
library and is tagged accordingly (this release is `py3-none-win_amd64`). Later
releases add further targets alongside it; pip selects the wheel matching your
platform.

## Quick start

```python
import ctypes
from ctypes import byref

import sensoray.s2600 as s26

status = s26.S26_DriverOpen(1)
if status != 0:
    raise s26.S26Error(status, "S26_DriverOpen")

status = s26.S26_BoardOpen(0, None, b"10.10.10.1")
if status != 0:
    raise s26.S26Error(status, "S26_BoardOpen")

# Schedule a query, execute it, then read the out-parameter.
firmware = ctypes.c_uint16()
x = s26.S26_SchedOpen(0, 50)
s26.S26_Sched2600_GetFirmwareVersion(x, s26.MODID_GATEWAY, byref(firmware))
iom_status = (ctypes.c_uint8 * s26.NUM_IOMPORTS)()
result = s26.S26_SchedExecute(x, 100, iom_status)
print(f"Gateway firmware: 0x{firmware.value:04X} ({s26.err_name(result)})")

s26.S26_DriverClose()
```

## Key usage notes

- **Error codes, not exceptions.** SDK functions return status codes
  (`GWERR_NONE` = 0 on success). Wrap failures yourself with
  `s26.S26Error(code, "function name")`, which formats the code as
  `0x… (GWERR_NAME)` and carries `code`/`fn` as attributes.
- **Two error domains.** Driver-open errors (`DRVERR_*`), board-open errors
  (`ERR_*`), and gateway transaction errors (`GWERR_*`) are distinct
  constants; `s26.err_name()` decodes gateway errors, including the extra
  info in the low byte (e.g. the IOM port inside `GWERR_IOMNORESPOND`).
- **Transactions are one-shot.** `S26_SchedOpen()` allocates a transaction,
  and `S26_SchedExecute()` consumes (frees) it. Open a fresh one per batch.
- **Out-parameters fill at execute time.** `S26_Sched*` query calls accept a
  ctypes out-buffer, but it is only written during post-processing inside
  `S26_SchedExecute()`. Read the buffer *after* execute returns. See
  [SKILL.md](SKILL.md) for the full reference.

## API surface

| Area | Functions |
|---|---|
| Driver lifecycle | `S26_DriverOpen`, `S26_DriverClose`, `S26_DriverVersion`, `S26_DLLOpen`, `S26_DLLClose` |
| Boards | `S26_BoardOpen`, `S26_BoardClose`, `S26_ResetNetwork`, `S26_ReadStatistics` |
| IOM registration | `S26_RegisterAllIoms`, `S26_ResetIom` |
| Transactions | `S26_SchedOpen`, `S26_SchedExecute`, `S26_SchedExecuteStart`, `S26_SchedExecuteIsResponded`, `S26_SchedExecuteWait`, `S26_SchedExecuteFinish` |
| Serial comports | `S26_ComOpen`, `S26_ComClose`, `S26_ComSetMode`, `S26_ComSend`, `S26_ComReceive`, `S26_ComFlush`, `S26_ComClearFlags`, `S26_ComGetRxCount`, `S26_ComGetTxCount`, `S26_ComSetBreakChar`, `S26_ComStartBreak`, `S26_ComEndBreak` |
| 2608 analog I/O | `S26_Sched2608_*`, `S26_2608_*` |
| 2610 / 2612 digital & high-res ADC | `S26_Sched2610_*`, `S26_Sched2612_*`, `S26_2612_*` |
| 2620 / 2631 counters & motor controller | `S26_Sched2620_*`, `S26_Sched2631_*` |
| 2650 / 2652 / 2653 relays | `S26_Sched2650_*`, `S26_Sched2652_*`, `S26_Sched2653_*` |
| Utilities | `S26_CastAsLong`, `S26_CastAsShort`, `S26_CopyAny`, `S26_Bitmask` |

Python-side helpers (`load`, `lib`) and the `S26Error` exception type are also
available in the module namespace.

## Development

The `sensorayd` telemetry daemon ships as an installable CLI with the package:

```sh
uvx --from sensoray-sdk-contrib sensorayd 10.10.10.1          # AF_UNIX socket
uvx --from sensoray-sdk-contrib sensorayd 10.10.10.1 --tcp 26010   # TCP instead
```

## License

This package contains material under **two separate sets of terms**; see
[NOTICE.md](NOTICE.md) for the full accounting.

- **This project's code** (the Python bindings and daemon) is original work by
  Maxwell Bloch, dual-licensed at your option under **AGPL-3.0-only** *or*
  **GPL-3.0-or-later**. See [COPYING](COPYING), [agpl-3.0.txt](agpl-3.0.txt),
  and [gpl-3.0.txt](gpl-3.0.txt).
- **The bundled `s2600.dll`** is a combined work: it also contains the
  OS-independent Sensoray 2600 SDK core, which is
  **Copyright (C) Sensoray Co., Inc.** and is *not* licensed under the AGPL/GPL.
  Verbatim notices ship in
  [LICENSES/Sensoray-2600-SDK-NOTICE.txt](LICENSES/Sensoray-2600-SDK-NOTICE.txt).

Using the bundled binary requires compliance with both Sensoray's terms and one
of the licenses above. Both license options carry an additional permission
(AGPL-3.0 §7 / GPL-3.0 §7) permitting that combination.

All of the above texts also ship in the wheel's `dist-info/licenses` directory.

This is an independent community project. It is not affiliated with, endorsed
by, or sponsored by Sensoray Co., Inc.