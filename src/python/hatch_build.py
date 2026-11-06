"""Hatch build hook: platform-tagged wheels with per-target native payloads.

Copyright: (C) 2026 Maxwell Bloch

The wheel ships exactly one target's native middleware library, placed at a
single stable runtime path inside the package:

    sensoray/s2600/lib/<library>

so that ``sensoray.s2600._bindings`` needs no per-platform knowledge. Targets
are selected by the ``S26_WHEEL_TAG`` environment variable, which also
determines the wheel's platform tag.

Layout of the source tree::

    _libs/<platform-tag>/       native library, one directory per target
    src/sensoray/               pure-Python wrapper (platform independent)
    sensorayd/                  pure-Python daemon + CLI

Adding a target means adding an ``_libs/<tag>/`` directory and a ``PAYLOADS``
entry. Every version ships whatever targets were built for it; earlier targets
remain available at their earlier versions.

This hook only *selects and tags*; it never compiles anything, so building the
sdist remains possible on any platform (``_bindings`` degrades gracefully when
the native library is absent and ``S26_DLL`` can point at one built locally).
"""

from __future__ import annotations

import os

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

#: platform tag -> (source path in _libs/, destination path inside the wheel)
#: Add an entry here (and an _libs/<platform>/ directory) to ship a new target.
PAYLOADS: dict[str, str] = {
    "win_amd64": "_libs/win_amd64/s2600.dll",
}

#: Runtime path the library is placed at, identical for every target, so that
#: ``sensoray.s2600._bindings`` needs no per-platform knowledge.
DESTINATIONS: dict[str, str] = {
    "win_amd64": "sensoray/s2600/lib/s2600.dll",
}

#: Default target when S26_WHEEL_PLATFORM is unset, so a bare `uv build` works.
DEFAULT_PLATFORM = "win_amd64"


class WheelPayloadHook(BuildHookInterface):
    """Tag each wheel for one platform and inject that platform's library."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:  # noqa: D102
        if self.target_name != "wheel":
            # The sdist stays platform neutral and carries every payload.
            return

        platform = os.environ.get("S26_WHEEL_PLATFORM", DEFAULT_PLATFORM).strip()
        try:
            source = PAYLOADS[platform]
            destination = DESTINATIONS[platform]
        except KeyError:
            known = ", ".join(sorted(PAYLOADS))
            msg = (
                f"S26_WHEEL_PLATFORM={platform!r} is not a known target. "
                f"Known targets: {known}. Add an _libs/<platform>/ directory "
                f"and PAYLOADS/DESTINATIONS entries to support it."
            )
            raise ValueError(msg) from None

        if not os.path.isfile(os.path.join(self.root, source)):
            msg = (
                f"Native payload for {platform!r} is missing: expected {source} "
                f"in {self.root}. Build that target before packaging it."
            )
            raise FileNotFoundError(msg)

        # `none` ABI is correct: this is a ctypes-loaded plain C library, not a
        # CPython extension module, so it is interpreter-version independent.
        build_data["tag"] = f"py3-none-{platform}"
        build_data["pure_python"] = False
        # force_include, not artifacts: the destination is inside a package
        # that is selected by `packages`, and the source lives outside it.
        build_data["force_include"][source] = destination
