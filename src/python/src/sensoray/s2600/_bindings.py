"""ctypes bindings for s2600.dll (Sensoray 2600 middleware).

Copyright: (C) 2026 Maxwell Bloch

This module loads the bundled `lib/s2600.dll` and exposes every exported
`S26_*` function as a first-class ctypes callable. Constants, helper
functions, and `S26Error` are also exported for use by the public package.

The DLL is expected to live at::

    sensoray/s2600/lib/s2600.dll

This module is imported automatically when `sensoray.s2600` is used.
"""

import ctypes
import os
import sys
import warnings
from ctypes import (
    c_uint8, c_uint16, c_uint32, c_int, c_void_p, c_char_p, c_double,
    c_int16, c_int32, POINTER, byref,
)

u8 = c_uint8
u16 = c_uint16
u32 = c_uint32
s16 = c_int16
s32 = c_int32
double = c_double

LOGDEV_GATEWAY = 0x00
LOGDEV_COM1 = 0x01
LOGDEV_COM2 = 0x02
LOGDEV_COM3 = 0x03
LOGDEV_COM4 = 0x04

MODID_GATEWAY = 0xFF

IOM_2608 = 2608
IOM_2610 = 2610
IOM_2612 = 2612
IOM_2620 = 2620
IOM_2631 = 2631
IOM_2650 = 2650
IOM_2652 = 2652
IOM_2653 = 2653

GWERR_NONE = 0x00000000
GWERR_TOOLARGE = 0x00000100
GWERR_XACTALLOC = 0x00000300
GWERR_IOMNORESPOND = 0x00000400
GWERR_MMCLOSED = 0x00000500
GWERR_IOMCLOSED = 0x00000600
GWERR_IOMTYPE = 0x00000700
GWERR_IOMERROR = 0x00000800
GWERR_IOMRESET = 0x00000900
GWERR_MMNORESPOND = 0x00000A00
GWERR_PACKETSEND = 0x00000B00
GWERR_IOMSPECIFIC = 0x00000C00
GWERR_BADVALUE = 0x00000D00
GWERR_THREAD = 0x00000E00
GWERRMASK = 0xFFFFFF00

ERR_NONE = 0x00000000
ERR_BADHANDLE = 0x00000001
ERR_CREATESOCKET = 0x00000002
ERR_BINDSOCKET = 0x00000004
ERR_SEMAPHORE = 0x00000008
ERR_THREAD = 0x00000010
ERR_CRITICALSECTION = 0x00000020
ERR_BUSY = 0x00000040

DRVERR_NONE = 0x00000000
DRVERR_MALLOC = 0x00000001
DRVERR_NETWORKOPEN = 0x00000002
DRVERR_REOPEN = 0x00000004

STATUS_RST = 0x80
STATUS_CERR = 0x40

ADC_SNAPSHOT = 0
ADC_INTEGRATED = 1
LINEFREQ_50HZ = 1
LINEFREQ_60HZ = 0

RAW_LG_TYPE = 0
RAW_HG_TYPE = 1
V_10_TYPE = 2
V_001_TYPE = 3
TC_B_TYPE = 4
TC_C_TYPE = 5
TC_E_TYPE = 6
TC_J_TYPE = 7
TC_K_TYPE = 8
TC_N_TYPE = 9
TC_R_TYPE = 10
TC_S_TYPE = 11
TC_T_TYPE = 12

SIO_BR_300 = 0x0300
SIO_BR_600 = 0x0180
SIO_BR_1200 = 0x00C0
SIO_BR_2400 = 0x0060
SIO_BR_4800 = 0x0030
SIO_BR_9600 = 0x0018
SIO_BR_19200 = 0x000C
SIO_BR_38400 = 0x0006
SIO_BR_57600 = 0x0004
SIO_BR_115200 = 0x0002

SIO_PARITY_NONE = 0x00
SIO_PARITY_ODD = 0x08
SIO_PARITY_EVEN = 0x18
SIO_DATA_5 = 0x00
SIO_DATA_6 = 0x01
SIO_DATA_7 = 0x02
SIO_DATA_8 = 0x03
SIO_STOP_1 = 0x00
SIO_STOP_2 = 0x04
SIO_PHY_RS232 = 0x00
SIO_PHY_RS422_IDLEON = 0x40
SIO_PHY_RS485 = 0x80
SIO_PHY_RS422_IDLEOFF = 0xC0
SIO_FLOW_OFF = 0x00
SIO_FLOW_ON = 0x20
SIO_LED_TRANSMIT = 0x08
SIO_LED_RECEIVE = 0x04
SIO_LED_ERROR = 0x02

