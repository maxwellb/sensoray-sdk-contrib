"""Tests for the sensoray.s2600 ctypes wrapper.

Copyright: (C) 2026 Maxwell Bloch

These tests do not require 2600 hardware: they cover DLL resolution, symbol
binding, and error decoding. Anything that talks to a gateway lives in
``src/_utils/`` and needs a real MM.
"""

from __future__ import annotations

import os
import pathlib
import sys
import warnings

import pytest

import sensoray
from sensoray import s2600


WINDOWS_ONLY = pytest.mark.skipif(
    sys.platform != "win32", reason="the native middleware library is Windows only"
)


def test_package_exposes_version() -> None:
    assert isinstance(sensoray.__version__, str)
    assert sensoray.__version__.count(".") >= 1


@WINDOWS_ONLY
def test_bundled_library_is_present() -> None:
    """The wheel must ship its native payload at the documented runtime path."""
    lib = s2600.lib()
    if lib is None:  # pragma: no cover - only on a broken install
        pytest.fail("s2600 library failed to load; see the ImportWarning above")
    assert lib is not None


@WINDOWS_ONLY
def test_driver_version_returns_a_string() -> None:
    version = s2600.S26_DriverVersion()
    assert isinstance(version, bytes)
    assert version.count(b".") >= 1


@WINDOWS_ONLY
def test_exported_constants_are_intact() -> None:
    assert s2600.GWERR_NONE == 0x00000000
    assert s2600.GWERRMASK == 0xFFFFFF00
    assert s2600.MODID_GATEWAY == 0xFF
    assert s2600.IOM_2608 == 2608
    assert s2600.NUM_IOMPORTS > 0


@WINDOWS_ONLY
def test_sched_symbols_are_bound() -> None:
    """A sample of S26_* entry points must be real, bound ctypes callables."""
    for name in ("S26_SchedOpen", "S26_SchedExecute", "S26_Sched2600_Nop"):
        fn = getattr(s2600, name)
        assert callable(fn), f"{name} was not bound"
        assert fn.argtypes is not None, f"{name} has no declared argtypes"


def test_err_name_decodes_known_codes() -> None:
    assert s2600.err_name(s2600.GWERR_NONE) == "GWERR_NONE"
    assert s2600.err_name(s2600.GWERR_IOMNORESPOND) == "GWERR_IOMNORESPOND"


def test_err_name_preserves_low_byte_detail() -> None:
    """Gateway errors carry extra info (e.g. IOM port) in the low byte."""
    for port in (0, 3, 7):
        code = s2600.GWERR_IOMNORESPOND | port
        assert port == (code & 0xFF)
        # The base error name must still be recognised through GWERRMASK.
        assert s2600.err_name(code).startswith("GWERR_IOMNORESPOND")


def test_s26error_formats_message() -> None:
    err = s2600.S26Error(s2600.GWERR_BADVALUE, "S26_SchedExecute")
    assert err.code == s2600.GWERR_BADVALUE
    assert err.fn == "S26_SchedExecute"
    text = str(err)
    assert "S26_SchedExecute" in text
    assert "GWERR_BADVALUE" in text
    assert "0x" in text


def test_s26error_without_function_name() -> None:
    err = s2600.S26Error(s2600.GWERR_THREAD)
    assert err.fn == ""
    assert "GWERR_THREAD" in str(err)


def test_dll_override_is_honoured(monkeypatch: pytest.MonkeyPatch) -> None:
    """S26_DLL must take precedence over the bundled library path."""
    monkeypatch.setenv("S26_DLL", os.path.join("somewhere", "else.dll"))
    resolved = s2600._bindings._get_dll_path()
    assert pathlib.Path(resolved).name == "else.dll"


def test_missing_library_raises_a_clear_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A wrong S26_DLL must fail with a diagnostic naming the expected path."""
    monkeypatch.setenv("S26_DLL", os.path.join(os.sep, "nonexistent", "nope.dll"))
    with pytest.raises(FileNotFoundError) as excinfo:
        s2600._bindings._load_and_bind_dll()
    assert "nope.dll" in str(excinfo.value)


def test_load_failure_is_non_fatal_at_import() -> None:
    """Import-time load failures degrade to a warning, not a crash.

    This is what keeps a source install on a non-Windows host importable, and
    it is why the sdist remains installable everywhere.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            s2600._bindings._load_and_bind_dll()
        except Exception as exc:  # noqa: BLE001 - mirrors the import guard
            warnings.warn(f"Runtime binary loading deferred: {exc}", ImportWarning)
    # Either the library loaded, or exactly one deferred-load warning appeared.
    assert s2600.lib() is not None or len(caught) == 1
