# SPDX-License-Identifier: MIT
"""ellmos Unified GUI — importierbare Operator-Konsole.

Standalone:  from unified_gui import create_app; app = create_app()
Eingebettet: from unified_gui import mount; mount(host_app, prefix="/control")
"""

__version__ = "0.9.0"

from .web.app import create_app, mount  # noqa: E402,F401  (Re-Export der API)
from .web.control_shell import create_control_shell_app, mount_control_shell  # noqa: E402

__all__ = ["create_app", "mount", "create_control_shell_app", "mount_control_shell", "__version__"]
