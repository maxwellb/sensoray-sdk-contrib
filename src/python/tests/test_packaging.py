"""Packaging tests: wheel tag, native payload placement, license metadata.

Copyright: (C) 2026 Maxwell Bloch

These assert the things that are only discoverable at build time — an incorrect
wheel tag or a missing License-File is rejected by the index *after* a version
number has been spent, so they are checked here instead.
"""

from __future__ import annotations

import os
import subprocess
import sys
import zipfile

import pytest

PYPROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _build(dist_dir: str) -> list[str]:
    """Build a wheel into ``dist_dir`` and return its path."""
    env = {**os.environ, "S26_WHEEL_PLATFORM": "win_amd64"}
    subprocess.run(
        [sys.executable, "-m", "build", "--no-isolation", "--wheel", "--outdir", dist_dir],
        cwd=PYPROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
    )
    return [os.path.join(dist_dir, n) for n in os.listdir(dist_dir) if n.endswith(".whl")]


@pytest.fixture(scope="module")
def wheel(tmp_path_factory: pytest.TempPathFactory) -> zipfile.ZipFile:
    dist_dir = str(tmp_path_factory.mktemp("dist"))
    wheels = _build(dist_dir)
    assert wheels, "no wheel produced"
    return zipfile.ZipFile(wheels[0])


def test_wheel_is_tagged_for_the_platform_not_any(wheel: zipfile.ZipFile) -> None:
    """A wheel carrying a native library must never be py3-none-any."""
    name = os.path.basename(wheel.filename)
    assert name.endswith("-none-any.whl") is False
    assert "-none-win_amd64.whl" in name


def test_wheel_marks_itself_not_purelib(wheel: zipfile.ZipFile) -> None:
    wheel_meta = next(n for n in wheel.namelist() if n.endswith(".dist-info/WHEEL"))
    contents = wheel.read(wheel_meta).decode()
    assert "Root-Is-Purelib: false" in contents
    assert "Tag: py3-none-win_amd64" in contents


def test_wheel_ships_the_native_payload_at_runtime_path(wheel: zipfile.ZipFile) -> None:
    assert "sensoray/s2600/lib/s2600.dll" in wheel.namelist()


def test_wheel_ships_exactly_one_payload(wheel: zipfile.ZipFile) -> None:
    """Per-target wheels must not leak the other targets' libraries."""
    payloads = [n for n in wheel.namelist() if n.startswith("sensoray/s2600/lib/")]
    assert len(payloads) == 1, payloads


def test_wheel_does_not_ship_the_libs_source_tree(wheel: zipfile.ZipFile) -> None:
    assert not [n for n in wheel.namelist() if n.startswith("_libs/")]


def test_wheel_declares_license_expression(wheel: zipfile.ZipFile) -> None:
    metadata = next(n for n in wheel.namelist() if n.endswith(".dist-info/METADATA"))
    contents = wheel.read(metadata).decode()
    assert "License-Expression: (AGPL-3.0-only OR GPL-3.0-or-later) AND LicenseRef-Sensoray-2600-SDK" in contents


def test_every_declared_license_file_is_present(wheel: zipfile.ZipFile) -> None:
    """PyPI rejects an upload if a License-File entry is missing from the archive."""
    metadata = next(n for n in wheel.namelist() if n.endswith(".dist-info/METADATA"))
    declared = [
        line.split(": ", 1)[1]
        for line in wheel.read(metadata).decode().splitlines()
        if line.startswith("License-File: ")
    ]
    assert declared, "no License-File entries in METADATA"
    prefix = next(
        n for n in wheel.namelist() if ".dist-info/licenses/" in n
    ).split(".dist-info/", 1)[0]
    present = set(wheel.namelist())
    for relative in declared:
        assert f"{prefix}.dist-info/licenses/{relative}" in present, relative


def test_upstream_notices_are_shipped(wheel: zipfile.ZipFile) -> None:
    """Attribution for the Sensoray core must travel with the binary."""
    notices = [n for n in wheel.namelist() if n.endswith("Sensoray-2600-SDK-NOTICE.txt")]
    assert notices, "upstream copyright notices are missing from the wheel"