COM_REJECTED = 0x80
COM_FRAMINGERROR = 0x08
COM_PARITYERROR = 0x04
COM_OVERFLOWERROR = 0x02
COM_ISOPEN = 0x01

NUM_IOMPORTS = 16
NUM_AINS = 16
DIO_BYTECOUNT = 6
MAX_NUM_AOUTS = 8

# Derived constants that do not have dedicated macros in app2600.h.
REF_OUT_1V = 0
REF_OUT_2V = 1
REF_OUT_3V = 2
REF_OUT_5V = 3

LOAD_2620 = 1
LATCH_2620 = 2

MODE_2631_REVERSE = 1
MODE_2631_RUN = 2

RESP_READY = 0x00000000
RESP_BUSY = 0x00000001

_GWERR_NAMES = {
    GWERR_NONE: "GWERR_NONE",
    GWERR_TOOLARGE: "GWERR_TOOLARGE",
    GWERR_XACTALLOC: "GWERR_XACTALLOC",
    GWERR_IOMNORESPOND: "GWERR_IOMNORESPOND",
    GWERR_MMCLOSED: "GWERR_MMCLOSED",
    GWERR_IOMCLOSED: "GWERR_IOMCLOSED",
    GWERR_IOMTYPE: "GWERR_IOMTYPE",
    GWERR_IOMERROR: "GWERR_IOMERROR",
    GWERR_IOMRESET: "GWERR_IOMRESET",
    GWERR_MMNORESPOND: "GWERR_MMNORESPOND",
    GWERR_PACKETSEND: "GWERR_PACKETSEND",
    GWERR_IOMSPECIFIC: "GWERR_IOMSPECIFIC",
    GWERR_BADVALUE: "GWERR_BADVALUE",
    GWERR_THREAD: "GWERR_THREAD",
}


def err_name(code):
    base = code & GWERRMASK
    extra = code & ~GWERRMASK
    name = _GWERR_NAMES.get(base, "S26_ERR_UNKNOWN")
    return f"{name}+{extra}" if extra else name


class S26Error(Exception):
    def __init__(self, code, fn=""):
        self.code = code
        self.fn = fn
        msg = f"{fn}: 0x{code:08X} ({err_name(code)})" if fn else f"Error 0x{code:08X} ({err_name(code)})"
        super().__init__(msg)


def _candidate_library_names():
    """Native library file names, in preference order, for this platform.

    Each wheel ships exactly one target's library at ``sensoray/s2600/lib``.
    Listing every platform's name keeps a single code path as more targets are
    added (see ``hatch_build.py``).
    """
    if sys.platform == "win32":
        return ("s2600.dll",)
    if sys.platform == "darwin":
        return ("libs2600.dylib",)
    return ("libs2600.so", "libs2600.so.2", "libs2600.so.1")


def _source_tree_payload():
    """Locate a native library in the development source tree, if any.

    Wheels ship the library at ``sensoray/s2600/lib/``. A checkout keeps the
    built libraries under ``_libs/<platform>/`` (see ``hatch_build.py``) and
    only injects one of them when packaging. This lets ``import sensoray.s2600``
    work from a source tree without a build step.

    Only directories listed in ``_candidate_library_names()`` are considered,
    so a stray file cannot be picked up accidentally.
    """
    package_dir = os.path.dirname(os.path.abspath(__file__))
    # src/sensoray/s2600 -> src/sensoray -> src -> project root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(package_dir)))
    libs_root = os.path.join(project_root, "_libs")
    if not os.path.isdir(libs_root):
        return None
    names = _candidate_library_names()
    for entry in sorted(os.listdir(libs_root)):
        target = os.path.join(libs_root, entry)
        if not os.path.isdir(target):
            continue
        for name in names:
            candidate = os.path.join(target, name)
            if os.path.isfile(candidate):
                return os.path.normpath(candidate)
    return None


