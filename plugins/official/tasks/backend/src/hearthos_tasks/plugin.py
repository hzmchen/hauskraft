# SPDX-License-Identifier: MIT
"""Entry point of the tasks plugin: ``hearthos_tasks.plugin:plugin`` (manifest ``runtime.entrypoint``)."""

from __future__ import annotations

from fastapi import APIRouter

from hearthos_sdk import PluginContext, PluginRegistration
from hearthos_tasks.models import metadata


class TasksPlugin:
    id = "org.hearthos.tasks"

    def register(self, ctx: PluginContext) -> PluginRegistration:
        router = APIRouter()
        return PluginRegistration(router=router, metadata=metadata)


plugin = TasksPlugin()
