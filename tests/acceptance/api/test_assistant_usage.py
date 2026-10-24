# SPDX-License-Identifier: MIT
"""M2S-E08 usage records and the usage overview for owners. Against the demo stack with the fake model."""

from __future__ import annotations

import pytest

from _support.live import Api, assert_problem, configure_fake, new_chat, say

pytestmark = pytest.mark.live
story = pytest.mark.story


def usage(api: Api, **params) -> dict:
    r = api.get("/assistant/usage", params=params)
    assert r.status_code == 200, f"RED (M2S-E08-02): {r.status_code} {r.text[:200]}"
    return r.json()


def by_key(body: dict) -> dict:
    return {g["key"]: g for g in body["groups"]}


# ---------------------------------------------------------------- M2S-E08-01
@story("M2S-E08-01")
def test_every_model_request_is_counted(assistant: Api) -> None:
    before = usage(assistant, group_by="kind")["totals"]
    say(assistant, new_chat(assistant), "Hello!")
    after = usage(assistant, group_by="kind")
    assert after["totals"]["requests"] == before["requests"] + 1
    assert after["totals"]["input_tokens"] > before["input_tokens"]
    assert after["totals"]["output_tokens"] > before["output_tokens"]
    assert "chat" in by_key(after)


@story("M2S-E08-01")
def test_connection_tests_count_as_test(assistant: Api) -> None:
    before = by_key(usage(assistant, group_by="kind")).get("test", {}).get("requests", 0)
    assert assistant.post("/assistant/settings/test", timeout=30).status_code == 200
    assert by_key(usage(assistant, group_by="kind"))["test"]["requests"] > before


@story("M2S-E08-01")
def test_missing_usage_is_counted_as_unknown(assistant: Api) -> None:
    before = usage(assistant)["totals"]["unknown_requests"]
    configure_fake(assistant, model="fake-no-usage")
    try:
        say(assistant, new_chat(assistant), "Hello!")
    finally:
        configure_fake(assistant)
    assert usage(assistant)["totals"]["unknown_requests"] == before + 1


@story("M2S-E08-01")
def test_deleting_a_chat_keeps_its_usage(assistant: Api) -> None:
    cid = new_chat(assistant)
    say(assistant, cid, "Hello!")
    before = usage(assistant)["totals"]
    assert assistant.delete(f"/assistant/conversations/{cid}").status_code == 204
    assert usage(assistant)["totals"] == before


# ---------------------------------------------------------------- M2S-E08-02
@story("M2S-E08-02")
@pytest.mark.parametrize("group_by", ["day", "user", "model", "kind"])
def test_totals_equal_the_groups(assistant: Api, group_by: str) -> None:
    say(assistant, new_chat(assistant), "Hello!")
    body = usage(assistant, group_by=group_by)
    assert body["group_by"] == group_by
    for field in ("requests", "input_tokens", "output_tokens"):
        assert body["totals"][field] == sum(g[field] for g in body["groups"]), field
    if group_by == "user":
        assert assistant.session["user"]["display_name"] in [g["label"] for g in body["groups"]]
    if group_by == "model":
        assert "fake-tools" in by_key(body)


@story("M2S-E08-02")
def test_cost_estimate_follows_the_prices(assistant: Api) -> None:
    assert usage(assistant)["totals"]["cost"] is None or "amount" in usage(assistant)["totals"]["cost"]
    prices = {"input_per_million": 2.0, "output_per_million": 8.0}
    assert assistant.patch("/assistant/settings", json={"prices": prices}).status_code == 200
    try:
        totals = usage(assistant)["totals"]
        expected = round(totals["input_tokens"] * 2.0 / 1e6 + totals["output_tokens"] * 8.0 / 1e6, 2)
        assert totals["cost"] == {"amount": pytest.approx(expected, abs=0.01), "currency": "EUR"}
    finally:
        assistant.patch("/assistant/settings", json={"prices": {"input_per_million": None,
                                                                "output_per_million": None}})
    assert usage(assistant)["totals"]["cost"] is None


@story("M2S-E08-02")
def test_adults_cannot_read_usage(alex: Api) -> None:
    assert_problem(alex.get("/assistant/usage"), 403, "policy_denied")


@story("M2S-E08-02")
def test_invalid_query_is_rejected(assistant: Api) -> None:
    assert_problem(assistant.get("/assistant/usage", params={"group_by": "planet"}), 422)