def _get_bundled_dll_path():
    package_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib")
    for name in _candidate_library_names():
        candidate = os.path.normpath(os.path.join(package_dir, name))
        if os.path.exists(candidate):
            return candidate
    # Fall back to the checkout's _libs/ tree (development installs only).
    from_source_tree = _source_tree_payload()
    if from_source_tree is not None:
        return from_source_tree
    # Nothing bundled: return the preferred name so the error message from
    # _load_and_bind_dll() names the path that was actually expected.
    return os.path.normpath(os.path.join(package_dir, _candidate_library_names()[0]))


def _get_dll_path():
    if "S26_DLL" in os.environ:
        return os.path.normpath(os.environ["S26_DLL"])
    return _get_bundled_dll_path()


def _bind(lib):
    """Register argument and return types for every exported S26_* function."""

    lib.S26_DriverOpen.argtypes = [c_int]
    lib.S26_DriverOpen.restype = c_int
    lib.S26_DriverClose.argtypes = []
    lib.S26_DriverClose.restype = None
    lib.S26_DLLOpen.argtypes = [c_int]
    lib.S26_DLLOpen.restype = c_int
    lib.S26_DLLClose.argtypes = []
    lib.S26_DLLClose.restype = None
    lib.S26_DriverVersion.argtypes = []
    lib.S26_DriverVersion.restype = c_char_p
    lib.S26_ReadStatistics.argtypes = [u32, POINTER(u32)]
    lib.S26_ReadStatistics.restype = c_int

    lib.S26_BoardOpen.argtypes = [u32, c_char_p, c_char_p]
    lib.S26_BoardOpen.restype = u32
    lib.S26_BoardClose.argtypes = [u32]
    lib.S26_BoardClose.restype = None
    lib.S26_RegisterAllIoms.argtypes = [u32, u32, POINTER(u16), POINTER(u16), POINTER(u8), u32]
    lib.S26_RegisterAllIoms.restype = u32
    lib.S26_ResetIom.argtypes = [u32, u8, u32, u32]
    lib.S26_ResetIom.restype = u32
    lib.S26_ResetNetwork.argtypes = [u32]
    lib.S26_ResetNetwork.restype = c_int

    lib.S26_ComClearFlags.argtypes = [u32, u8, u32, u32]
    lib.S26_ComClearFlags.restype = u32
    lib.S26_ComClose.argtypes = [u32, u8, u32, u32]
    lib.S26_ComClose.restype = u32
    lib.S26_ComEndBreak.argtypes = [u32, u8, u32, u32]
    lib.S26_ComEndBreak.restype = u32
    lib.S26_ComFlush.argtypes = [u32, u8, u32, u32]
    lib.S26_ComFlush.restype = u32
    lib.S26_ComGetRxCount.argtypes = [u32, u8, POINTER(u16), u32, u32]
    lib.S26_ComGetRxCount.restype = u32
    lib.S26_ComGetTxCount.argtypes = [u32, u8, POINTER(u16), u32, u32]
    lib.S26_ComGetTxCount.restype = u32
    lib.S26_ComOpen.argtypes = [u32, u8, u32, u32]
    lib.S26_ComOpen.restype = u32
    lib.S26_ComReceive.argtypes = [u32, u8, POINTER(u8), POINTER(u16), u32, u32]
    lib.S26_ComReceive.restype = u32
    lib.S26_ComSend.argtypes = [u32, u8, POINTER(u8), u16, u32, u32]
    lib.S26_ComSend.restype = u32
    lib.S26_ComSetMode.argtypes = [u32, u8, u16, u8, u8, u32, u32]
    lib.S26_ComSetMode.restype = u32
    lib.S26_ComSetBreakChar.argtypes = [u32, u8, u8, u32, u32]
    lib.S26_ComSetBreakChar.restype = u32
    lib.S26_ComStartBreak.argtypes = [u32, u8, u32, u32]
    lib.S26_ComStartBreak.restype = u32

    lib.S26_SchedOpen.argtypes = [u32, u32]
    lib.S26_SchedOpen.restype = c_void_p
    lib.S26_SchedExecute.argtypes = [c_void_p, u32, POINTER(u8)]
    lib.S26_SchedExecute.restype = u32
    lib.S26_SchedExecuteStart.argtypes = [c_void_p, u32]
    lib.S26_SchedExecuteStart.restype = u32
    lib.S26_SchedExecuteIsResponded.argtypes = [c_void_p]
    lib.S26_SchedExecuteIsResponded.restype = c_int
    lib.S26_SchedExecuteWait.argtypes = [c_void_p]
    lib.S26_SchedExecuteWait.restype = u32
    lib.S26_SchedExecuteFinish.argtypes = [c_void_p, POINTER(u8)]
    lib.S26_SchedExecuteFinish.restype = u32

    lib.S26_Sched2600_Nop.argtypes = [c_void_p, u8]
    lib.S26_Sched2600_Nop.restype = u32
    lib.S26_Sched2600_ClearStatus.argtypes = [c_void_p, u8, u8]
    lib.S26_Sched2600_ClearStatus.restype = u32
    lib.S26_Sched2600_IomGetProductID.argtypes = [c_void_p, u8, POINTER(u16)]
    lib.S26_Sched2600_IomGetProductID.restype = u32
    lib.S26_Sched2600_GetFirmwareVersion.argtypes = [c_void_p, u8, POINTER(u16)]
    lib.S26_Sched2600_GetFirmwareVersion.restype = u32
    lib.S26_Sched2600_GetAddress.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2600_GetAddress.restype = u32

    lib.S26_Sched2601_GetLinkStatus.argtypes = [c_void_p, POINTER(u16)]
    lib.S26_Sched2601_GetLinkStatus.restype = u32
    lib.S26_Sched2601_GetInterlocks.argtypes = [c_void_p, POINTER(u8)]
    lib.S26_Sched2601_GetInterlocks.restype = u32
    lib.S26_Sched2601_SetWatchdog.argtypes = [c_void_p, u8]
    lib.S26_Sched2601_SetWatchdog.restype = u32

    lib.S26_2608_AdcCorrect.argtypes = [u32, u8, s16, c_int]
    lib.S26_2608_AdcCorrect.restype = double
    lib.S26_2608_WriteEeprom.argtypes = [u32, u8, u32, u8, u8, u32]
    lib.S26_2608_WriteEeprom.restype = u32
    lib.S26_Sched2608_GetAins.argtypes = [c_void_p, u8, POINTER(double), c_int]
    lib.S26_Sched2608_GetAins.restype = u32
    lib.S26_Sched2608_GetAinTypes.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2608_GetAinTypes.restype = u32
    lib.S26_Sched2608_GetAout.argtypes = [c_void_p, u8, u8, POINTER(double)]
    lib.S26_Sched2608_GetAout.restype = u32
    lib.S26_Sched2608_GetCalData.argtypes = [c_void_p, u8, POINTER(s16)]
    lib.S26_Sched2608_GetCalData.restype = u32
    lib.S26_Sched2608_ReadEeprom.argtypes = [c_void_p, u8, u8, POINTER(u8)]
    lib.S26_Sched2608_ReadEeprom.restype = u32
    lib.S26_Sched2608_SetAinTypes.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2608_SetAinTypes.restype = u32
    lib.S26_Sched2608_SetAout.argtypes = [c_void_p, u8, u8, double]
    lib.S26_Sched2608_SetAout.restype = u32
    lib.S26_Sched2608_SetTempUnits.argtypes = [c_void_p, u8, c_int]
    lib.S26_Sched2608_SetTempUnits.restype = u32
    lib.S26_Sched2608_SetLineFreq.argtypes = [c_void_p, u8, u8]
    lib.S26_Sched2608_SetLineFreq.restype = u32

    lib.S26_Sched2610_GetInputs.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2610_GetInputs.restype = u32
    lib.S26_Sched2610_GetModes.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2610_GetModes.restype = u32
    lib.S26_Sched2610_GetModes32.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2610_GetModes32.restype = u32
    lib.S26_Sched2610_GetOutputs.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2610_GetOutputs.restype = u32
    lib.S26_Sched2610_GetPwmRatio.argtypes = [c_void_p, u8, u8, POINTER(u8), POINTER(u8)]
    lib.S26_Sched2610_GetPwmRatio.restype = u32
    lib.S26_Sched2610_SetModes.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2610_SetModes.restype = u32
    lib.S26_Sched2610_SetModes32.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2610_SetModes32.restype = u32
    lib.S26_Sched2610_SetOutputs.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2610_SetOutputs.restype = u32
    lib.S26_Sched2610_SetPwmRatio.argtypes = [c_void_p, u8, u8, u8, u8]
    lib.S26_Sched2610_SetPwmRatio.restype = u32

    lib.S26_Sched2612_SetMode.argtypes = [c_void_p, u8, u32]
    lib.S26_Sched2612_SetMode.restype = u32
    lib.S26_Sched2612_SetVoltages.argtypes = [c_void_p, u8, u8]
    lib.S26_Sched2612_SetVoltages.restype = u32
    lib.S26_Sched2612_GetValues.argtypes = [c_void_p, u8, POINTER(s32), POINTER(u8)]
    lib.S26_Sched2612_GetValues.restype = u32
    lib.S26_Sched2612_RefreshData.argtypes = [c_void_p, u8]
    lib.S26_Sched2612_RefreshData.restype = u32
    lib.S26_2612_RegisterZero.argtypes = [u32, u8, u32, u8, u32]
    lib.S26_2612_RegisterZero.restype = u32
    lib.S26_2612_RegisterSpan.argtypes = [u32, u8, u32, u8, u32, double]
    lib.S26_2612_RegisterSpan.restype = u32
    lib.S26_2612_RegisterTare.argtypes = [u32, u8, u32, u8, u32]
    lib.S26_2612_RegisterTare.restype = u32
    lib.S26_2612_SaveCalibrations.argtypes = [u32, u8, u32, u8]
    lib.S26_2612_SaveCalibrations.restype = u32
    lib.S26_2612_RestoreCalibrations.argtypes = [u32, u8, u32, u8]
    lib.S26_2612_RestoreCalibrations.restype = u32
    lib.S26_2612_GetCalibratedValue.argtypes = [u32, u8, u8, POINTER(u32)]
    lib.S26_2612_GetCalibratedValue.restype = double
    lib.S26_2612_GetOffset.argtypes = [u32, u8, u8]
    lib.S26_2612_GetOffset.restype = double
    lib.S26_2612_GetScale.argtypes = [u32, u8, u8]
    lib.S26_2612_GetScale.restype = double
    lib.S26_2612_GetTare.argtypes = [u32, u8, u8]
    lib.S26_2612_GetTare.restype = double
    lib.S26_2612_SetCalibrations.argtypes = [u32, u8, u8, double, double, double]
    lib.S26_2612_SetCalibrations.restype = u32

    lib.S26_Sched2620_GetCommonControl.argtypes = [c_void_p, u8, POINTER(u16), POINTER(u8)]
    lib.S26_Sched2620_GetCommonControl.restype = u32
    lib.S26_Sched2620_GetCounts.argtypes = [c_void_p, u8, u8, POINTER(u32), POINTER(u16)]
    lib.S26_Sched2620_GetCounts.restype = u32
    lib.S26_Sched2620_GetMode.argtypes = [c_void_p, u8, u8, POINTER(u16)]
    lib.S26_Sched2620_GetMode.restype = u32
    lib.S26_Sched2620_GetPreload.argtypes = [c_void_p, u8, u8, u8, POINTER(u32)]
    lib.S26_Sched2620_GetPreload.restype = u32
    lib.S26_Sched2620_GetStatus.argtypes = [c_void_p, u8, u8, POINTER(u16)]
    lib.S26_Sched2620_GetStatus.restype = u32
    lib.S26_Sched2620_SetCommonControl.argtypes = [c_void_p, u8, u16, u8]
    lib.S26_Sched2620_SetCommonControl.restype = u32
    lib.S26_Sched2620_SetControlReg.argtypes = [c_void_p, u8, u8, u8]
    lib.S26_Sched2620_SetControlReg.restype = u32
    lib.S26_Sched2620_SetMode.argtypes = [c_void_p, u8, u8, u16]
    lib.S26_Sched2620_SetMode.restype = u32
    lib.S26_Sched2620_SetModeEncoder.argtypes = [c_void_p, u8, u8, u16, u16, u16]
    lib.S26_Sched2620_SetModeEncoder.restype = u32
    lib.S26_Sched2620_SetModeFreqMeas.argtypes = [c_void_p, u8, u8, u16]
    lib.S26_Sched2620_SetModeFreqMeas.restype = u32
    lib.S26_Sched2620_SetModePeriodMeas.argtypes = [c_void_p, u8, u8, u16]
    lib.S26_Sched2620_SetModePeriodMeas.restype = u32
    lib.S26_Sched2620_SetModePulseGen.argtypes = [c_void_p, u8, u8, u16, u16, u16]
    lib.S26_Sched2620_SetModePulseGen.restype = u32
    lib.S26_Sched2620_SetModePulseMeas.argtypes = [c_void_p, u8, u8, u16]
    lib.S26_Sched2620_SetModePulseMeas.restype = u32
    lib.S26_Sched2620_SetModePwmGen.argtypes = [c_void_p, u8, u8, u16]
    lib.S26_Sched2620_SetModePwmGen.restype = u32
    lib.S26_Sched2620_SetPreload.argtypes = [c_void_p, u8, u8, u8, u32]
    lib.S26_Sched2620_SetPreload.restype = u32

    lib.S26_Sched2631_SetControlReg.argtypes = [c_void_p, u8, u8]
    lib.S26_Sched2631_SetControlReg.restype = u32
    lib.S26_Sched2631_GetStatus.argtypes = [c_void_p, u8, POINTER(u16)]
    lib.S26_Sched2631_GetStatus.restype = u32
    lib.S26_Sched2631_SetPreload.argtypes = [c_void_p, u8, u8, u32]
    lib.S26_Sched2631_SetPreload.restype = u32
    lib.S26_Sched2631_GetPreload.argtypes = [c_void_p, u8, u8, POINTER(u32)]
    lib.S26_Sched2631_GetPreload.restype = u32
    lib.S26_Sched2631_GetCounts.argtypes = [c_void_p, u8, POINTER(u32), POINTER(u16)]
    lib.S26_Sched2631_GetCounts.restype = u32
    lib.S26_Sched2631_SetCommonControl.argtypes = [c_void_p, u8, u16, u8]
    lib.S26_Sched2631_SetCommonControl.restype = u32
    lib.S26_Sched2631_GetCommonControl.argtypes = [c_void_p, u8, POINTER(u16), POINTER(u8)]
    lib.S26_Sched2631_GetCommonControl.restype = u32
    lib.S26_Sched2631_SetMode.argtypes = [c_void_p, u8, u16]
    lib.S26_Sched2631_SetMode.restype = u32
    lib.S26_Sched2631_GetMode.argtypes = [c_void_p, u8, POINTER(u16)]
    lib.S26_Sched2631_GetMode.restype = u32
    lib.S26_Sched2631_SetModeEncoder.argtypes = [c_void_p, u8, u16, u16, u16]
    lib.S26_Sched2631_SetModeEncoder.restype = u32
    lib.S26_Sched2631_SetModePulseGen.argtypes = [c_void_p, u8, u16, u16, u16]
    lib.S26_Sched2631_SetModePulseGen.restype = u32
    lib.S26_Sched2631_SetModePwmGen.argtypes = [c_void_p, u8, u16]
    lib.S26_Sched2631_SetModePwmGen.restype = u32
    lib.S26_Sched2631_SetModePulseMeas.argtypes = [c_void_p, u8, u16]
    lib.S26_Sched2631_SetModePulseMeas.restype = u32
    lib.S26_Sched2631_SetModePeriodMeas.argtypes = [c_void_p, u8, u16]
    lib.S26_Sched2631_SetModePeriodMeas.restype = u32
    lib.S26_Sched2631_SetModeFreqMeas.argtypes = [c_void_p, u8, u16]
    lib.S26_Sched2631_SetModeFreqMeas.restype = u32
    lib.S26_Sched2631_OutEnable.argtypes = [c_void_p, u8]
    lib.S26_Sched2631_OutEnable.restype = u32
    lib.S26_Sched2631_SetOutMode.argtypes = [c_void_p, u8]
    lib.S26_Sched2631_SetOutMode.restype = u32
    lib.S26_Sched2631_SetAmpl.argtypes = [c_void_p, u32]
    lib.S26_Sched2631_SetAmpl.restype = u32
    lib.S26_Sched2631_SetOutputFrq.argtypes = [c_void_p, u32]
    lib.S26_Sched2631_SetOutputFrq.restype = u32
    lib.S26_Sched2631_SetPWMFrq.argtypes = [c_void_p, u32]
    lib.S26_Sched2631_SetPWMFrq.restype = u32

    lib.S26_Sched2650_GetInputs.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2650_GetInputs.restype = u32
    lib.S26_Sched2650_GetOutputs.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2650_GetOutputs.restype = u32
    lib.S26_Sched2650_SetOutputs.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2650_SetOutputs.restype = u32

    lib.S26_Sched2652_GetInputs.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2652_GetInputs.restype = u32
    lib.S26_Sched2652_GetOutputs.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2652_GetOutputs.restype = u32
    lib.S26_Sched2652_SetOutputs.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2652_SetOutputs.restype = u32
    lib.S26_Sched2652_GetModes.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2652_GetModes.restype = u32
    lib.S26_Sched2652_GetPwmRatio.argtypes = [c_void_p, u8, u8, POINTER(u8), POINTER(u8)]
    lib.S26_Sched2652_GetPwmRatio.restype = u32
    lib.S26_Sched2652_SetModes.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2652_SetModes.restype = u32
    lib.S26_Sched2652_SetPwmRatio.argtypes = [c_void_p, u8, u8, u8, u8]
    lib.S26_Sched2652_SetPwmRatio.restype = u32

    lib.S26_Sched2653_SetModes.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2653_SetModes.restype = u32
    lib.S26_Sched2653_GetModes.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2653_GetModes.restype = u32
    lib.S26_Sched2653_SetPwmRatio.argtypes = [c_void_p, u8, u8, u8, u8]
    lib.S26_Sched2653_SetPwmRatio.restype = u32
    lib.S26_Sched2653_GetPwmRatio.argtypes = [c_void_p, u8, u8, POINTER(u8), POINTER(u8)]
    lib.S26_Sched2653_GetPwmRatio.restype = u32
    lib.S26_Sched2653_GetInputs.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2653_GetInputs.restype = u32
    lib.S26_Sched2653_GetOutputs.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2653_GetOutputs.restype = u32
    lib.S26_Sched2653_SetOutputs.argtypes = [c_void_p, u8, POINTER(u8)]
    lib.S26_Sched2653_SetOutputs.restype = u32

    lib.S26_CastAsLong.argtypes = [c_void_p]
    lib.S26_CastAsLong.restype = POINTER(u32)
    lib.S26_CastAsShort.argtypes = [c_void_p]
    lib.S26_CastAsShort.restype = POINTER(u16)
    lib.S26_CopyAny.argtypes = [c_void_p, c_void_p, c_int]
    lib.S26_CopyAny.restype = None
    lib.S26_Bitmask.argtypes = [u32]
    lib.S26_Bitmask.restype = u32


