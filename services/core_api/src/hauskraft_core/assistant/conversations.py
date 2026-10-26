# SPDX-License-Identifier: AGPL-3.0-or-later
"""Conversations (M2S-E04-01): private to their writer, owners included, and kept until deleted.

Chats are personal bookkeeping like sessions: callers check ``assistant.use``, and nothing here emits an event.
Deleting a conversation removes its messages, runs and actions; usage rows stay (M2S-E08-01).
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hauskraft_core.db.models import AssistantAction, AssistantConversation, AssistantMessage, AssistantRun
from hauskraft_sdk.errors import NotFoundError

TITLE_LENGTH = 80


async def create(session: AsyncSession, user_id: uuid.UUID) -> AssistantConversation:
    conversation = AssistantConversation(user_id=user_id)
    session.add(conversation)
    await session.flush()
    await session.refresh(conversation)
    return conversation


async def list_for(session: AsyncSession, user_id: uuid.UUID) -> list[AssistantConversation]:
    query = (
        select(AssistantConversation)
        .where(AssistantConversation.user_id == user_id)
        .order_by(AssistantConversation.updated_at.desc(), AssistantConversation.id.desc())
    )
    return list(await session.scalars(query))


async def get_own(
    session: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID, *, for_update: bool = False
) -> AssistantConversation:
    """The caller's conversation; someone else's answers 404 exactly like a missing one."""
    query = select(AssistantConversation).where(
        AssistantConversation.id == conversation_id, AssistantConversation.user_id == user_id
    )
    found = await session.scalar(query.with_for_update() if for_update else query)
    if found is None:
        raise NotFoundError("No such conversation.")
    return found


async def messages(session: AsyncSession, conversation_id: uuid.UUID) -> list[AssistantMessage]:
    query = (
        select(AssistantMessage)
        .where(AssistantMessage.conversation_id == conversation_id)
        .order_by(AssistantMessage.created_at, AssistantMessage.id)
    )
    return list(await session.scalars(query))


async def actions(session: AsyncSession, conversation_id: uuid.UUID) -> list[AssistantAction]:
    query = (
        select(AssistantAction)
        .join(AssistantRun, AssistantRun.id == AssistantAction.run_id)
        .where(AssistantRun.conversation_id == conversation_id)
        .order_by(AssistantAction.created_at, AssistantAction.id)
    )
    return list(await session.scalars(query))


async def delete_own(session: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID) -> None:
    await get_own(session, user_id, conversation_id)
    await session.execute(delete(AssistantConversation).where(AssistantConversation.id == conversation_id))


async def touch(session: AsyncSession, conversation: AssistantConversation, first_message: str | None = None) -> None:
    """Mark the conversation as just used; the first message becomes its title."""
    if conversation.title is None and first_message:
        text = " ".join(first_message.split())
        conversation.title = text if len(text) <= TITLE_LENGTH else text[: TITLE_LENGTH - 1] + "…"
    conversation.updated_at = func.now()
