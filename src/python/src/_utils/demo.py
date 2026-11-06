"""Sensoray 2600 demo, ported to Python (mirrors src/x86_64-w64-mingw32/demo.c).

Author   : Maxwell Bloch (github.com/maxwellb)
Copyright: (C) 2026 Maxwell Bloch
"""

import ctypes
import time
from ctypes import byref

from sensoray import s2600

MM_IP = "10.10.10.1"
MMHANDLE = 0
MSEC_GATEWAY = 100
MSEC_COMPORT = 100
COM_RETRIES = 50
GATEWAY_RETRIES = 50

CHAN_WIDTH = 0
CHAN_FREQ = 1
CHAN_PWM = 2
CHAN_ENCODER = 3

COM_SRC_A = s2600.LOGDEV_COM2
COM_DST_A = s2600.LOGDEV_COM1
COM_BR_A = s2600.SIO_BR_9600
COM_SRC_B = s2600.LOGDEV_COM4
COM_DST_B = s2600.LOGDEV_COM3
COM_BR_B = s2600.SIO_BR_115200

AINTYPES = [s2600.V_10_TYPE] * 16

iters = 0
total_sent = 0
iom_type = [0] * 16
iom_status = [0] * 16
n_aouts = [0] * 16
relay_states = 0
dout_states = [0] * 6
aout = [0.0] * 8

# Out-param buffers (filled during S26_SchedExecute, read afterwards).
ain_buf = (ctypes.c_double * 16)()
din_buf = (ctypes.c_uint8 * 6)()
dout_buf = (ctypes.c_uint8 * 6)()
counts_buf = [ctypes.c_uint32() for _ in range(4)]
timestamp_buf = [ctypes.c_uint16() for _ in range(4)]


def show_error(gwerr, status):
    print(f"Error: 0x{gwerr:08X} ({s2600.err_name(gwerr)}), iters = {iters}.")


def com_error(gwerr, fname):
    flags = s2600.COM_FRAMINGERROR | s2600.COM_PARITYERROR | s2600.COM_OVERFLOWERROR | s2600.COM_REJECTED
    if (gwerr & s2600.GWERRMASK) or (gwerr & flags):
        print(f"{fname}() error: 0x{gwerr:08X} ({s2600.err_name(gwerr)}), iters = {iters}.")
        return gwerr
    return 0


def detect_all_ioms():
    global iom_type, iom_status
    err, iom_type, iom_status = s2600.register_all_ioms(MMHANDLE, MSEC_GATEWAY, GATEWAY_RETRIES)
    if err:
        show_error(err, iom_status)
        return False

    print("DETECTED IOM'S:")
    for port, t in enumerate(iom_type):
        if t:
            print(f" port {port:2d}: {t:4d}")
    return True


def create_transaction():
    x = s2600.sched_open(MMHANDLE, GATEWAY_RETRIES)
    if not x:
        print("Error: S26_SchedOpen() failed to allocate a transaction object.")
    return x


def io_exec(x):
    global iom_status
    err, iom_status = s2600.sched_execute(x, MSEC_GATEWAY)
    if err:
        show_error(err, iom_status)
    return err


def sched_io(x):
    L = s2600.lib()

    L.S26_Sched2601_GetLinkStatus(x, byref(ctypes.c_uint16()))
    L.S26_Sched2601_GetInterlocks(x, byref(ctypes.c_uint8()))

    for port, t in enumerate(iom_type):
        if t == s2600.IOM_2608:
            L.S26_Sched2608_GetCalData(x, port, None)
            L.S26_Sched2608_GetAins(x, port, ain_buf, s2600.ADC_INTEGRATED)
            for chan in range(n_aouts[port]):
                L.S26_Sched2608_SetAout(x, port, chan, ctypes.c_double(aout[chan]))
        elif t == s2600.IOM_2610:
            L.S26_Sched2610_SetOutputs(x, port, dout_buf)
            L.S26_Sched2610_GetInputs(x, port, din_buf)
        elif t == s2600.IOM_2620:
            L.S26_Sched2620_SetControlReg(x, port, CHAN_PWM, 2)
            L.S26_Sched2620_SetControlReg(x, port, CHAN_ENCODER, 2)
            for chan in range(4):
                L.S26_Sched2620_GetCounts(x, port, chan, byref(counts_buf[chan]), byref(timestamp_buf[chan]))
        elif t in (s2600.IOM_2650, s2600.IOM_2652):
            L.S26_Sched2650_SetOutputs(x, port, byref(ctypes.c_uint8(relay_states)))


def serial_init(src, dst, baud):
    attrs = s2600.SIO_PHY_RS232 | s2600.SIO_PARITY_NONE | s2600.SIO_DATA_8 | s2600.SIO_STOP_1 | s2600.SIO_FLOW_OFF
    L = s2600.lib()

    err = L.S26_ComSetMode(MMHANDLE, src, baud, attrs, s2600.SIO_LED_TRANSMIT, MSEC_COMPORT, COM_RETRIES)
    if com_error(err, "S26_ComSetMode"):
        return 1
    err = L.S26_ComOpen(MMHANDLE, src, MSEC_COMPORT, COM_RETRIES)
    if com_error(err, "S26_ComOpen"):
        return 1

    err = L.S26_ComSetMode(MMHANDLE, dst, baud, attrs, s2600.SIO_LED_RECEIVE, MSEC_COMPORT, COM_RETRIES)
    if com_error(err, "S26_ComSetMode"):
        return 1
    err = L.S26_ComOpen(MMHANDLE, dst, MSEC_COMPORT, COM_RETRIES)
    if com_error(err, "S26_ComOpen"):
        return 1

    return 0


