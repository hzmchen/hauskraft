# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E13-03: theme validation against the spec fixtures, plus cases built at test time."""

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

from hearthos_core.themes.validate import validate_theme

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[4]
FIXTURES = REPO / "tests" / "fixtures" / "themes"
EXPECTED: dict[str, Any] = json.loads((FIXTURES / "expected.json").read_text())["themes"]
ERROR_CODES = {
    "manifest.invalid",
    "schema.invalid",
    "token.missing",
    "token.invalid_value",
    "token.alias_cycle",
    "contrast.text",
    "contrast.non_text",
    "distinct.destructive_primary",
    "asset.path",
    "asset.type",
    "asset.size",
    "asset.limit",
    "svg.unsafe",
}
WARNING_CODES = {"icons.partial", "preview.missing", "licence.missing"}


def _codes(issues: list[Any]) -> set[str]:
    return {i.code for i in issues}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_fixture_outcomes(name: str) -> None:
    exp = EXPECTED[name]
    report = validate_theme(FIXTURES / name)
    assert report.theme_id == exp["id"]
    assert report.valid is exp["valid"], [(i.code, i.message) for i in report.errors]
    if exp["valid"]:
        assert report.errors == []
        assert _codes(report.warnings) == set(exp["warnings"])
    else:
        assert set(exp["errors"]) <= _codes(report.errors)
    assert _codes(report.errors) <= ERROR_CODES
    assert _codes(report.warnings) <= WARNING_CODES
    for issue in [*report.errors, *report.warnings]:
        assert issue.message.strip()
        assert issue.path


def test_contrast_issue_points_into_the_token_file() -> None:
    report = validate_theme(FIXTURES / "invalid-low-contrast")
    paths = [i.path for i in report.errors if i.code == "contrast.text"]
    assert "tokens.light.json#/color/muted-foreground" in paths, paths


def test_css_injection_is_an_invalid_value() -> None:
    report = validate_theme(FIXTURES / "invalid-css-injection")
    assert any(i.code == "token.invalid_value" and "primary" in i.path for i in report.errors)
    assert report.css is None, "invalid themes are never compiled"


def _copy(tmp_path: Path, name: str = "valid-minimal") -> Path:
    dst = tmp_path / name
    shutil.copytree(FIXTURES / name, dst)
    return dst


def _edit_tokens(folder: Path, mode: str, path: list[str], value: Any) -> None:
    file = folder / f"tokens.{mode}.json"
    doc = json.loads(file.read_text())
    node = doc
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    file.write_text(json.dumps(doc))


def _edit_theme(folder: Path, **changes: Any) -> None:
    doc = json.loads((folder / "theme.json").read_text())
    doc.update(changes)
    (folder / "theme.json").write_text(json.dumps(doc))


def test_alias_to_a_missing_token(tmp_path: Path) -> None:
    folder = _copy(tmp_path)
    _edit_tokens(folder, "dark", ["color", "ring", "$value"], "{color.nope}")
    assert "token.alias_cycle" in _codes(validate_theme(folder).errors)


def test_alpha_is_composited_before_contrast(tmp_path: Path) -> None:
    folder = _copy(tmp_path)
    # Nearly transparent text over white reads as white: must fail although the base colour is dark.
    _edit_tokens(folder, "light", ["color", "foreground", "$value"], "#11182710")
    report = validate_theme(folder)
    assert any(i.code == "contrast.text" and i.path.endswith("/color/foreground") for i in report.errors)


@pytest.mark.parametrize(
    "value",
    [
        "oklch(45% 0.2 264)",
        "hsl(220 80% 40%)",
        "rgb(29 78 216)",
        {"colorSpace": "display-p3", "components": [0.15, 0.3, 0.8]},
    ],
)
def test_modern_colour_syntaxes_are_accepted(tmp_path: Path, value: Any) -> None:
    folder = _copy(tmp_path)
    _edit_tokens(folder, "light", ["color", "primary", "$value"], value)
    report = validate_theme(folder)
    assert "token.invalid_value" not in _codes(report.errors), report.errors


@pytest.mark.parametrize(
    ("group", "token", "value"),
    [
        ("font", "sans", ['Evil"; } body {', "sans-serif"]),
        ("radius", "md", {"value": "4px; color: red", "unit": "px"}),
        ("radius", "md", "4vw"),
        ("duration", "fast", {"value": 120, "unit": "years"}),
        ("easing", "standard", [2, 0, 0, 1]),
        ("font-weight", "bold", 1200),
    ],
)
def test_non_colour_values_are_type_checked(tmp_path: Path, group: str, token: str, value: Any) -> None:
    folder = _copy(tmp_path)
    _edit_tokens(folder, "light", [group, token, "$value"], value)
    assert "token.invalid_value" in _codes(validate_theme(folder).errors)


