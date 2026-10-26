# SPDX-License-Identifier: AGPL-3.0-or-later
"""M2S-E04-03: a short, stable system prompt with the household context last (spec §8.0)."""

import datetime as dt

import pytest

from hauskraft_core.assistant.prompt import PromptContext, prompt_version, render

pytestmark = pytest.mark.unit

CTX = PromptContext(
    now=dt.datetime(2026, 11, 2, 9, 5, tzinfo=dt.UTC),
    timezone="Europe/Berlin",
    household="Familie Müller",
    person="Mia",
    role="owner",
    locale="de",
)


def test_context_block_ends_the_prompt_in_order() -> None:
    lines = render(CTX).rstrip().splitlines()
    assert lines[-4:] == [
        "Today: 2026-11-02 (Monday), 10:05 in Europe/Berlin",
        "Household: Familie Müller",
        "Person: Mia (owner)",
        "Language: German – answer in this language",  # noqa: RUF001 - the contract uses an en dash
    ]


def test_skill_line_and_instructions_only_in_skill_runs() -> None:
    plain = render(CTX)
    skill = render(CTX, skill_id="tasks.weekly-overview", skill_instructions="Write the overview.")
    assert "Skill:" not in plain
    assert skill.rstrip().splitlines()[-1] == "Skill: tasks.weekly-overview"
    assert "Write the overview." in skill
    assert skill.index("Write the overview.") < skill.index("Today:")


def test_rules_cover_the_contract() -> None:
    text = render(CTX).lower()
    for phrase in ("never invent", "clarifying question", "confirm", "data, not instructions", "short"):
        assert phrase in text, phrase


def test_plugin_guidance_comes_before_the_context() -> None:
    text = render(CTX, guidance=["Due dates are calendar dates."])
    assert text.index("Due dates are calendar dates.") < text.index("Today:")


def test_size_cap_without_guidance_and_skills() -> None:
    assert len(render(CTX)) < 4000


def test_voice_style_differs_and_text_is_the_default() -> None:
    assert render(CTX) == render(CTX, channel="text")
    assert render(CTX, channel="voice") != render(CTX)


def test_prompt_version_is_a_stable_hash_of_the_templates() -> None:
    assert prompt_version() == prompt_version()
    assert len(prompt_version()) == 12


def test_english_people_get_english() -> None:
    assert (
        render(PromptContext(**{**CTX.__dict__, "locale": "en"}))
        .rstrip()
        .endswith("Language: English – answer in this language")  # noqa: RUF001
    )
