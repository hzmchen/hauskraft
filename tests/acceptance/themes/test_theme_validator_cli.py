# SPDX-License-Identifier: MIT
"""M0S-E13-03 (validator) and M0S-E13-09 (CLI) · `hauskraft themes validate` on fixture themes.

Contract (E13 "Contracts"):
    hauskraft themes validate <path> [--strict] [--json]
    exit 0 = valid (and, with --strict, no warnings), 1 = invalid, 2 = usage error / path not found.
    --json prints {"theme_id", "path", "valid", "errors": [Issue], "warnings": [Issue]}
    Issue = {"code", "message", "path"}; codes come from the fixed list in tests/_support/theme_contract.py.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from _support import FIXTURES, REPO
from _support.cli import run
from _support.theme_contract import ERROR_CODES, WARNING_CODES

pytestmark = pytest.mark.story("M0S-E13-03", "M0S-E13-09")
EXPECTED = json.loads((FIXTURES / "themes" / "expected.json").read_text())["themes"]


def validate(path: Path, *extra: str):
    return run("themes", "validate", str(path), "--json", *extra)


def codes(issues: list[dict]) -> set[str]:
    return {i["code"] for i in issues}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_fixture_outcome(name: str) -> None:
    exp = EXPECTED[name]
    res = validate(FIXTURES / "themes" / name)
    report = res.json()
    assert report["theme_id"] == exp["id"]
    assert report["valid"] is exp["valid"], report
    if exp["valid"]:
        assert res.code == 0, res.stderr
        assert report["errors"] == []
        assert codes(report["warnings"]) == set(exp["warnings"]), report["warnings"]
    else:
        assert res.code == 1
        missing = set(exp["errors"]) - codes(report["errors"])
        assert not missing, f"{name}: expected {missing} in {report['errors']}"


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_issue_shape_and_codes(name: str) -> None:
    report = validate(FIXTURES / "themes" / name).json()
    for issue in report["errors"]:
        assert {"code", "message", "path"} <= set(issue), issue
        assert issue["code"] in ERROR_CODES, f"unknown error code {issue['code']}"
        assert issue["message"].strip()
    for issue in report["warnings"]:
        assert {"code", "message", "path"} <= set(issue), issue
        assert issue["code"] in WARNING_CODES, f"unknown warning code {issue['code']}"


def test_contrast_issue_points_at_token() -> None:
    report = validate(FIXTURES / "themes" / "invalid-low-contrast").json()
    hits = [i for i in report["errors"] if i["code"] == "contrast.text"]
    assert any("tokens.light.json" in i["path"] and "muted-foreground" in i["path"] for i in hits), hits


def test_strict_accepts_clean_theme() -> None:
    assert validate(FIXTURES / "themes" / "valid-minimal", "--strict").code == 0


@pytest.mark.parametrize("name", [n for n, e in EXPECTED.items() if e["valid"] and e["warnings"]])
def test_strict_rejects_warnings(name: str) -> None:
    assert validate(FIXTURES / "themes" / name, "--strict").code == 1


def test_missing_path_is_usage_error() -> None:
    assert run("themes", "validate", str(REPO / "does-not-exist"), "--json").code == 2


# ---- cases built at test time so the repo never contains them ------------------------------
def _copy(tmp_path: Path, name: str = "valid-minimal") -> Path:
    dst = tmp_path / name
    shutil.copytree(FIXTURES / "themes" / name, dst)
    return dst


def _theme_json(folder: Path) -> dict:
    return json.loads((folder / "theme.json").read_text())


def _write_theme_json(folder: Path, doc: dict) -> None:
    (folder / "theme.json").write_text(json.dumps(doc, indent=2))


def test_symlink_leaving_theme_is_rejected(tmp_path: Path) -> None:
    folder = _copy(tmp_path)
    (folder / "assets" / "images").mkdir(parents=True)
    outside = tmp_path / "outside.webp"
    outside.write_bytes(b"RIFF\0\0\0\0WEBPVP8 ")
    (folder / "assets" / "images" / "bg.webp").symlink_to(outside)
    doc = _theme_json(folder)
    doc["background"] = {"light": {"image": "assets/images/bg.webp"}, "dark": {"color": "{color.background}"}}
    _write_theme_json(folder, doc)
    report = validate(folder).json()
    assert not report["valid"] and "asset.path" in codes(report["errors"]), report


def test_oversized_asset_is_rejected(tmp_path: Path) -> None:
    folder = _copy(tmp_path)
    (folder / "assets" / "images").mkdir(parents=True)
    big = folder / "assets" / "images" / "big.png"
    big.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * (2 * 1024 * 1024 + 100))
    doc = _theme_json(folder)
    doc["background"] = {"light": {"image": "assets/images/big.png"}, "dark": {"color": "{color.background}"}}
    _write_theme_json(folder, doc)
    report = validate(folder).json()
    assert not report["valid"] and "asset.size" in codes(report["errors"]), report


def test_too_many_fonts_is_rejected(tmp_path: Path) -> None:
    folder = _copy(tmp_path)
    src = folder / "assets" / "fonts" / "FixtureSans.woff2"
    doc = _theme_json(folder)
    doc["fonts"] = []
    for i in range(9):
        shutil.copy(src, folder / "assets" / "fonts" / f"F{i}.woff2")
        doc["fonts"].append({"family": f"Fixture {i}", "src": f"assets/fonts/F{i}.woff2", "weight": "400",
                             "style": "normal"})
    _write_theme_json(folder, doc)
    report = validate(folder).json()
    assert not report["valid"] and "asset.limit" in codes(report["errors"]), report


@pytest.mark.story("M0S-E13-06")
def test_list_shows_builtin_themes() -> None:
    res = run("themes", "list")
    assert res.code == 0, res.stderr
    for theme_id in ("dev.hauskraft.theme.default", "dev.hauskraft.theme.paper", "dev.hauskraft.theme.hackspace"):
        assert theme_id in res.stdout


def test_template_theme_validates() -> None:
    template = REPO / "themes" / "template"
    if not template.exists():
        pytest.fail("RED (M0S-E13-09): themes/template missing", pytrace=False)
    report = validate(template).json()
    assert report["valid"] and report["theme_id"] == "org.example.theme.mytheme", report


def test_authoring_guide_exists() -> None:
    guide = REPO / "docs" / "themes.md"
    if not guide.exists():
        pytest.fail("RED (M0S-E13-09): docs/themes.md missing", pytrace=False)
    text = guide.read_text().lower()
    for topic in ("contrast", "density", "navigation", "icon", "licence", "data/themes", "validate", "custom css"):
        assert topic in text, f"docs/themes.md should cover {topic!r}"
