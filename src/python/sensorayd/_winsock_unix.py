"""Raw ws2_32.dll transport for Windows AF_UNIX stream sockets.

Author   : Maxwell Bloch (github.com/maxwellb)
Copyright: (C) 2026 Maxwell Bloch

Windows 10 (1803+) implements AF_UNIX in Winsock, but CPython does not expose
the address family, so this module talks to ``ws2_32.dll`` directly via ctypes:

- ``sockaddr_un`` is mapped by hand (u16 family + 108-byte sun_path).
- Per the OS limitation, only ``SOCK_STREAM`` is supported; AF_UNIX datagram
  sockets do not exist on Windows.
- All handles are raw ``SOCKET`` values (unsigned pointer-size integers).
  Do NOT wrap them in ``socket.socket``.

Concurrency model: every accepted connection is an independent stream, so any
number of ephemeral readers may hold their sockets simultaneously. Outgoing
sends carry a short timeout (``SO_SNDTIMEO``) so one slow or stalled client
cannot block the broadcaster past the deadline; a client that cannot drain in
time raises ``TimeoutError`` and is dropped by the caller.

Import is safe on any platform, but every function except :func:`supported`
raises ``NotImplementedError`` on non-Windows systems.
"""

import sys
from ctypes import (
    Structure, POINTER, WinDLL, byref, c_char, c_char_p, c_int, c_size_t,
    c_uint, c_ushort, c_void_p, create_string_buffer, sizeof,
)

# Winsock constants ------------------------------------------------------------
AF_UNIX = 1                 # Windows maps AF_UNIX to 1, as POSIX does.
SOCK_STREAM = 1
SOCK_DGRAM = 2              # Defined for completeness; UNSUPPORTED for AF_UNIX.
SOL_SOCKET = 0xFFFF
SO_SNDTIMEO = 0x1006
FD_SETSIZE = 64
WSAEAFNOSUPPORT = 10047     # OS lacks AF_UNIX (Windows < 1803)
WSAEADDRINUSE = 10048
WSAEWOULDBLOCK = 10035

SOCKET = c_size_t           # SOCKET == UINT_PTR on x64/Win64.
INVALID_SOCKET = c_size_t(-1).value   # (~0) as unsigned UINT_PTR
SOCKET_ERROR = -1                     # winsock int-returning calls use this

_WSAOVERLAPPED_SIZE = 0     # Unused placeholder; winsock structs kept opaque.

WSA_FLAG_OVERLAPPED = 0x01


class WSABuf(Structure):
    _fields_ = [("len", c_size_t), ("buf", c_char * 0)]


class _WSAData(Structure):
    _fields_ = [
        ("wVersion", c_ushort),
        ("wHighVersion", c_ushort),
        ("iMaxSockets", c_ushort),
        ("iMaxUdpDg", c_ushort),
        ("lpVendorInfo", POINTER(c_char)),
        ("szDescription", c_char * 257),
        ("szSystemStatus", c_char * 129),
    ]


class sockaddr_un(Structure):
    """struct sockaddr_un, as WS2_32 expects it for AF_UNIX (108-byte path)."""
    _fields_ = [
        ("sun_family", c_ushort),          # af = 1 on Windows == POSIX AF_UNIX.
        ("sun_path", c_char * 108),
    ]
    __slots__ = ()


def _addr_union():
    class _AddrUnion(Structure):
        _fields_ = [("generic", c_char * 16), ("un", sockaddr_un)]
    return _AddrUnion


# Library handles (created lazily in _bootstrap()).
_ws2 = None


def _bootstrap():
    """Resolve ws2_32 entry points and start WSA once per process."""
    global _ws2

    if _ws2 is not None:
        return

    dll = WinDLL("ws2_32")
    dll.WSAStartup.argtypes = [c_ushort, POINTER(_WSAData)]
    dll.WSAStartup.restype = c_int
    dll.socket.argtypes = [c_int, c_int, c_int]
    dll.socket.restype = SOCKET
    dll.bind.argtypes = [SOCKET, c_void_p, c_int]
    dll.bind.restype = c_int
    dll.listen.argtypes = [SOCKET, c_int]
    dll.listen.restype = c_int
    dll.accept.argtypes = [SOCKET, c_void_p, POINTER(c_int)]
    dll.accept.restype = SOCKET
    dll.send.argtypes = [SOCKET, c_char_p, c_int, c_int]
    dll.send.restype = c_int
    dll.recv.argtypes = [SOCKET, c_void_p, c_int, c_int]
    dll.recv.restype = c_int
    dll.closesocket.argtypes = [SOCKET]
    dll.closesocket.restype = c_int
    dll.setsockopt.argtypes = [SOCKET, c_int, c_int, c_char_p, c_int]
    dll.setsockopt.restype = c_int
    dll.WSAGetLastError.argtypes = []
    dll.WSAGetLastError.restype = c_int

    data = _WSAData()
    rc = dll.WSAStartup(0x0202, byref(data))
    if rc != 0:
        raise OSError(f"WSAStartup failed: {rc}")

    _ws2 = dll


def _check():
    if _ws2 is None:
        raise OSError("Winsock transport not initialized; call startup() first.")


def _family_supported(af):
    """Probe whether the kernel exposes an address family (socket/create probe)."""
    s = _ws2.socket(af, SOCK_STREAM, 0)
    if s == INVALID_SOCKET:
        return False
    _ws2.closesocket(s)
    return True


