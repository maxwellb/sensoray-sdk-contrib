"""
Verify the bundled s2600.dll against a connected MM.

Author   : Maxwell Bloch (github.com/maxwellb)
Copyright: (C) 2026 Maxwell Bloch

Opens the driver + board, queries the gateway firmware version, link status
and interlocks, then shuts down cleanly.

Important SDK detail: S26_Sched* query functions take an out-param POINTER that
is only filled during post-processing *inside* S26_SchedExecute(). So the buffer
must be read after execute returns (and each execute frees its transaction).

Run (adjust MM IP if needed):
    cd src/python/src
    uv run python -m _utils.check2600 [MM_IP]
"""
import sys
import ctypes
from ctypes import byref

from sensoray import s2600


def main():
    mm_ip = sys.argv[1] if len(sys.argv) > 1 else "10.10.10.1"

    print("s2600.dll loaded.")
    L = s2600.lib()
    print(f"Driver version : {s2600.S26_DriverVersion().decode('ascii')}")

    err = s2600.S26_DriverOpen(1)
    print(f"DriverOpen     : {err} (DRVERR_NONE=0)")
    if err != 0:
        return 1

    err = s2600.S26_BoardOpen(0, None, mm_ip.encode("ascii"))
    print(f"BoardOpen      : 0x{err:08X} (ERR_NONE=0)")
    if err != 0:
        s2600.S26_DriverClose()
        return 1

    ok = s2600.S26_ResetNetwork(0)
    print(f"ResetNetwork   : {ok}")

    # --- Firmware version of the gateway (MODID_GATEWAY = 0xFF) ---
    x = s2600.S26_SchedOpen(0, 50)
    v = ctypes.c_uint16(0)
    serr = s2600.S26_Sched2600_GetFirmwareVersion(x, ctypes.c_uint8(0xFF), byref(v))
    status = (ctypes.c_uint8 * 16)()
    gerr = s2600.S26_SchedExecute(x, 100, status)
    print(f"MM fw version  : 0x{v.value:04X} (sched=0x{serr:08X} exec=0x{gerr:08X} {s2600.err_name(gerr)})")

    # --- Link status ---
    x = s2600.S26_SchedOpen(0, 50)
    links = ctypes.c_uint16(0)
    serr = s2600.S26_Sched2601_GetLinkStatus(x, byref(links))
    status = (ctypes.c_uint8 * 16)()
    gerr = s2600.S26_SchedExecute(x, 100, status)
    print(f"Link status    : 0x{links.value:04X} (sched=0x{serr:08X} exec=0x{gerr:08X})")

    # --- Interlocks ---
    x = s2600.S26_SchedOpen(0, 50)
    locks = ctypes.c_uint8(0)
    serr = s2600.S26_Sched2601_GetInterlocks(x, byref(locks))
    status = (ctypes.c_uint8 * 16)()
    gerr = s2600.S26_SchedExecute(x, 100, status)
    print(f"Interlocks     : 0x{locks.value:02X} (sched=0x{serr:08X} exec=0x{gerr:08X})")

    s2600.S26_BoardClose(0)
    s2600.S26_DriverClose()
    print("Closed cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
