# SPDX-License-Identifier: AGPL-3.0-or-later
"""Theme package validation (M0S-E13-03). Thresholds and limits: ADR-0013 / tokens-v1.json.

``validate_theme(folder)`` returns a ``ThemeReport``; valid themes are compiled (``report.css``). Every rule
is a hard error except the three warnings (missing optional icons, missing preview, missing licence texts).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from hearthos_core import schemas
from hearthos_core.themes import dtcg
from hearthos_core.themes.compile import compile_css
from hearthos_core.themes.model import ThemeReport
from hearthos_core.themes.svg_sanitize import problems as svg_problems
from hearthos_core.themes.svg_sanitize import symbol_ids

MANIFEST_SCHEMA = "manifest/hearthos.plugin.schema.json"
THEME_SCHEMA = "theme/hearthos.theme.schema.json"
MODES = ("light", "dark")
MAGIC: dict[str, Callable[[bytes], bool]] = {
    ".woff2": lambda b: b[:4] == b"wOF2",
    ".png": lambda b: b[:8] == b"\x89PNG\r\n\x1a\n",
    ".webp": lambda b: b[:4] == b"RIFF" and b[8:12] == b"WEBP",
    ".jpg": lambda b: b[:3] == b"\xff\xd8\xff",
    ".jpeg": lambda b: b[:3] == b"\xff\xd8\xff",
    ".avif": lambda b: b[4:8] == b"ftyp" and b[8:12] in (b"avif", b"avis"),
    ".svg": lambda b: b"<svg" in b[:4096],
}
PARSERS: dict[str, Callable[[Any], str]] = {
    "dimension": dtcg.parse_dimension,
    "duration": dtcg.parse_duration,
    "fontFamily": dtcg.parse_font_family,
    "fontWeight": dtcg.parse_font_weight,
    "number": dtcg.parse_number,
    "cubicBezier": dtcg.parse_cubic_bezier,
}


def contract() -> dict[str, Any]:
    return schemas.load("theme/tokens-v1.json")


def core_icon_names() -> list[str]:
    return list(schemas.load("theme/icon-names-v1.json")["icons"])


def _pointer(mode: str, token: str) -> str:
    return f"tokens.{mode}.json#/" + token.replace(".", "/")


def theme_hash(folder: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in folder.rglob("*") if p.is_file() and not p.is_symlink()):
        digest.update(path.relative_to(folder).as_posix().encode() + b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def validate_theme(folder: Path, theme_key: str | None = None) -> ThemeReport:
    folder = Path(folder)
    report = ThemeReport(theme_id=folder.name, folder=folder)
    if not _check_manifest(report, theme_key):
        return report
    if not _check_theme_json(report, theme_key):
        return report
    _check_tokens(report)
    _check_assets(report)
    _check_warnings(report)
    report.hash = theme_hash(folder)
    if report.valid:
        report.css = compile_css(report)
    return report


def _load_json(report: ThemeReport, rel: str, code: str) -> Any:
    path = report.folder / rel
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        report.error(code, f"{rel} is missing", rel)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        report.error(code, f"{rel} is not valid JSON: {exc}", rel)
    return None


def _check_manifest(report: ThemeReport, theme_key: str | None) -> bool:
    manifest = _load_json(report, "hearthos.plugin.json", "manifest.invalid")
    if not isinstance(manifest, dict):
        return False
    report.manifest = manifest
    plugin_id = str(manifest.get("id", report.folder.name))
    themes = (manifest.get("contributes") or {}).get("themes") or []
    key = theme_key or (themes[0]["id"] if themes and isinstance(themes[0], dict) and "id" in themes[0] else None)
    report.theme_id = plugin_id if len(themes) <= 1 else f"{plugin_id}:{key}"
    for problem in schemas.errors(MANIFEST_SCHEMA, manifest):
        report.error("manifest.invalid", problem, "hearthos.plugin.json")
    if manifest.get("type") != ["theme"]:
        report.error("manifest.invalid", 'a theme package must have type ["theme"]', "hearthos.plugin.json#/type")
    return report.valid


def _check_theme_json(report: ThemeReport, theme_key: str | None) -> bool:
    themes = report.manifest["contributes"]["themes"]
    entry = next((t for t in themes if theme_key in (None, t["id"])), themes[0])
    theme = _load_json(report, entry["file"], "schema.invalid")
    if not isinstance(theme, dict):
        return False
    report.theme = theme
    for err in schemas.validator(THEME_SCHEMA).iter_errors(theme):
        where = "/".join(map(str, err.absolute_path))
        if err.validator == "maxItems" and where == "fonts":
            # The schema caps fonts too; report it as the limit it is (tokens-v1 limits.max_fonts).
            report.error(
                "asset.limit", f"{len(theme['fonts'])} fonts (at most {err.validator_value})", f"{entry['file']}#/fonts"
            )
        else:
            report.error("schema.invalid", f"{where or '<root>'}: {err.message}", f"{entry['file']}#/{where}")
    return report.valid


def _check_tokens(report: ThemeReport) -> None:
    rules = contract()
    required: dict[str, str] = {name: spec["type"] for name, spec in rules["tokens"].items()}
    colours: dict[str, dict[str, dtcg.Rgba]] = {}
    for mode in MODES:
        rel = report.theme["tokens"][mode]
        tree = _load_json(report, rel, "token.invalid_value")
        if not isinstance(tree, dict):
            continue
        tokens = dtcg.flatten(tree)
        values: dict[str, str] = {}
        parsed: dict[str, dtcg.Rgba] = {}

        def colour_of(raw: Any, _tokens: dict[str, dict[str, Any]] = tokens) -> dtcg.Rgba:
            if isinstance(raw, str) and (m := dtcg.ALIAS.match(raw)):
                raw = dtcg.resolve(_tokens, m.group(1))
            return dtcg.parse_colour(raw)

        for name, ttype in required.items():
            pointer = _pointer(mode, name)
            if name not in tokens:
                report.error("token.missing", f"{name} is required in {mode} mode", pointer)
                continue
            declared = tokens[name]["$type"]
            if declared is not None and declared != ttype:
                report.error("token.invalid_value", f"{name} must have $type {ttype}, not {declared}", pointer)
                continue
            try:
                raw = dtcg.resolve(tokens, name)
                if ttype == "color":
                    parsed[name] = dtcg.parse_colour(raw)
                    values[name] = parsed[name].css()
                elif ttype == "shadow":
                    values[name] = dtcg.parse_shadow(raw, colour_of)
                else:
                    values[name] = PARSERS[ttype](raw)
            except dtcg.AliasError as exc:
                report.error("token.alias_cycle", str(exc), pointer)
            except dtcg.TokenValueError as exc:
                report.error("token.invalid_value", f"{name}: {exc}", pointer)
        report.css_values[mode] = values
        colours[mode] = parsed
        swatches = (report.theme.get("preview") or {}).get("swatches") or []
        report.preview[mode] = [_swatch(s, tokens) for s in swatches]
    for mode, parsed in colours.items():
        _check_contrast(report, mode, parsed, rules)


def _swatch(value: str, tokens: dict[str, dict[str, Any]]) -> str:
    try:
        raw: Any = value
        if (m := dtcg.ALIAS.match(value)) is not None:
            raw = dtcg.resolve(tokens, m.group(1))
        return dtcg.parse_colour(raw).css()
    except (dtcg.AliasError, dtcg.TokenValueError):
        return "rgb(0 0 0)"


def _check_contrast(report: ThemeReport, mode: str, colours: dict[str, dtcg.Rgba], rules: dict[str, Any]) -> None:
    for kind, code in (("text", "contrast.text"), ("non_text", "contrast.non_text")):
        minimum = float(rules["contrast"][kind]["min"])
        for fg, bg in rules["contrast"][kind]["pairs"]:
            if fg in colours and bg in colours:
                ratio = dtcg.contrast(colours[fg], colours[bg])
                if ratio < minimum:
                    report.error(
                        code, f"{fg} on {bg} is {ratio:.2f}:1 in {mode} mode (needs {minimum}:1)", _pointer(mode, fg)
                    )
    distance_min = float(rules["distinct"]["destructive_primary_min_oklab"])
    if "color.destructive" in colours and "color.primary" in colours:
        distance = dtcg.oklab_distance(colours["color.destructive"], colours["color.primary"])
        if distance < distance_min:
            report.error(
                "distinct.destructive_primary",
                f"destructive and primary are too similar in {mode} mode (OKLab distance {distance:.3f}, "
                f"needs {distance_min})",
                _pointer(mode, "color.destructive"),
            )


def referenced_assets(theme: dict[str, Any]) -> list[tuple[str, str]]:
    """``(relative path, where in theme.json)`` for every asset the theme points to."""
    refs = [(f["src"], f"theme.json#/fonts/{i}/src") for i, f in enumerate(theme.get("fonts") or [])]
    if (theme.get("icons") or {}).get("pack"):
        refs.append((theme["icons"]["pack"], "theme.json#/icons/pack"))
    for mode in MODES:
        image = ((theme.get("background") or {}).get(mode) or {}).get("image")
        if image:
            refs.append((image, f"theme.json#/background/{mode}/image"))
    return refs


def _check_assets(report: ThemeReport) -> None:
    limits = contract()["limits"]
    root = report.folder.resolve()
    for rel, where in referenced_assets(report.theme):
        path = report.folder / rel
        try:
            resolved = path.resolve(strict=True)
        except (FileNotFoundError, RuntimeError):
            report.error("asset.path", f"{rel} does not exist", where)
            continue
        if not resolved.is_relative_to(root) or path.is_symlink():
            report.error("asset.path", f"{rel} leaves the theme folder", where)
            continue
        suffix = path.suffix.lower()
        head = resolved.read_bytes()[:4096]
        if suffix not in MAGIC or not MAGIC[suffix](head):
            report.error("asset.type", f"{rel} is not an allowed {suffix or 'file'} (type or magic bytes)", where)
            continue
        if resolved.stat().st_size > limits["asset_max_bytes"]:
            report.error("asset.size", f"{rel} is larger than {limits['asset_max_bytes'] // (1024 * 1024)} MB", where)
        if suffix == ".svg":
            for problem in svg_problems(resolved):
                report.error("svg.unsafe", f"{rel}: {problem}", where)
    files = (
        [p for p in (report.folder / "assets").rglob("*") if p.is_file()] if (report.folder / "assets").is_dir() else []
    )
    total = sum(p.lstat().st_size for p in files)
    if total > limits["assets_total_max_bytes"]:
        report.error(
            "asset.limit", f"assets add up to more than {limits['assets_total_max_bytes'] // 1048576} MB", "assets/"
        )
    fonts = max(len(report.theme.get("fonts") or []), sum(1 for p in files if p.suffix.lower() == ".woff2"))
    if fonts > limits["max_fonts"]:
        report.error("asset.limit", f"{fonts} font files (at most {limits['max_fonts']})", "theme.json#/fonts")
    pack = (report.theme.get("icons") or {}).get("pack")
    if pack and not any(i.path == "theme.json#/icons/pack" for i in report.errors):
        symbols = symbol_ids(report.folder / pack)
        report.icon_names = sorted(set(symbols))
        if len(symbols) > limits["max_sprite_symbols"]:
            report.error(
                "asset.limit",
                f"sprite has {len(symbols)} symbols (at most {limits['max_sprite_symbols']})",
                "theme.json#/icons/pack",
            )


def _check_warnings(report: ThemeReport) -> None:
    pack = (report.theme.get("icons") or {}).get("pack")
    if pack and report.icon_names:
        missing = [n for n in core_icon_names() if n not in report.icon_names]
        if missing:
            report.warn(
                "icons.partial",
                f"the sprite lacks {len(missing)} core icons, which fall back to the "
                f"default pack: {', '.join(missing)}",
                "theme.json#/icons/pack",
            )
    if not (report.theme.get("preview") or {}).get("swatches"):
        report.warn(
            "preview.missing", "no preview swatches; Settings → Appearance shows a plain card", "theme.json#/preview"
        )
    bundles_assets = bool(report.theme.get("fonts")) or bool(pack)
    licences = report.folder / "LICENSES"
    if bundles_assets and not (licences.is_dir() and any(licences.iterdir())):
        report.warn("licence.missing", "bundled fonts or icons need their licence texts in LICENSES/", "LICENSES/")
