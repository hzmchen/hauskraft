# SPDX-License-Identifier: MIT
"""Entry point of the tasks plugin: ``hauskraft_tasks.plugin:plugin`` (manifest ``runtime.entrypoint``)."""

from __future__ import annotations

from hauskraft_sdk import PluginContext, PluginRegistration
from hauskraft_tasks.models import metadata
from hauskraft_tasks.router import build_router
from hauskraft_tasks.seed import seed


class TasksPlugin:
    id = "dev.hauskraft.tasks"

    def register(self, ctx: PluginContext) -> PluginRegistration:
        return PluginRegistration(router=build_router(ctx), metadata=metadata, seed=seed)


plugin = TasksPlugin()