def supported():
    """True when this Windows kernel exposes AF_UNIX stream sockets."""
    _bootstrap()
    return _family_supported(AF_UNIX)


def startup():
    """Idempotent WSA + capability probe.

    Returns ``"af_unix"`` when the OS supports AF_UNIX sockets, ``"none"``
    otherwise. Callers (e.g. the daemon) may use it to pick a fallback
    transport. Raises ``NotImplementedError`` on non-Windows systems.
    """
    if sys.platform == "win32":
        _bootstrap()
        return "af_unix" if _family_supported(AF_UNIX) else "none"
    raise NotImplementedError("ws2_32 transport is Windows-only.")


def create_server_socket(path, backlog=64):
    """Create a bound, listening AF_UNIX SOCK_STREAM socket at *path*.

    Returns the raw SOCKET handle. An existing file at *path* is removed first
    (stale bind artifacts). Raises ``OSError`` on EADDRINUSE or any kernel
    rejection.
    """
    _check()
    if sys.platform != "win32":
        raise NotImplementedError("ws2_32 transport is Windows-only.")

    from pathlib import Path

    p = Path(path)
    if p.exists():
        try:
            p.unlink()
        except OSError as e:
            raise OSError(f"Cannot replace existing telemetry socket {path}: {e}") from e

    handle = _ws2.socket(AF_UNIX, SOCK_STREAM, 0)
    if handle == INVALID_SOCKET:
        err = _ws2.WSAGetLastError()
        if err == WSAEAFNOSUPPORT:
            raise OSError(
                10047, "Windows reports AF_UNIX is unsupported (need Windows 10 1803+)"
            )
        raise OSError(err, "socket() failed for AF_UNIX stream")

    addr = sockaddr_un()
    addr.sun_family = AF_UNIX
    encoded = str(path).encode("utf-8")
    addr.sun_path = encoded[:107]               # keep room for NUL

    rc = _ws2.bind(handle, byref(addr), sizeof(addr))
    if rc != 0:
        err = _ws2.WSAGetLastError()
        _ws2.closesocket(handle)
        raise OSError(err, f"bind({path}) failed")

    rc = _ws2.listen(handle, backlog)
    if rc != 0:
        err = _ws2.WSAGetLastError()
        _ws2.closesocket(handle)
        raise OSError(err, f"listen({path}) failed")

    return handle


def accept(server_handle):
    """Accept one client on a bound server socket.

    Returns the client's raw SOCKET handle, or ``None`` if the operation would
    block or was interrupted. Accepted sockets inherit the listener's blocking
    nature; callers may apply send timeout via :func:`set_send_timeout`.
    """
    _check()
    client = c_int(0)
    addrlen = c_int(sizeof(sockaddr_un))
    peer_addr = sockaddr_un()
    handle = _ws2.accept(SOCKET(server_handle), byref(peer_addr), byref(addrlen))
    if handle == INVALID_SOCKET:
        err = _ws2.WSAGetLastError()
        if err == WSAEWOULDBLOCK:
            return None
        raise OSError(err, "accept() failed on AF_UNIX listener")
    return handle


def set_send_timeout(handle, msec):
    """Apply SO_SNDTIMEO so broadcast() cannot stall longer than *msec* per client.

    A slow or stopped client past the deadline raises TimeoutError on the next
    send attempt and is dropped, keeping the broadcaster responsive to the
    many-ephemeral-readers workloads.
    """
    _check()
    timeout = c_int(int(msec))
    opt = create_string_buffer(bytes(timeout)[:sizeof(c_int)])
    rc = _ws2.setsockopt(SOCKET(handle), SOL_SOCKET, SO_SNDTIMEO, opt, sizeof(c_int))
    if rc != 0:
        err = _ws2.WSAGetLastError()
        raise OSError(err, "setsockopt(SO_SNDTIMEO) failed")


def send_all(handle, payload):
    """Send *payload* (bytes) fully; raises TimeoutError if the peer stalls.

    Loops the Winsock ``send()`` call until the whole buffer is pushed; a
    socket-level timeout surfaces as ``TimeoutError`` so the caller can drop
    the client without stalling the broadcaster.
    """
    _check()
    view = bytes(payload)
    total = 0
    while total < len(view):
        chunk = view[total:]
        sent = _ws2.send(SOCKET(handle), chunk, len(chunk), 0)
        if sent == SOCKET_ERROR:
            err = _ws2.WSAGetLastError()
            if err == WSAEWOULDBLOCK:
                raise TimeoutError("peer did not drain in time (SO_SNDTIMEO)")
            raise OSError(err, "send() failed on AF_UNIX peer")
        if sent == 0:
            raise ConnectionResetError("peer closed during send")
        total += sent
    return total


def recv(handle, bufsize=4096):
    """Blocking read; returns b'' at peer EOF, None on would-block, bytes otherwise."""
    _check()
    buf = create_string_buffer(bufsize)
    got = _ws2.recv(SOCKET(handle), buf, bufsize, 0)
    if got == SOCKET_ERROR:
        err = _ws2.WSAGetLastError()
        if err == WSAEWOULDBLOCK:
            return None
        raise OSError(err, "recv() failed on AF_UNIX peer")
    if got == 0:
        return b""
    return buf.raw[:got]


def close(handle):
    """Close a raw SOCKET handle; safe to call with INVALID_SOCKET/0/None (no-op)."""
    if not handle or handle == INVALID_SOCKET:
        return
    _check()
    _ws2.closesocket(SOCKET(handle))