def _load_and_bind_dll():
    target_path = _get_dll_path()
    if sys.platform != "win32":
        raise ImportError(
            f"The s2600 native library is not available for this platform "
            f"({sys.platform}); this distribution target is Windows only. "
            f"Set S26_DLL to a locally built library path (looked for: {target_path})."
        )
    if not os.path.exists(target_path):
        raise FileNotFoundError(
            f"Required native library missing from package layout at: {target_path}"
        )
    lib = ctypes.WinDLL(target_path, use_last_error=True)
    _bind(lib)
    return lib


# Load the DLL immediately and bind all signatures. The resulting S26_*
# callables live on the WinDLL instance; we also copy them into this module's
# namespace so the public package can re-export them as module attributes.
try:
    _loaded_lib = _load_and_bind_dll()
except (ImportError, FileNotFoundError) as e:
    _loaded_lib = None
    warnings.warn(f"Runtime binary loading deferred: {e}", ImportWarning)

if _loaded_lib is not None:
    for _name in list(dir(_loaded_lib)):
        if _name.startswith("S26_"):
            globals()[_name] = getattr(_loaded_lib, _name)

__all__ = sorted([_name for _name in globals() if _name.startswith("S26_")] + ["S26Error", "err_name", "load", "lib"])


# Provide a backwards-compatible helper to load/reload the library explicitly.
def load(dll_path=None):
    global _loaded_lib
    if dll_path:
        _loaded_lib = ctypes.WinDLL(os.path.normpath(dll_path), use_last_error=True)
        _bind(_loaded_lib)
    return _loaded_lib


def lib():
    return _loaded_lib