def test_symlink_leaving_the_theme(tmp_path: Path) -> None:
    folder = _copy(tmp_path)
    (folder / "assets" / "images").mkdir()
    outside = tmp_path / "outside.webp"
    outside.write_bytes(b"RIFF\0\0\0\0WEBPVP8 ")
    (folder / "assets" / "images" / "bg.webp").symlink_to(outside)
    _edit_theme(
        folder, background={"light": {"image": "assets/images/bg.webp"}, "dark": {"color": "{color.background}"}}
    )
    assert "asset.path" in _codes(validate_theme(folder).errors)


def test_oversized_asset(tmp_path: Path) -> None:
    folder = _copy(tmp_path)
    (folder / "assets" / "images").mkdir()
    (folder / "assets" / "images" / "big.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * (2 * 1024 * 1024 + 1))
    _edit_theme(
        folder, background={"light": {"image": "assets/images/big.png"}, "dark": {"color": "{color.background}"}}
    )
    assert "asset.size" in _codes(validate_theme(folder).errors)


def test_too_many_fonts(tmp_path: Path) -> None:
    folder = _copy(tmp_path)
    src = folder / "assets" / "fonts" / "FixtureSans.woff2"
    fonts = []
    for i in range(9):
        shutil.copy(src, folder / "assets" / "fonts" / f"F{i}.woff2")
        fonts.append({"family": f"Fixture {i}", "src": f"assets/fonts/F{i}.woff2", "weight": "400"})
    _edit_theme(folder, fonts=fonts)
    assert "asset.limit" in _codes(validate_theme(folder).errors)


def test_missing_asset_file(tmp_path: Path) -> None:
    folder = _copy(tmp_path)
    _edit_theme(
        folder, background={"light": {"image": "assets/images/missing.png"}, "dark": {"color": "{color.background}"}}
    )
    assert "asset.path" in _codes(validate_theme(folder).errors)


def test_valid_theme_compiles_to_safe_css(tmp_path: Path) -> None:
    report = validate_theme(FIXTURES / "valid-minimal")
    css = report.css
    assert css is not None
    assert css.startswith(f"/* org.example.theme.valid-minimal 0.1.0 hash={report.hash} */")
    assert re.fullmatch(r"[0-9a-f]{64}", report.hash)
    assert "@font-face" in css
    assert '"Fixture Sans"' in css
    assert (
        f"/api/v1/theme/assets/org.example.theme.valid-minimal/assets/fonts/FixtureSans.woff2?h={report.hash[:16]}"
        in css
    )
    root, dark = css.split(":root.dark", 1)
    assert "color-scheme: light;" in root
    assert "--hearth-color-background: rgb(255 255 255);" in root
    assert "--background: var(--hearth-color-background);" in root
    assert "--hearth-density: 1;" in root
    assert "--hearth-grid-row:" in root
    assert "color-scheme: dark;" in dark
    for forbidden in ("<", "}body", "url(http", "javascript:", "@import", "expression("):
        assert forbidden not in css.replace(" ", "")


def test_compilation_is_deterministic(tmp_path: Path) -> None:
    a = validate_theme(FIXTURES / "valid-minimal")
    b = validate_theme(_copy(tmp_path))
    assert a.css == b.css
    assert a.hash == b.hash


def test_hash_changes_with_content(tmp_path: Path) -> None:
    folder = _copy(tmp_path)
    before = validate_theme(folder).hash
    _edit_tokens(folder, "light", ["color", "primary", "$value"], "#1e40af")
    assert validate_theme(folder).hash != before


def test_golden_css(tmp_path: Path) -> None:
    golden = Path(__file__).parent / "golden" / "valid-minimal.css"
    assert validate_theme(FIXTURES / "valid-minimal").css == golden.read_text()


@pytest.mark.parametrize("name", ["default", "paper", "hackspace"])
def test_golden_css_builtin(name: str) -> None:
    """M0S-E13-06: built-in themes compile to their reviewed stylesheet (regenerate on purpose, never blindly)."""
    report = validate_theme(REPO / "themes" / "builtin" / name)
    assert report.valid, report.errors
    assert not report.warnings, report.warnings
    golden = Path(__file__).parent / "golden" / f"builtin-{name}.css"
    assert report.css == golden.read_text()
