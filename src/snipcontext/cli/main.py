"""Deprecated — use snipcontext.cli.app instead.

This shim exists for backward compatibility during the migration.
"""

import warnings

warnings.warn(
    "snipcontext.cli.main is deprecated, use snipcontext.cli.app",
    DeprecationWarning,
    stacklevel=2,
)

from snipcontext.cli.app import app  # noqa: E402

if __name__ == "__main__":
    app()
