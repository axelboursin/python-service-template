# Python Service Template

A **[Copier](https://copier.readthedocs.io) template** for Python services, with a **reproducible development environment built on Nix and [devenv](https://devenv.sh)**. Every developer and the CI get the same Python, the same tools and the same git hooks, with the same versions, pinned by a lockfile.

Ten minutes of onboarding become one command, and "works on my machine" problems go away.

```bash
uvx copier copy gh:axelboursin/python-service-template my-service
cd my-service
devenv shell   # or let direnv load it on `cd`
```

## What you get

| Concern | Choice |
|---|---|
| Environment | **devenv** (Nix flakes under the hood), inputs pinned in `devenv.lock`, loaded automatically with **direnv** |
| Python | Interpreter from Nix (`UV_PYTHON_DOWNLOADS=never`), dependencies with **uv** and its lockfile, `uv sync` on shell entry |
| Quality | **ruff** (lint + format), **mypy --strict**, **pytest** with coverage ≥ 80% |
| Git hooks | Declared in `devenv.nix` and installed on shell entry: ruff, YAML/TOML checks, private-key detection, **gitleaks**, plus hadolint and terraform fmt/tflint when those options are enabled |
| Commands | `lint`, `fmt`, `tests`, and `devenv test`, the single command CI runs |
| Logging | Structured JSON logs to stdout |
| Docker *(option)* | Multi-stage build from `uv.lock`, slim runtime, non-root user |
| Terraform *(option)* | `terraform/` skeleton with S3 backend (partial config) + Terraform, TFLint and Trivy in the dev shell |
| CI | GitHub Actions: Nix + devenv with Cachix, running `devenv test` (the exact environment developers use) |
| Updates | `copier update` merges template improvements into existing projects (answers stored in `.copier-answers.yml`) |

## How the template itself is tested

- **`tests/test_template.py`** (9 tests): renders the template with several sets of answers. It checks:
  - which optional files are present or absent;
  - the derived names;
  - that `${{ }}` GitHub expressions survive Jinja;
  - that no `.jinja` leftovers remain;
  - that invalid answers are rejected.

  It then **runs ruff, mypy and pytest inside each generated project**.
- **CI matrix**: generates the minimal and full variants and runs **`devenv test`** in each with real Nix. It also runs every week, to catch upstream breakage from nixpkgs or tool releases.

```bash
uv sync
uv run pytest
```

## Layout

```text
.
├── copier.yml                # questions, validators, defaults
├── template/                 # rendered into the new project (_subdirectory)
│   ├── devenv.nix.jinja      # packages, python + uv, git hooks, scripts, enterTest
│   ├── devenv.yaml.jinja     # pinned inputs (+ allowUnfree only when Terraform is enabled)
│   ├── .envrc                # direnv integration
│   ├── pyproject.toml.jinja  # uv, ruff, mypy, pytest, coverage
│   ├── src/{{ package_name }}/ …
│   └── {% if include_docker %}Dockerfile{% endif %}.jinja …
└── tests/test_template.py
```

## Status

Template rendering and the generated projects' Python checks are tested locally. The `devenv test` step runs in CI only, because it needs Nix.
