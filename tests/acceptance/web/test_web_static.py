# SPDX-License-Identifier: MIT
"""Static checks for the web shell: scaffold, plugin registry, i18n parity, no raw styles."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from _support import REPO
from _support.files import jsonc, text_files
from _support.red import require_file, require_text

story = pytest.mark.story

UI_COMPONENTS = ["button", "input", "checkbox", "card", "dialog", "dropdown-menu", "popover", "calendar",
                 "sonner", "tabs", "sheet"]


# ---------------------------------------------------------------- M0S-E08-01
@story("M0S-E08-01")
@pytest.mark.parametrize("component", UI_COMPONENTS)
def test_ui_package_has_component(component: str) -> None:
    require_file(f"packages/ui/src/components/{component}.tsx", "M0S-E08-01")


@story("M0S-E08-01")
def test_ui_package_identity() -> None:
    pkg = jsonc("packages/ui/package.json", "M0S-E08-01")
    assert pkg.get("name") == "@hearthos/ui" and pkg.get("license") == "MIT"
    require_file("packages/ui/components.json", "M0S-E08-01")


@story("M0S-E08-01")
def test_router_plugin_runs_before_react_plugin() -> None:
    text = require_text("apps/web/vite.config.ts", "M0S-E08-01")
    router, react = text.find("tanstackRouter("), text.find("react(")
    if router == -1:
        router = text.find("TanStackRouterVite(")
    assert router != -1 and react != -1 and router < react, "TanStack router plugin must come before react()"


# ---------------------------------------------------------------- M0S-E06-06
@story("M0S-E06-06")
def test_generated_registry_lists_tasks_plugin_only() -> None:
    text = require_text("apps/web/src/plugins/registry.gen.ts", "M0S-E06-06")
    assert "org.hearthos.tasks" in text and "@hearthos/plugin-tasks" in text
    assert "org.hearthos.theme" not in text, "theme plugins have no web code and must not be in the registry"


# ---------------------------------------------------------------- M0S-E08-04 / M0S-E09-03 i18n
def _flatten(d: dict, prefix: str = "") -> dict[str, str]:
    out = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        out.update(_flatten(v, key) if isinstance(v, dict) else {key: v})
    return out


def _namespaces() -> list[tuple[Path, Path]]:
    pairs = []
    roots = [REPO / "apps" / "web" / "src" / "i18n" / "locales",
             *sorted((REPO / "plugins" / "official").glob("*/web/src/locales"))]
    for root in roots:
        for en in sorted((root / "en").glob("*.json")) if (root / "en").exists() else []:
            pairs.append((en, root / "de" / en.name))
    return pairs


@story("M0S-E08-04")
def test_shell_namespace_exists_in_both_languages() -> None:
    require_file("apps/web/src/i18n/locales/en/shell.json", "M0S-E08-04")
    require_file("apps/web/src/i18n/locales/de/shell.json", "M0S-E08-04")


@story("M0S-E09-03")
def test_tasks_namespace_exists_in_both_languages() -> None:
    require_file("plugins/official/tasks/web/src/locales/en/tasks.json", "M0S-E09-03")
    de = json.loads(require_text("plugins/official/tasks/web/src/locales/de/tasks.json", "M0S-E09-03"))
    assert "Aufgaben" in json.dumps(de, ensure_ascii=False), "German tasks namespace should title the list 'Aufgaben'"


@story("M0S-E08-04", "M0S-E09-03")
def test_every_namespace_has_identical_keys_in_en_and_de() -> None:
    pairs = _namespaces()
    if not pairs:
        pytest.fail("RED (M0S-E08-04): no locale files yet", pytrace=False)
    for en, de in pairs:
        assert de.exists(), f"{de.relative_to(REPO)} missing"
        en_keys = _flatten(json.loads(en.read_text()))
        de_keys = _flatten(json.loads(de.read_text()))
        assert set(en_keys) == set(de_keys), {
            "file": en.name, "only_en": sorted(set(en_keys) - set(de_keys)), "only_de": sorted(set(de_keys) - set(en_keys))}
        empty = [k for k, v in {**en_keys, **de_keys}.items() if not (isinstance(v, str) and v.strip())]
        assert not empty, f"{en.name}: empty strings for {empty}"


# ---------------------------------------------------------------- M0S-E13-08 backstop
PALETTE = re.compile(
    r"\b(?:bg|text|border|ring|fill|stroke|from|via|to|outline|decoration|shadow|accent|caret|divide|placeholder)-"
    r"(?:slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|"
    r"purple|fuchsia|pink|rose)-(?:50|[1-9]00|950)\b")
ARBITRARY = re.compile(r"\b[a-z][a-z-]*-\[[^\]\s]+\]")
COLOUR_FN = re.compile(r"\b(?:rgba?|hsla?|oklch|oklab|hwb|lab|lch)\(")
HEX = re.compile(r"(?<![\w&/])#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b(?![\w-])")
ALLOW = re.compile(r"hearthos-allow-raw-style")


def _ui_sources() -> list[Path]:
    roots = [REPO / "apps" / "web" / "src", REPO / "packages" / "ui" / "src",
             *sorted((REPO / "plugins" / "official").glob("*/web/src"))]
    files = []
    for root in roots:
        if root.exists():
            files += [p for p in text_files(root, (".ts", ".tsx", ".css"))
                      if not p.name.endswith(".gen.ts") and p.name != "fallback.css"]
    return files


@story("M0S-E13-08")
def test_ui_code_has_no_raw_styles() -> None:
    files = _ui_sources()
    if not files:
        pytest.fail("RED (M0S-E13-08): no UI sources yet", pytrace=False)
    offences = []
    for path in files:
        for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if ALLOW.search(line):
                continue
            for name, rx in (("palette class", PALETTE), ("arbitrary value", ARBITRARY),
                             ("colour function", COLOUR_FN), ("hex colour", HEX)):
                if rx.search(line):
                    offences.append(f"{path.relative_to(REPO)}:{no}: {name}: {line.strip()[:100]}")
    assert not offences, "raw styles found (use @hearthos/ui and semantic tokens):\n" + "\n".join(offences[:50])


@story("M0S-E13-08")
@pytest.mark.parametrize("probe", ["raw-hex-colour", "raw-palette-class", "raw-arbitrary-value", "raw-inline-spacing"])
def test_lint_rule_flags_raw_style_probe(probe: str) -> None:
    from _support import FIXTURES
    from _support.tools import eslint_on_stdin

    src = (FIXTURES / "lint" / f"{probe}.tsx").read_text()
    msgs = eslint_on_stdin(src, "plugins/official/tasks/web/src/_probe.tsx", "M0S-E13-08")
    assert any(m.get("ruleId") == "hearthos/no-raw-styles" for m in msgs), msgs


@story("M0S-E13-08")
def test_lint_rule_accepts_semantic_probe() -> None:
    from _support import FIXTURES
    from _support.tools import eslint_on_stdin

    src = (FIXTURES / "lint" / "semantic-ok.tsx").read_text()
    msgs = eslint_on_stdin(src, "plugins/official/tasks/web/src/_probe.tsx", "M0S-E13-08")
    assert not [m for m in msgs if m.get("ruleId") == "hearthos/no-raw-styles"], msgs
