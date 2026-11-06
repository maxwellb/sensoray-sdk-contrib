"""sensorayd — Sensoray 2600 telemetry daemon (Python port of the SDK's sensorayd.c).

Author   : Maxwell Bloch (github.com/maxwellb)
Copyright: (C) 2026 Maxwell Bloch

This module implements the daemon; ``sensorayd.cli`` provides the console
entry point used by the ``sensorayd`` command (and ``python -m sensorayd``).

Self-describing wide-row polymorphic ingestion core: discovers available
hardware sub-modules and compiles them into dense wide-row CSV payloads with
inline channel-type metadata blocks (e.g. V:V:V:V or D:D:D:D:D:D) for
downstream parsers, broadcast over a local streaming socket to any number of
connected clients. High-resolution UTC timestamps are emitted as the date
fields plus nanoseconds-since-UTC-midnight.

CSV row schema (one row per detected IOM port, per telemetry frame):

    YYYY,MM,DD,<ns since UTC midnight>,<iomport>,<model>,<count>,<type block>,<values...>

- Model 2608 (analog):  count=16, type block ``V:V:...:V`` (16 fields),
  values are measured volts with 4 decimal places.
- Model 2610 (digital): count=6, type block ``D:D:D:D:D:D``, values are the
  six input bytes as ``0x…`` hex (8 digital inputs packed per byte).

Adaptations from the C original (POSIX/Linux):

- pthreads -> ``threading``; usleep(500 ms) -> ``Event.wait(0.5)``.
- The Unix domain socket is served through a raw ws2_32.dll AF_UNIX STREAM
  transport (see ``_winsock_unix``), bypassing Python's ``socket`` module
  entirely: Windows only implements AF_UNIX SOCK_STREAM (no datagrams), and
  CPython does not expose the family. The default socket path is a local
  NTFS temp path (``S26_DAEMON_SOCKET`` overrides it). Many independent
  ephemeral readers can be attached concurrently; each client gets its own
  frame queue + writer thread, with a per-send timeout so a stalled reader
  is dropped rather than holding up the fan-out.
- ``SIGPIPE`` is ignored by catching send errors per client; broken clients
  are dropped on the spot. A full client roster closes new connections
  immediately (the C original silently leaked them).
- SIGINT/SIGTERM/Ctrl+C shut down cleanly: sockets close, then board + driver.
- IOM models other than 2608/2610 are skipped (the C original re-broadcast a
  stale buffer for them).

Hardware poll rate is throttled to 500 ms; gateway transactions use the SDK
default of msec=100 / retries=50.

Run (adjust MM IP as needed):

    cd src/python/src
    uv run python -m _utils.sensorayd [MM_IP] [OPTION]

Options:

- ``--tcp [PORT]`` — bind ``127.0.0.1:PORT`` (default 26010) instead of the
  AF_UNIX socket. TCP is an explicit, opt-in alternate binding; the daemon
  never silently switches transports.

Connect with any AF_UNIX stream client (``nc -U`` on POSIX, .NET
``UnixDomainSocketEndPoint`` / ``af_unix`` tooling on Windows), or a plain
TCP client when ``--tcp`` is active. The bound endpoint is printed at
startup.
"""

import argparse
import ctypes
import os
import queue
import signal
import socket
import sys
import tempfile
import threading
import time
from contextlib import suppress
from ctypes import byref

from sensoray import s2600
from sensorayd import _winsock_unix as wsaunix

TARGET_IP = "10.10.10.1"
MMHANDLE = 0
MSEC_GATEWAY = 100
GATEWAY_RETRIES = 50
POLL_MSEC = 500

SOCKET_PATH = os.environ.get(
    "S26_DAEMON_SOCKET",
    os.path.join(tempfile.gettempdir(), "sensoray.sock"),
)  # Windows AF_UNIX binds require a local NTFS path; /tmp is not one.
BACKLOG = 64                    # pending connections while all slots busy
MAX_CLIENTS = 10
SEND_TIMEOUT_MSEC = 250         # per-send cap so one stalled reader cannot freeze fan-out
TCP_DEFAULT_PORT = 26010        # used only when --tcp is passed

NUM_PORTS = s2600.NUM_IOMPORTS    # 16
NUM_DIN_BYTES = s2600.DIO_BYTECOUNT  # 6


# --- Daemon state -----------------------------------------------------------

running = threading.Event()

# --- Core hardware storage matrices -----------------------------------------

iom_type = [0] * NUM_PORTS
volts_matrix = [(ctypes.c_double * NUM_PORTS)() for _ in range(NUM_PORTS)]
din_matrix = [(ctypes.c_uint8 * NUM_DIN_BYTES)() for _ in range(NUM_PORTS)]
dac_channels = [ctypes.c_uint8(0) for _ in range(NUM_PORTS)]

