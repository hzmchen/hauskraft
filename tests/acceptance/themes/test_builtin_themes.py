# SPDX-License-Identifier: MIT
"""M0S-E13-06 · The three built-in themes, checked independently of the validator under test."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET

import pytest

from _support import REPO
from _support import colour
from _support.cli import run
from _support.theme_contract import (
    CORE_ICON_NAMES, DESTRUCTIVE_PRIMARY_MIN_OKLAB, NON_TEXT_MIN, NON_TEXT_PAIRS, REQUIRED_TOKENS, TEXT_MIN,
    TEXT_PAIRS,
)
from _support.tokens import load, resolve

pytestmark = pytest.mark.story("M0S-E13-06")
BUILTIN = REPO / "themes" / "builtin"

# Spec §10.2.7 / E13 "Built-in themes" table.
TABLE = {
    "default": {"navigation": {"wide": "sidebar", "narrow": "drawer"}, "density": "comfortable",
                "content_width": "full", "widget": {"chrome": "outlined", "header": "inline"},
                "button": "solid", "checkbox": "square"},
    "paper": {"navigation": {"wide": "topbar", "narrow": "drawer"}, "density": "compact",
              "content_width": "full", "widget": {"chrome": "flat", "header": "inline"},
              "button": "outline", "checkbox": "square"},
    "hackspace": {"navigation": {"wide": "topbar", "narrow": "bottom-tabs"}, "density": "compact",
                  "content_width": "contained", "widget": {"chrome": "tinted", "header": "banner"},
                  "button": "solid", "checkbox": "square"},
}
MODES = ("light", "dark")


def folder(name: str):
    path = BUILTIN / name
    if not path.is_dir():
        pytest.fail(f"RED (M0S-E13-06): themes/builtin/{name} missing", pytrace=False)
    return path


def tokens(name: str, mode: str):
    return load(folder(name) / f"tokens.{mode}.json")


@pytest.mark.parametrize("name", TABLE)
def test_package_files(name: str) -> None:
    f = folder(name)
    for rel in ("hearthos.plugin.json", "theme.json", "tokens.light.json", "tokens.dark.json", "LICENSE"):
        assert (f / rel).is_file(), f"{name}: {rel} missing"
    manifest = json.loads((f / "hearthos.plugin.json").read_text())
    assert manifest["id"] == f"org.hearthos.theme.{name}"
    assert manifest["type"] == ["theme"] and manifest["runtime"]["kind"] == "declarative"


@pytest.mark.parametrize("name", TABLE)
def test_matches_design_table(name: str) -> None:
    doc = json.loads((folder(name) / "theme.json").read_text())
    want = TABLE[name]
    assert doc["layout"]["navigation"] == want["navigation"]
    assert doc["layout"]["density"] == want["density"]
    assert doc["layout"]["content_width"] == want["content_width"]
    assert doc["components"]["widget"] == want["widget"]
    assert doc["components"]["button"]["primary"] == want["button"]
    assert doc["components"]["checkbox"]["style"] == want["checkbox"]


@pytest.mark.parametrize("name", TABLE)
def test_validates_strictly(name: str) -> None:
    res = run("themes", "validate", str(folder(name)), "--json", "--strict")
    assert res.code == 0, res.stdout + res.stderr


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name", TABLE)
def test_all_required_tokens_present(name: str, mode: str) -> None:
    missing = sorted(set(REQUIRED_TOKENS) - set(tokens(name, mode)))
    assert not missing, f"{name}/{mode} lacks {missing}"


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name", TABLE)
def test_contrast_and_distinctness_independently(name: str, mode: str) -> None:
    t = tokens(name, mode)
    for fg, bg in TEXT_PAIRS:
        ratio = colour.contrast(resolve(t, fg), resolve(t, bg))
        assert ratio >= TEXT_MIN, f"{name}/{mode}: {fg} on {bg} is {ratio:.2f}:1"
    for fg, bg in NON_TEXT_PAIRS:
        ratio = colour.contrast(resolve(t, fg), resolve(t, bg))
        assert ratio >= NON_TEXT_MIN, f"{name}/{mode}: {fg} on {bg} is {ratio:.2f}:1"
    dist = colour.oklab_distance(resolve(t, "color.destructive"), resolve(t, "color.primary"))
    assert dist >= DESTRUCTIVE_PRIMARY_MIN_OKLAB, f"{name}/{mode}: destructive vs primary {dist:.3f}"


@pytest.mark.parametrize("mode", MODES)
def test_paper_reaches_aaa_for_body_text(mode: str) -> None:
    t = tokens("paper", mode)
    for fg, bg in (("color.foreground", "color.background"), ("color.surface-foreground", "color.surface")):
        ratio = colour.contrast(resolve(t, fg), resolve(t, bg))
        assert ratio >= 7.0, f"paper/{mode}: {fg} on {bg} is {ratio:.2f}:1 (needs 7:1)"


@pytest.mark.parametrize("name", TABLE)
def test_fonts_are_self_hosted_woff2_with_licence(name: str) -> None:
    f = folder(name)
    doc = json.loads((f / "theme.json").read_text())
    for font in doc.get("fonts", []):
        path = f / font["src"]
        assert path.suffix == ".woff2" and path.read_bytes()[:4] == b"wOF2", f"{name}: {font['src']}"
    if doc.get("fonts"):
        assert (f / "LICENSES" / "OFL-1.1.txt").is_file(), f"{name}: bundled fonts need LICENSES/OFL-1.1.txt"


def test_hackspace_sprite_covers_core_icons() -> None:
    f = folder("hackspace")
    doc = json.loads((f / "theme.json").read_text())
    sprite = f / doc["icons"]["pack"]
    ids = {el.get("id") for el in ET.parse(sprite).getroot().iter() if el.tag.endswith("symbol")}
    missing = sorted(set(CORE_ICON_NAMES) - ids)
    assert not missing, f"hackspace sprite lacks {missing}"
    assert any(p.name.lower().startswith("mit") for p in (f / "LICENSES").glob("*")), "icon pack licence missing"


BRANDING = re.compile(r"chaos\s*computer|\bccc\b|chaosknoten|chaos\s*communication", re.I)


def test_no_third_party_branding() -> None:
    hits = []
    for path in folder("hackspace").rglob("*"):
        if path.is_file() and path.suffix in {".json", ".svg", ".md", ".txt"} and "LICENSES" not in path.parts:
            if BRANDING.search(path.read_text(encoding="utf-8", errors="ignore")):
                hits.append(str(path.relative_to(REPO)))
    assert not hits, f"Hackspace must not use a real club's name or marks: {hits}"
