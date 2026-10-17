"""Render the template with several answer sets and check the generated projects.

Each generated project is linted and its own test-suite is run, so a broken
template never reaches `copier copy` users.
"""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from copier import run_copy

TEMPLATE = Path(__file__).resolve().parents[1]

BASE = {
    "project_name": "Grid Forecast",
    "description": "Forecasts grid load",
    "author_name": "Test Author",
}


def render(tmp_path: Path, **answers: object) -> Path:
    dest = tmp_path / "project"
    run_copy(
        str(TEMPLATE),
        dest,
        data={**BASE, **answers},
        defaults=True,
        unsafe=False,
        quiet=True,
    )
    return dest


@pytest.fixture
def minimal(tmp_path: Path) -> Path:
    return render(tmp_path, include_docker=False, include_terraform=False, license="Proprietary")


@pytest.fixture
def full(tmp_path: Path) -> Path:
    return render(tmp_path, include_docker=True, include_terraform=True, python_version="3.13")


def test_derived_names(minimal: Path) -> None:
    pyproject = tomllib.loads((minimal / "pyproject.toml").read_text())
    assert pyproject["project"]["name"] == "grid-forecast"
    assert pyproject["project"]["scripts"] == {"grid-forecast": "grid_forecast.main:main"}
    assert (minimal / "src/grid_forecast/main.py").is_file()


def test_optional_parts_are_omitted(minimal: Path) -> None:
    for path in ("Dockerfile", ".dockerignore", "terraform", "LICENSE"):
        assert not (minimal / path).exists(), path
    nix = (minimal / "devenv.nix").read_text()
    assert "terraform" not in nix
    assert "hadolint" not in nix
    assert "allowUnfree" not in (minimal / "devenv.yaml").read_text()


def test_optional_parts_are_rendered(full: Path) -> None:
    assert (full / "terraform/main.tf").is_file()
    assert (full / "terraform/.tflint.hcl").is_file()
    assert "FROM python:3.13-slim" in (full / "Dockerfile").read_text()
    assert "MIT License" in (full / "LICENSE").read_text()
    nix = (full / "devenv.nix").read_text()
    assert "pkgs.python313" in nix
    assert "languages.terraform.enable = true;" in nix
    assert "tflint.enable = true;" in nix
    assert "allowUnfree: true" in (full / "devenv.yaml").read_text()


def test_github_expressions_survive_rendering(full: Path) -> None:
    # The workflow is copied verbatim: ${{ }} must not be eaten by Jinja.
    assert "${{ github.ref }}" in (full / ".github/workflows/ci.yml").read_text()


def test_answers_file_enables_copier_update(full: Path) -> None:
    answers = (full / ".copier-answers.yml").read_text()
    assert "include_terraform: true" in answers
    assert "_src_path:" in answers


def test_no_unrendered_jinja_left(full: Path) -> None:
    for path in full.rglob("*"):
        assert not path.name.endswith(".jinja"), path
        if path.is_file():
            text = path.read_text(errors="ignore")
            assert "{{ package_name" not in text and "{%" not in text, path


@pytest.mark.parametrize("variant", ["minimal", "full"])
def test_generated_project_passes_its_own_checks(variant: str, request: pytest.FixtureRequest) -> None:
    project: Path = request.getfixturevalue(variant)
    run = lambda *cmd: subprocess.run(cmd, cwd=project, capture_output=True, text=True)  # noqa: E731
    lint = run(sys.executable, "-m", "ruff", "check", ".")
    assert lint.returncode == 0, lint.stdout + lint.stderr
    fmt = run(sys.executable, "-m", "ruff", "format", "--check", ".")
    assert fmt.returncode == 0, fmt.stdout + fmt.stderr
    types = run(sys.executable, "-m", "mypy", "src")
    assert types.returncode == 0, types.stdout + types.stderr
    tests = run(sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider")
    assert tests.returncode == 0, tests.stdout + tests.stderr


def test_invalid_slug_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(Exception, match="kebab-case"):
        render(tmp_path, project_slug="Not_Valid")