def serial_io(src, dst):
    global total_sent
    msg = f"12345678901234567890123456:{iters}\n".encode("ascii")
    L = s2600.lib()

    buf = (ctypes.c_uint8 * len(msg))(*msg)
    err = L.S26_ComSend(MMHANDLE, src, buf, len(msg), MSEC_COMPORT, COM_RETRIES)
    if com_error(err, "S26_ComSend"):
        print(f"TotalSent = {total_sent}")
        return 1
    total_sent += len(msg)

    rbuf = (ctypes.c_uint8 * 1024)()
    rlen = ctypes.c_uint16(1024)
    err = L.S26_ComReceive(MMHANDLE, dst, rbuf, byref(rlen), MSEC_COMPORT, COM_RETRIES)
    if com_error(err, "S26_ComReceive"):
        print(f"TotalSent = {total_sent}")
        return 1

    return 0


def io_control_loop():
    global iters, relay_states, dout_states, aout
    tmax = 0.0

    while True:
        relay_states = (relay_states + 1) & 0xFF
        for i in range(6):
            dout_states[i] = (dout_states[i] + 1) & 0xFF
        for chan in range(8):
            aout[chan] = float(chan + 1)

        if serial_io(COM_SRC_A, COM_DST_A):
            return iters
        if serial_io(COM_SRC_B, COM_DST_B):
            return iters

        x = create_transaction()
        sched_io(x)

        start = time.perf_counter()
        if io_exec(x):
            print("Terminating i/o control loop.")
            break
        tmax = max(tmax, (time.perf_counter() - start) * 1000.0)

        iters += 1

    print(f"Worst-case I/O time (msec):  {tmax:.0f}")
    return iters


def io_control_main():
    global iters, n_aouts
    L = s2600.lib()

    serial_init(COM_SRC_A, COM_DST_A, COM_BR_A)
    serial_init(COM_SRC_B, COM_DST_B, COM_BR_B)

    x = create_transaction()

    for port, t in enumerate(iom_type):
        if t == s2600.IOM_2608:
            v = ctypes.c_uint8()
            L.S26_Sched2608_ReadEeprom(x, port, 0, byref(v))
            n_aouts[port] = v.value
            L.S26_Sched2608_SetLineFreq(x, port, s2600.LINEFREQ_60HZ)
            types = (ctypes.c_uint8 * 16)(*AINTYPES)
            L.S26_Sched2608_SetAinTypes(x, port, types)
        elif t == s2600.IOM_2620:
            L.S26_Sched2620_SetCommonControl(x, port, 1000, 3)
            L.S26_Sched2620_SetPreload(x, port, CHAN_PWM, 1, 99)
            L.S26_Sched2620_SetPreload(x, port, CHAN_PWM, 0, 4899)
            L.S26_Sched2620_SetModePwmGen(x, port, CHAN_PWM, 0)
            L.S26_Sched2620_SetModeFreqMeas(x, port, CHAN_FREQ, 1)
            L.S26_Sched2620_SetModePulseMeas(x, port, CHAN_WIDTH, 0)
            L.S26_Sched2620_SetModeEncoder(x, port, CHAN_ENCODER, 0, 0, 3)

    if io_exec(x):
        return

    print("Running main control loop\nHit any key to terminate")
    start = time.time()
    iters = io_control_loop()
    elapsed = time.time() - start

    for port, t in enumerate(iom_type):
        if t == s2600.IOM_2608:
            print("AIN states:")
            for v in ain_buf:
                print(f" {v:8f}")
        elif t == s2600.IOM_2610:
            print("DIN states:", " ".join(f"{b:02X}" for b in din_buf))
        elif t == s2600.IOM_2620:
            print("Counter states:", " ".join(f"{j}:{counts_buf[j].value:08X}" for j in range(4)))

    print(f"Control loop cycles:    {iters}")
    print(f"Elapsed time (seconds): {elapsed:.0f}")
    print(f"Average I/O cycle time (msec):  {elapsed / iters * 1000.0:.2f}")


def main():
    s2600.load()

    print(f"Driver version : {s2600.driver_version()}")

    err = s2600.lib().S26_DriverOpen(1)
    print(f"DriverOpen     : {err}")
    if err:
        return 1

    err = s2600.board_open(MMHANDLE, MM_IP)
    print(f"BoardOpen      : 0x{err:08X}")
    if err:
        s2600.lib().S26_DriverClose()
        return 1

    s2600.lib().S26_ResetNetwork(MMHANDLE)

    if detect_all_ioms():
        io_control_main()

    s2600.lib().S26_DriverClose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
