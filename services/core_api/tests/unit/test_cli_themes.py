# SPDX-License-Identifier: AGPL-3.0-or-later
"""M0S-E13-09: ``hearthos themes validate`` and ``hearthos themes list`` (CliRunner, no database)."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hearthos_core.cli import app
from tests.theme_helpers import FIXTURES

pytestmark = pytest.mark.unit
REPO = Path(__file__).resolve().parents[4]
runner = CliRunner()


def test_valid_theme_exits_0_with_a_summary() -> None:
    result = runner.invoke(app, ["themes", "validate", str(FIXTURES / "valid-minimal")])
    assert result.exit_code == 0, result.output
    assert "org.example.theme.valid-minimal" in result.output
    assert "valid" in result.output


def test_invalid_theme_exits_1_and_names_code_file_and_pointer() -> None:
    result = runner.invoke(app, ["themes", "validate", str(FIXTURES / "invalid-low-contrast")])
    assert result.exit_code == 1
    assert "contrast.text" in result.output
    assert "tokens.light.json#/color/muted-foreground" in result.output


def test_json_shape() -> None:
    folder = FIXTURES / "invalid-missing-token"
    result = runner.invoke(app, ["themes", "validate", str(folder), "--json"])
    assert result.exit_code == 1
    report = json.loads(result.stdout)
    assert set(report) == {"theme_id", "path", "valid", "errors", "warnings"}
    assert report["theme_id"] == "org.example.theme.invalid-missing-token"
    assert report["path"] == str(folder)
    assert report["valid"] is False
    assert report["errors"][0] == {
        "code": "token.missing",
        "message": report["errors"][0]["message"],
        "path": "tokens.dark.json#/color/ring",
    }


def test_warnings_pass_unless_strict() -> None:
    folder = str(FIXTURES / "warn-no-preview")
    assert runner.invoke(app, ["themes", "validate", folder]).exit_code == 0
    strict = runner.invoke(app, ["themes", "validate", folder, "--strict"])
    assert strict.exit_code == 1
    assert "preview.missing" in strict.output


@pytest.mark.parametrize("path", ["does/not/exist", "README.md"])
def test_missing_or_non_theme_path_is_a_usage_error(path: str) -> None:
    assert runner.invoke(app, ["themes", "validate", str(REPO / path)]).exit_code == 2


def test_list_shows_validity_and_the_active_theme(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HEARTHOS_THEME_PATHS", f"{REPO / 'themes' / 'builtin'},{FIXTURES}")
    monkeypatch.setenv("HEARTHOS_DATABASE_URL", "postgresql+psycopg://x:y@127.0.0.1:9/nowhere")
    result = runner.invoke(app, ["themes", "list"])
    assert result.exit_code == 0, result.output
    rows = [line for line in result.stdout.splitlines() if line[:2] in ("* ", "  ")]
    lines = {line[2:].split()[0]: line for line in rows}
    assert lines["org.hearthos.theme.default"].startswith("*"), "Default is active without a stored choice"
    assert "valid" in lines["org.hearthos.theme.paper"]
    assert "invalid" in lines["org.example.theme.invalid-alias-cycle"]
    assert "database" in result.stdout.lower(), "say that the stored choice could not be read"
    assert "theme.loaded" not in result.stdout, "logs go to stderr, not into the listing"
