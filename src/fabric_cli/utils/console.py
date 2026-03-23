# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Rich Console instances for Fabric CLI output.

Provides shared Console instances for stdout and stderr. These are the
only Console objects that should be used for terminal output throughout
the CLI. File logging remains handled by fab_logger.py and is not
affected by these instances.
"""

from rich.console import Console
from rich.theme import Theme

# Fabric brand colour (#49C5B1) used for accents.
FAB_THEME = Theme(
    {
        "fab.brand": "#49C5B1",
        "fab.muted": "grey62",
        "fab.success": "green",
        "fab.warning": "yellow",
        "fab.error": "red",
        "fab.info": "blue",
    }
)

# Primary console for normal output (stdout).
console = Console(theme=FAB_THEME, highlight=False)

# Secondary console for diagnostic / status output (stderr).
err_console = Console(theme=FAB_THEME, stderr=True, highlight=False)
