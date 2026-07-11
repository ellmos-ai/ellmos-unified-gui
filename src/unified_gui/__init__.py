# SPDX-License-Identifier: MIT
"""ellmos Unified GUI — importierbare Operator-Konsole.

Standalone:  from unified_gui import create_app; app = create_app()
Eingebettet: from unified_gui import mount; mount(host_app, prefix="/control")
"""

__version__ = "0.3.0"

from .web.app import create_app, mount  # noqa: E402,F401  (Re-Export der API)

__all__ = ["create_app", "mount", "__version__"]