# --- Client roster ----------------------------------------------------------

# Map of raw socket handle -> client record (dict for ordered fan-out + remove).
_clients = {}
_clients_lock = threading.Lock()
_server_sock = None


def add_client(handle, transport=None):
    """Register a client socket with its own outbound frame queue + writer.

    *transport* is optional; pass an object with ``send_all``/``close`` for
    bridges that are not raw winsock handles (e.g. the --tcp wrapper).
    """
    rec = {
        "handle": handle,
        "transport": transport,
        "frames": queue.SimpleQueue(),      # unbounded; writer thread drains.
        "alive": True,
    }
    if transport is None:
        try:
            wsaunix.set_send_timeout(handle, SEND_TIMEOUT_MSEC)
        except OSError as e:
            print(f"[!] Could not set send timeout on client {handle}: {e}")
    with _clients_lock:
        _clients[handle] = rec
    threading.Thread(
        target=_client_writer, args=(rec,), name=f"client-{handle}", daemon=True
    ).start()


def remove_client(handle, quiet=True):
    with _clients_lock:
        rec = _clients.pop(handle, None)
    if rec is not None:
        rec["alive"] = False
        closer = rec["transport"].close if rec["transport"] else wsaunix.close
        with suppress(OSError):
            closer(handle)
    if not quiet:
        print(f"[*] Dropped telemetry client {handle}")


def _client_writer(rec):
    """Drain the client's frame queue onto its socket until dropped."""
    handle = rec["handle"]
    send = rec["transport"].send_all if rec["transport"] else wsaunix.send_all
    while rec["alive"] and running.is_set():
        try:
            frame = rec["frames"].get(timeout=0.5)
        except queue.Empty:
            continue
        try:
            send(handle, frame)
        except (TimeoutError, ConnectionResetError, BrokenPipeError) as e:
            if not isinstance(e, TimeoutError):
                print(f"[*] Client {handle} dropped: {e}")
            remove_client(handle, quiet=False)
            return
        except OSError as e:
            print(f"[*] Client {handle} dropped: {e}")
            remove_client(handle, quiet=False)
            return


def broadcast_telemetry(csv_row):
    """Enqueue one CSV row for every connected reader; slow clients drop."""
    payload = csv_row if isinstance(csv_row, bytes) else csv_row.encode("ascii")
    with _clients_lock:
        targets = list(_clients.values())
    for rec in targets:
        rec["frames"].put(payload)


def utc_timestamp():
    """UTC wall clock -> (struct_time, ns since UTC midnight)."""
    sec, nsec = divmod(time.time_ns(), 1_000_000_000)
    t = time.gmtime(sec)
    ns_midnight = ((t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec) * 1_000_000_000) + nsec
    return t, ns_midnight


