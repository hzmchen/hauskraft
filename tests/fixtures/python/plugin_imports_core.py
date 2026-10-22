"""Probe: a plugin importing core internals. Linted as if it lived in plugins/official/tasks."""
from hauskraft_core.db import models  # must be flagged (banned API for plugins)

__all__ = ["models"]
