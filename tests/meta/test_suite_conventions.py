# SPDX-License-Identifier: MIT
"""The acceptance suite follows its own rules, and its contract mirrors agree with the spec."""

from __future__ import annotations

import json
import re

import pytest

from _support import FIXTURES, REPO, SPEC, TESTS
from _support.theme_contract import COLOUR_TOKENS, CORE_ICON_NAMES, LAYOUT_OPTIONS

pytestmark = pytest.mark.meta

PY_TESTS = sorted(p for p in TESTS.rglob("test_*.py") if "fixtures" not in p.parts)
E2E_SPECS = sorted((TESTS / "e2e").glob("*.spec.ts"))


@pytest.mark.parametrize("path", [*PY_TESTS, *E2E_SPECS, *sorted((TESTS / "_support").glob("*.py")),
                                  *sorted((TESTS / "e2e" / "support").glob("*.ts"))],
                         ids=lambda p: str(p.relative_to(TESTS)))
def test_files_carry_spdx_header(path) -> None:
    head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:3])
    assert "SPDX-License-Identifier: MIT" in head


@pytest.mark.parametrize("path", sorted((TESTS / "acceptance" / "api").glob("test_*.py")), ids=lambda p: p.name)
def test_api_modules_are_marked_live(path) -> None:
    assert re.search(r"^pytestmark = .*pytest\.mark\.live", path.read_text(), re.M), \
        f"{path.name} must set pytestmark with pytest.mark.live"


@pytest.mark.parametrize("path", E2E_SPECS, ids=lambda p: p.name)
def test_every_e2e_test_is_story_tagged(path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines):
        if re.match(r"\s*test\((?!\.)", line):
            window = " ".join(lines[i:i + 3])
            assert "story(" in window, f"{path.name}:{i + 1}: e2e test without story(...) tags"


def test_theme_fixture_index_matches_folders() -> None:
    expected = json.loads((FIXTURES / "themes" / "expected.json").read_text())["themes"]
    folders = {p.name for p in (FIXTURES / "themes").iterdir() if p.is_dir()}
    assert set(expected) == folders
    for name, e in expected.items():
        manifest = json.loads((FIXTURES / "themes" / name / "hearthos.plugin.json").read_text())
        assert manifest["id"] == e["id"]
        assert name.startswith("valid") or name.startswith("warn") or name.startswith("invalid")
        assert e["valid"] == (not name.startswith("invalid"))


def test_icon_names_match_spec() -> None:
    text = SPEC.read_text(encoding="utf-8")
    section = text.split("#### 10.2.6 Icons", 1)[1].split("####", 1)[0]
    names = re.findall(r"`([a-z]+\.[a-z-]+)`", section.split("(core set v1)", 1)[0])
    assert names == CORE_ICON_NAMES


def test_colour_tokens_match_spec() -> None:
    text = SPEC.read_text(encoding="utf-8")
    table = text.split("#### 10.2.5", 1)[1].split("Compilation:", 1)[0]
    spec_tokens = set(re.findall(r"`(color\.[a-z0-9-]+)`", table))
    expanded = {t for t in spec_tokens if not t.startswith("color.chart")} | {f"color.chart-{i}" for i in range(1, 7)}
    assert expanded == set(COLOUR_TOKENS)


def test_layout_options_match_spec() -> None:
    text = SPEC.read_text(encoding="utf-8")
    table = text.split("#### 10.2.1", 1)[1].split("#### 10.2.2", 1)[0]
    for values in LAYOUT_OPTIONS.values():
        for v in values:
            assert f"`{v}`" in table, f"layout option {v} not in spec §10.2.1"


def test_e2e_names_are_in_ui_contract() -> None:
    contract = (REPO / "docs" / "testing" / "ui-contract.md").read_text(encoding="utf-8")
    names: set[str] = set()
    for path in [*E2E_SPECS, *(TESTS / "e2e" / "support").glob("*.ts")]:
        text = path.read_text(encoding="utf-8")
        names |= set(re.findall(r'name: "([^"$]+)"', text))
        names |= set(re.findall(r'getByLabel\("([^"$]+)"\)', text))
        names |= set(re.findall(r'goNav\(\w+, "([^"]+)"\)', text))
    names = {re.sub(r"'[^']*'", "'<title>'", n) for n in names}
    missing = sorted(n for n in names if n not in contract)
    assert not missing, f"accessible names used by e2e tests but not in docs/testing/ui-contract.md: {missing}"