def init_hardware(mm_ip):
    """Open driver/board, discover IOMs, and stage their configuration."""
    global iom_type

    print("[*] Opening driver layer...")
    faults = s2600.S26_DriverOpen(1)
    if faults != 0:
        print(f"[-] DriverOpen() fault: {faults}")
        return False

    print(f"[*] Binding to Board at {mm_ip}...")
    faults = s2600.S26_BoardOpen(MMHANDLE, None, mm_ip.encode("ascii"))
    if faults != 0:
        print(f"[-] BoardOpen() fault: {faults}")
        s2600.S26_DriverClose()
        return False

    print("[*] Resetting Network I/O system...")
    s2600.S26_ResetNetwork(MMHANDLE)

    print("[*] Probing network for active IOM sub-modules...")
    nboards = ctypes.c_uint16(0)
    types_buf = (ctypes.c_uint16 * NUM_PORTS)()
    status_buf = (ctypes.c_uint8 * NUM_PORTS)()
    faults = s2600.S26_RegisterAllIoms(
        MMHANDLE, MSEC_GATEWAY, byref(nboards), types_buf, status_buf, GATEWAY_RETRIES
    )
    if faults != 0 or nboards.value == 0:
        print(f"[-] Registration failed or 0 modules unmasked. Fault: {faults}")
        s2600.S26_BoardClose(MMHANDLE)
        s2600.S26_DriverClose()
        return False
    iom_type = list(types_buf)

    print(f"[+] Subsystem Online. Detected {nboards.value} active hardware expansion node(s).")

    # Stage 1: gateway status + per-2608 DAC channel count (EEPROM address 0).
    link_flags = ctypes.c_uint16(0)
    lock_flags = ctypes.c_uint8(0)
    x = s2600.S26_SchedOpen(MMHANDLE, GATEWAY_RETRIES)
    s2600.S26_Sched2601_GetLinkStatus(x, byref(link_flags))
    s2600.S26_Sched2601_GetInterlocks(x, byref(lock_flags))
    for port, t in enumerate(iom_type):
        if t == s2600.IOM_2608:
            s2600.S26_Sched2608_ReadEeprom(x, port, 0, byref(dac_channels[port]))
    if (faults := s2600.S26_SchedExecute(x, MSEC_GATEWAY, status_buf)) != 0:
        print(f"[-] Stage 1 Configuration Matrix Fetch Denied: 0x{faults:X}")
        s2600.S26_BoardClose(MMHANDLE)
        s2600.S26_DriverClose()
        return False

    # Stage 2: line frequency, input types, zero all DAC rails.
    ain_types = (ctypes.c_uint8 * NUM_PORTS)(*[s2600.V_10_TYPE] * NUM_PORTS)
    x = s2600.S26_SchedOpen(MMHANDLE, GATEWAY_RETRIES)
    for port, t in enumerate(iom_type):
        if t == s2600.IOM_2608:
            print(f"[+] Mapping Analog Hub | Port {port:02d} | Model 2608 | DAC Rails: {dac_channels[port].value}")
            s2600.S26_Sched2608_SetLineFreq(x, port, s2600.LINEFREQ_60HZ)
            s2600.S26_Sched2608_SetAinTypes(x, port, ain_types)
            for chan in range(dac_channels[port].value):
                s2600.S26_Sched2608_SetAout(x, port, chan, 0.0)
        elif t == s2600.IOM_2610:
            print(f"[+] Mapping Digital Hub | Port {port:02d} | Model 2610")
    if (faults := s2600.S26_SchedExecute(x, MSEC_GATEWAY, status_buf)) != 0:
        print(f"[-] Stage 2 Configuration Implementation Denied: 0x{faults:X}")
        s2600.S26_BoardClose(MMHANDLE)
        s2600.S26_DriverClose()
        return False

    print("[+] Hardware deployment complete. Systems synchronized.")
    return True


def telemetry_loop():
    print(f"[*] Launching Hardware Polling Engine (Throttled Matrix: {POLL_MSEC}ms)...")
    while running.is_set():
        x = s2600.S26_SchedOpen(MMHANDLE, GATEWAY_RETRIES)
        if x:
            for port, t in enumerate(iom_type):
                if t == s2600.IOM_2608:
                    s2600.S26_Sched2608_GetAins(x, port, volts_matrix[port], s2600.ADC_INTEGRATED)
                elif t == s2600.IOM_2610:
                    s2600.S26_Sched2610_GetInputs(x, port, din_matrix[port])

            err = s2600.S26_SchedExecute(x, MSEC_GATEWAY, (ctypes.c_uint8 * NUM_PORTS)())
            if err == 0:
                t, ns_midnight = utc_timestamp()
                year = t.tm_year + 1900
                month = t.tm_mon + 1
                day = t.tm_mday

                print(
                    f"[{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}] "
                    "Telemetry Frame Captured | Channels Synchronized",
                    flush=True,
                )

                for port, t_iom in enumerate(iom_type):
                    if t_iom == 0:
                        continue
                    if t_iom == s2600.IOM_2608:
                        header = ",".join(
                            str(part)
                            for part in (
                                year, month, day, ns_midnight, port, s2600.IOM_2608,
                                NUM_PORTS, ":".join(["V"] * NUM_PORTS),
                            )
                        )
                        values = "," + ",".join(f"{volts_matrix[port][chan]:.4f}" for chan in range(NUM_PORTS))
                        row = header + values
                    elif t_iom == s2600.IOM_2610:
                        header = ",".join(
                            str(part)
                            for part in (
                                year, month, day, ns_midnight, port, s2600.IOM_2610,
                                NUM_DIN_BYTES, ":".join(["D"] * NUM_DIN_BYTES),
                            )
                        )
                        values = "," + ",".join(f"0x{din_matrix[port][b]:02X}" for b in range(NUM_DIN_BYTES))
                        row = header + values
                    else:
                        # Other IOM families are not wide-row formatted here.
                        continue

                    broadcast_telemetry((row + "\n").encode("ascii"))
            else:
                print(f"[!] WARNING: Framework desynchronization unmasked (Error Mask: {err})\n", flush=True)
        running.wait(POLL_MSEC / 1000.0)
    print("[*] Hardware Polling Engine stopped.", flush=True)


