"""sensorayd — installable CLI entry point for the Sensoray 2600 telemetry daemon.

Author   : Maxwell Bloch (github.com/maxwellb)
Copyright: (C) 2026 Maxwell Bloch

Exposes ``main`` so the distribution's console script ``sensorayd`` (declared
in pyproject.toml under [project.scripts]) can launch the daemon. The module
also supports ``python -m sensorayd``.
"""

import sys

from sensorayd.__main__ import main

if __name__ == "__main__":
    sys.exit(main())