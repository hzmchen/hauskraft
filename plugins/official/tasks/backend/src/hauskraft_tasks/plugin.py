# SPDX-License-Identifier: MIT
"""Entry point of the tasks plugin: ``hearthos_tasks.plugin:plugin`` (manifest ``runtime.entrypoint``)."""

from __future__ import annotations

from hearthos_sdk import PluginContext, PluginRegistration
from hearthos_tasks.models import metadata
from hearthos_tasks.router import build_router
from hearthos_tasks.seed import seed


class TasksPlugin:
    id = "org.hearthos.tasks"

    def register(self, ctx: PluginContext) -> PluginRegistration:
        return PluginRegistration(router=build_router(ctx), metadata=metadata, seed=seed)


plugin = TasksPlugin()