def socket_server(tcp_port=None):
    """Serve telemetry on the transport selected at startup.

    ``tcp_port is None`` binds the raw AF_UNIX stream socket at
    :data:`SOCKET_PATH` (the default). An integer binds localhost TCP
    instead — that mode must be opted into explicitly with ``--tcp [PORT]``;
    the daemon never silently switches transports.
    """
    global _server_sock

    if tcp_port is None:
        if wsaunix.startup() != "af_unix":
            print("[-] AF_UNIX is unavailable on this OS; rerun with --tcp [PORT].")
            running.clear()
            return
        print(f"[+] Streaming polymorphic telemetry on unix socket {SOCKET_PATH}")
        _server_sock = _serve_unix()
    else:
        _serve_tcp(tcp_port)


def _serve_unix():
    """AF_UNIX stream server loop; returns the raw listener handle."""
    try:
        server = wsaunix.create_server_socket(SOCKET_PATH, backlog=BACKLOG)
    except OSError as e:
        print(f"[-] Failed to bind telemetry socket: {e}")
        running.clear()
        return None

    while running.is_set():
        handle = wsaunix.accept(server)
        if handle is None:
            time.sleep(0.05)
            continue
        with _clients_lock:
            full = len(_clients) >= MAX_CLIENTS
        if full:
            wsaunix.close(handle)
            continue
        # Accepted stream is independent; ephemeral readers connect, drain
        # (or not), and vanish — no inbound reader thread is required. The
        # per-client writer thread owns the socket and cleans up on send
        # failure or daemon shutdown.
        add_client(handle)

    wsaunix.close(server)
    print("[*] Telemetry socket closed.", flush=True)
    return None


def _serve_tcp(port):
    """Alternate binding: localhost TCP stream, opted in with --tcp."""
    global _server_sock

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _server_sock = srv
    srv.settimeout(0.5)
    try:
        srv.bind(("127.0.0.1", port))
    except OSError as e:
        print(f"[-] Failed to bind TCP telemetry socket: {e}")
        running.clear()
        return
    srv.listen(MAX_CLIENTS)
    print(f"[+] Streaming polymorphic telemetry on tcp://127.0.0.1:{port}")

    while running.is_set():
        try:
            client_sock, _ = srv.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        with _clients_lock:
            full = len(_clients) >= MAX_CLIENTS
        if full:
            with suppress(OSError):
                client_sock.close()
            continue
        # Wrap the TCP socket so the same broadcast/queue pipeline works.
        bridge = _TcpSocketBridge(client_sock)
        add_client(bridge.handle, transport=bridge)

    srv.close()
    print("[*] Telemetry socket closed.", flush=True)


class _TcpSocketBridge:
    """Adapter exposing wsaunix-like send/close semantics over python socket."""

    def __init__(self, sock):
        self.sock = sock
        self.handle = id(sock)    # stable key for the roster map

    def send_all(self, _handle, payload):
        self.sock.sendall(payload)

    def close(self, _handle=None):
        with suppress(OSError):
            self.sock.close()


def parse_args(argv):
    parser = argparse.ArgumentParser(
        prog="sensorayd",
        description=(
            "Sensoray 2600 telemetry daemon: wide-row CSV frames over a local "
            "streaming socket (AF_UNIX by default)."
        ),
    )
    parser.add_argument(
        "mm_ip", nargs="?", default=TARGET_IP,
        help=f"MM gateway IP (default {TARGET_IP})",
    )
    parser.add_argument(
        "--tcp", nargs="?", const=TCP_DEFAULT_PORT, default=None, type=int,
        metavar="PORT",
        help=(
            "bind localhost TCP on PORT instead of the AF_UNIX socket"
            f" (default {TCP_DEFAULT_PORT})"
        ),
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    mm_ip = args.mm_ip

    def _stop(signum, frame):
        running.clear()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress((ValueError, OSError)):
            signal.signal(sig, _stop)

    if not init_hardware(mm_ip):
        return 1

    running.set()
    tel_thread = threading.Thread(target=telemetry_loop, name="telemetry", daemon=True)
    sock_thread = threading.Thread(
        target=socket_server, args=(args.tcp,), name="socket-server", daemon=True
    )
    tel_thread.start()
    sock_thread.start()

    try:
        while running.is_set() and tel_thread.is_alive() and sock_thread.is_alive():
            tel_thread.join(0.5)
            sock_thread.join(0.5)
    except KeyboardInterrupt:
        running.clear()

    running.clear()
    with suppress(OSError):
        if _server_sock is not None:
            if isinstance(_server_sock, socket.socket):
                _server_sock.close()
            else:
                wsaunix.close(_server_sock)
    tel_thread.join(2)
    sock_thread.join(2)
    with _clients_lock:
        leftovers = list(_clients)
    for handle in leftovers:
        remove_client(handle, quiet=True)

    print("[*] Closing hardware...")
    s2600.S26_BoardClose(MMHANDLE)
    s2600.S26_DriverClose()
    return 0


if __name__ == "__main__":
    sys.exit(main())