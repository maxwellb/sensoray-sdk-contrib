# Skill: Using the Sensoray 2600 SDK (compiled library + Python package)

Author   : Maxwell Bloch (github.com/maxwellb)
Copyright: (C) 2026 Maxwell Bloch

How to build and use the Sensoray 2600 middleware against the MSYS2 UCRT64
toolchain, and how to drive it from Python.

## When to use

- Building the 2600 SDK from source for Windows (MSYS2 UCRT64).
- Calling the 2600 API from Python via `ctypes`.
- Porting the `demo.c` example or writing custom I/O control scripts.
- Querying the MM gateway / attached IOMs (analog, digital, counter, relay, serial).

## Layout

```
src/common/        OS-independent core (s26core.c, app2600.h, ...) — DO NOT MODIFY.
src/x86_64-w64-mingw32/   Windows port: s26mod.c/h, s26app.h, Makefile, build.cmd, demo.c.
src/python/        Python package: sensoray.s2600 (ctypes wrapper), utility scripts in src/_utils/.
```

## Building the library (MSYS2 UCRT64)

Canonical build is the `Makefile`. From `src/x86_64-w64-mingw32`, either run
`make` in an MSYS2 UCRT64 shell, or run `build.cmd` from a Windows command
prompt (assumes MSYS2 at `C:\msys64`).

```sh
make          # lib + demo
make lib      # libraries only
make clean    # remove build/
```

This compiles with `-D ENDIAN_LITTLE` and outputs into `build/`:

- `build/lib2600.a` — static library.
- `build/s2600.dll` — shared library, all `S26_*` symbols exported, plain C ABI.
- `build/libs2600.dll.a` — import library.
- `build/demo.exe` — demo program.

Run it: `build/demo.exe` (or `build\demo.exe` from cmd). It opens the MM at
`10.10.10.1` (edit `IP_ADDRESS` in `demo.c` to change).

## Using the Python package

The `src/python` package wraps `s2600.dll`. Wheels ship it at
`sensoray/s2600/lib/s2600.dll`. In a source checkout the loader also looks in
`_libs/<platform>/` (the packaging payload directory). Override either with the
`S26_DLL` environment variable, which takes precedence.

```python
import sensoray.s2600 as s26

s26.load()                       # loads the DLL and resolves symbols
print(s26.driver_version())      # "2.0.5"

s26.lib().S26_DriverOpen(1)
s26.board_open(0, "10.10.10.1")           # hbd, mm_ip, (client_ip optional)
s26.lib().S26_ResetNetwork(0)

err, types, status = s26.register_all_ioms(0, msec=100, retries=50)
print([(i, t) for i, t in enumerate(types) if t])   # e.g. [(0, 2608), (7, 2610)]

s26.lib().S26_DriverClose()
```

Run the full demo (utility scripts are not distributed with the package):

```sh
cd src/python/src
uv run python -m _utils.demo
```

### Key SDK gotcha — out-params are filled at execute time

`S26_Sched*` query functions take an output POINTER, but that buffer is only
written during post-processing *inside* `S26_SchedExecute()` — not when the
action is scheduled. So:

1. Allocate a persistent `ctypes` buffer.
2. Pass it (byref) to the `S26_Sched*` call.
3. Call `S26_SchedExecute(x, msec)`.
4. Read the buffer **after** execute returns.

Each `S26_SchedExecute()` frees its transaction, so open a fresh one per query
via `S26_SchedOpen(hbd, retries)`.

```python
import ctypes
from ctypes import byref

x = s26.sched_open(0, retries=50)
v = ctypes.c_uint16()
s26.lib().S26_Sched2600_GetFirmwareVersion(x, ctypes.c_uint8(0xFF), byref(v))
err, _ = s26.sched_execute(x, msec=100)      # fills v during execute
print(hex(v.value))                            # read AFTER execute
```

## Common queries / operations

| Purpose | Function(s) |
|---|---|
| Firmware version | `S26_Sched2600_GetFirmwareVersion(x, 0xFF, &v)` → 0x0106 |
| Product ID | `S26_Sched2600_IomGetProductID(x, port, &v)` → 0x0A29 (2601) |
| Link status / interlocks | `S26_Sched2601_GetLinkStatus` / `GetInterlocks` |
| Analog in (2608) | `S26_Sched2608_GetAins(x, port, volts16, ADC_INTEGRATED)` |
| Analog out (2608) | `S26_Sched2608_SetAout(x, port, chan, volts)` |
| Digital (2610) | `S26_Sched2610_GetInputs` / `SetOutputs` |
| Counter (2620) | `S26_Sched2620_GetCounts`, `SetControlReg`, `SetPreload`, `SetMode*` |
| Relay (2650/2652) | `S26_Sched2650_SetOutputs` / `S26_Sched2652_SetOutputs` |
| Serial | `S26_ComOpen` / `ComSetMode` / `ComSend` / `ComReceive` |

## Error codes

`GWERR_NONE` (0) = success. Common values: `GWERR_MMNORESPOND` (0xA00),
`GWERR_PACKETSEND` (0xB00), `GWERR_IOMSPECIFIC` (0xC00), `GWERR_BADVALUE` (0xD00).
Use `s26.err_name(code)` to decode. Serial framing errors surface as
`COM_FRAMINGERROR` (0x08) in the low bits of a Com* return value.

## Verified behavior

- MM at `10.10.10.1`, fw version 0x0106, product 2601.
- `demo.exe` and `python demo.py` both detect a 2608 (port 0) and 2610 (port 7)
  and read live analog/digital values.
- `S26_ComSend` framing errors are expected unless the serial loopback ports
  (COM2↔COM1, COM4↔COM3) are cabled with null-modem adapters.
