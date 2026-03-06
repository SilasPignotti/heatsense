# Plan: Polish — heatsense

## Goal
Make heatsense portfolio-ready. Cosmetic changes only — functionality unchanged.

## Constraints
- No logic changes, no control flow changes
- No directory restructuring
- No runtime dependency changes
- nox must be green before final commit
- English for all code, comments, docs, commits
- Repository visibility stays private until manual review

## Context
- Repo: https://github.com/silas-workspace/heatsense
- Key files to read before exec:
  - `AGENTS.md`
  - `pyproject.toml`
  - `src/heatsense/config/settings.py`
  - `src/heatsense/data/urban_heat_island_analyzer.py`
  - `src/heatsense/webapp/app.py`
  - `src/heatsense/webapp/analysis_backend.py`
  - `src/heatsense/data/dwd_downloader.py`
  - `src/heatsense/utils/data_processor.py`
- External tools required: gh CLI, uv

## Audit Findings

| Area        | Finding |
|-------------|---------|
| Security    | Flask placeholder dev keys (`heatsense-dev-key-2025`, `uhi-analyzer-secret-key`) in old commits; `credentials.py` existed in early commits but contained no actual credentials — only env-var helper functions. Current code uses `os.environ.get()`. No real secrets. Low risk, no purge needed. |
| Tooling     | No `noxfile.py`. No `[tool.ruff]` or `[tool.pyright]` sections in `pyproject.toml`. `ruff` and `pytest` are listed as **runtime** dependencies instead of dev deps. |
| Docs        | README.md exists but has placeholder URLs (`your-username/HeatSense`) and placeholder author in `pyproject.toml` (`Your Name` / `your.email@example.com`). Project URLs in `pyproject.toml` also placeholder. README emoji style uses emojis in bullet points (match existing style). |
| Code        | Module-level docstrings carry verbose "Dependencies:" sections that duplicate `pyproject.toml`. Class `__init__` docstring in `UrbanHeatIslandAnalyzer` duplicates the class docstring verbatim. `sys.path.append` hack in `app.py` is unnecessary with installed package but is harmless to leave (touching it risks breakage). `settings.py` has trailing whitespace and inconsistent blank lines. |
| Git hygiene | 20 commits. Mix of Conventional Commits and free-form messages. Several commits in German, one with emoji (`🚀 Cache-System konsolidiert und Architektur optimiert`). Multiple commits without a `type:` prefix. History is substantive — no obvious squash candidates. |

---

## Tasks

- [x] 1. Security Sweep [AUTO]
  - [x] ~~1.1 git-filter-repo purge~~ — No real credentials found. Flask dev fallback values are just placeholders. No action needed.
  - [x] 1.2 Verify `.gitignore` covers `.env`, credential files — already present, add `*.json` exclusion note (currently `.json` is excluded globally which also blocks `copernicus_api_key.json`)
  - [x] 1.3 `.env.example` already exists and is complete — no action needed.

- [x] 2. Tooling Setup [AUTO]
  - [x] 2.1 Add `[tool.ruff]` section to `pyproject.toml`:
        ```toml
        [tool.ruff]
        target-version = "py311"
        line-length = 100

        [tool.ruff.lint]
        select = ["E", "F", "I", "UP", "B", "SIM"]
        ignore = ["E501"]

        [tool.ruff.lint.isort]
        known-first-party = ["heatsense"]
        ```
  - [x] 2.2 Add `[tool.pyright]` section:
        ```toml
        [tool.pyright]
        pythonVersion = "3.11"
        venvPath = "."
        venv = ".venv"
        typeCheckingMode = "basic"
        include = ["src"]
        ```
  - [x] 2.3 Move `ruff` and `pytest` from `[project.dependencies]` to
        `[project.optional-dependencies]` dev group:
        ```toml
        [project.optional-dependencies]
        dev = [
            "ruff>=0.12.0",
            "pytest>=7.0.0",
            "pyright",
            "nox",
        ]
        ```
        Note: `requires-python = ">=3.11,<3.12"` is overly restrictive — widen to `>=3.11`
        (this is metadata only, not a runtime dep change).
  - [x] 2.4 Create `noxfile.py` at repo root:
        ```python
        import nox

        @nox.session
        def lint(session):
            session.install("ruff")
            session.run("ruff", "check", ".")
            session.run("ruff", "format", "--check", ".")

        @nox.session
        def typecheck(session):
            session.install("pyright")
            session.install("-e", ".[dev]")
            session.run("pyright")
        ```
        No test session — no `tests/` directory exists.
  - [x] 2.5 Run `nox` — document any failures as input for Task 3.

- [x] 3. Code Cosmetics [AUTO]
  - [x] 3.1 `ruff format .` — enforce consistent formatting
  - [x] 3.2 `ruff check --fix .` — auto-fix linting issues (unused imports, style)
  - [x] 3.3 Clean up docstrings:
        - Remove "Dependencies:" sections from all module-level docstrings — this info
          belongs in `pyproject.toml`, not docstrings.
        - Remove the `__init__` method docstring from `UrbanHeatIslandAnalyzer` —
          it is a one-liner that restates the class docstring.
        - Remove "Key features:" / "Key capabilities:" bullets that duplicate the class
          docstring's opening paragraph.
        - Keep: Args sections, Returns sections, and non-obvious caveats.
        - Files to touch: `urban_heat_island_analyzer.py`, `app.py`,
          `analysis_backend.py`, `dwd_downloader.py`, `data_processor.py`,
          `corine_downloader.py`, `wfs_downloader.py`, `settings.py`, `__init__.py`
  - [x] 3.4 Remove / trim dead comments:
        - `settings.py`: inline comments on `CRS_CONFIG` values are fine (non-obvious
          EPSG codes). Keep them.
        - `app.py`: remove `# Add project root to Python path` block comment and the
          `sys.path.append` line — the package is installed via `uv sync`, making it
          unnecessary. **Verify import still works after removal.**
        - `data_processor.py`: inline comments on CORINE code→category mappings
          are genuinely useful — keep them.
  - [x] 3.5 Type hints: already comprehensive throughout. No additions needed.
  - [x] 3.6 Run `nox` — lint + typecheck must be green.

- [x] 4. Documentation [AUTO]
  - [x] 4.1 Update `README.md`:
        - Replace all `your-username/HeatSense` placeholder URLs with
          `silas-workspace/heatsense`
        - Replace `http://localhost:8000 🎉` — remove the emoji from body text
        - "Open your browser to **http://localhost:8000**" is fine
        - Programmatic usage example: replace `from src.heatsense.webapp...` with
          `from heatsense.webapp...` (matches installed package path)
        - README already uses emojis in bullet points — match existing style,
          do not strip them (the repo established this style before AGENTS.md)
  - [x] 4.2 LICENSE already exists (MIT) — verify author name is `Silas Pignotti`.
        Check year matches first commit year (2025).
  - [x] 4.3 Fill `pyproject.toml` metadata:
        - `authors`: `[{name = "Silas Pignotti", email = "pignottisilas@gmail.com"}]`
          (email visible in `git log`)
        - `[project.urls]` Homepage, Repository, Bug Reports: replace `your-username`
          with `silas-workspace`, update repo name to `heatsense` (lowercase)
        - `requires-python`: widen from `">=3.11,<3.12"` to `">=3.11"`
  - [x] 4.4 `.gitignore` is solid. Already updated in Phase 1 to cover `.pi/` dirs.

- [x] 5. Git Hygiene [AUTO + CONFIRM]
  - [x] 5.1 Analyze and normalize commit history [AUTO]

    **Current history (oldest → newest):**
    ```
    703c337  Initial commit: Urban Heat Island Analyzer - Projektstruktur, Downloader, Dokumentation, Tests
    37d10f0  feat: integrate BerlinWeatherService with DWD weather data download
    b25048f  Docs and codebase cleanup: update docs, remove unused credentials.py, translate __init__.py, and sync configuration. Also add new analyzer documentation. Updated classes and config.
    d0935ae  Refactor test structure: move all tests to tests/, update import paths, enforce strict date parsing in CorineDataDownloader, and ensure all tests pass. Remove test subfolders. Modernize all test files to pytest class-based style.
    a0ba275  Update urban heat island analyzer with new features and improvements
    4e660e3  feat: Transform analyze_heat_islands.py into dynamic CLI tool
    fa1c9a9  🚀 Cache-System konsolidiert und Architektur optimiert
    651edc2  feat: Add comprehensive tests and documentation for new UHI analyzer classes
    8f7b83d  refactor: fix linting issues
    1879a34  refactored all the classes and backend logic, cleaned up dict
    dfe6c3b  created webapp, updated docs und read me
    806c1d1  created webapp
    87674b2  Webapp and backend working.
    ddbceef  refactor: remove obsolete analyzer factory pattern
    c8ed502  Initial project setup with optimized structure
    c427cd7  Restructure project with optimized GitHub-ready setup
    439a48c  Implement complete data visualization layers
    1c6c6b6  Implement German UHI categorization and temperature effect visualization
    e4d3681  Refactor and enhance mitigation recommendations system
    e20b1d7  refactor: Enhance backend implementation and improve code structure
    ```

    **Proposed rewrite (oldest → newest):**
    ```
    703c337  REWORD → chore: initial project setup — analyzers, downloaders, docs
    37d10f0  KEEP   → feat: integrate BerlinWeatherService with DWD weather data download
    b25048f  REWORD → chore: clean up docs, remove credentials.py, translate init, sync config
    d0935ae  REWORD → refactor: reorganize test structure and modernize to pytest class style
    a0ba275  REWORD → feat: add new features and improvements to UHI analyzer
    4e660e3  KEEP   → feat: Transform analyze_heat_islands.py into dynamic CLI tool
    fa1c9a9  REWORD → refactor: consolidate cache system and optimize architecture
    651edc2  KEEP   → feat: Add comprehensive tests and documentation for new UHI analyzer classes
    8f7b83d  KEEP   → refactor: fix linting issues
    1879a34  REWORD → refactor: restructure classes and backend logic
    dfe6c3b  REWORD → feat: create webapp, update docs and README
    806c1d1  SQUASH → (into dfe6c3b — "created webapp" is split noise)
    87674b2  REWORD → feat: get webapp and backend working end-to-end
    ddbceef  KEEP   → refactor: remove obsolete analyzer factory pattern
    c8ed502  REWORD → chore: restructure project with optimized layout
    c427cd7  SQUASH → (into c8ed502 — back-to-back restructure commits)
    439a48c  REWORD → feat: implement data visualization layers
    1c6c6b6  REWORD → feat: implement UHI categorization and temperature effect visualization
    e4d3681  REWORD → refactor: enhance mitigation recommendations system
    e20b1d7  KEEP   → refactor: Enhance backend implementation and improve code structure
    ```

    Rules applied:
    - `806c1d1` squashed into `dfe6c3b` (consecutive webapp creation commits)
    - `c427cd7` squashed into `c8ed502` (consecutive project setup/restructure)
    - German text translated to English
    - Emoji removed from `fa1c9a9`
    - All messages normalized to Conventional Commits format
    - No commits fabricated, no reordering

    **Show this plan to user and wait for explicit approval before executing rebase.**

    Execution (on approval):
    ```bash
    # Write /tmp/rebase-todo with the sequence editor commands, then:
    GIT_SEQUENCE_EDITOR="cp /tmp/rebase-todo" \
    GIT_EDITOR="true" \
    git rebase -i --root
    ```

  - [x] 5.2 ⚠️ CONFIRM: Force-push rebased history
        Show `git log --oneline` for final verification, then:
        ```bash
        git push --force-with-lease origin main
        ```

- [x] 6. New Commits [AUTO]
  Commit polish work in logical groups after rebase:
  - `chore: add AGENTS.md with project context and constraints`
  - `chore: add dev tooling — nox, ruff config, pyright config`
  - `chore: move ruff and pytest to dev optional-dependencies`
  - `style: apply ruff formatting and linting`
  - `style: clean up docstrings — remove AI bloat and redundant sections`
  - `docs: fix placeholder URLs and author metadata in README and pyproject.toml`
  - `chore: update .gitignore to exclude .pi/ workspace dirs`

- [x] 7. Repo Settings [AUTO]
  - [x] 7.1 Set GitHub description:
        `Urban Heat Island analysis for Berlin — satellite, weather, and land use data`
  - [x] 7.2 Add topics: `urban-heat-island`, `geospatial`, `google-earth-engine`, `berlin`, `climate`, `flask`, `python`
  - [x] 7.3 Set branch protection on main
  - [x] 7.4 Disable wiki, projects, discussions
  ```bash
  gh repo edit silas-workspace/heatsense \
    --description "Urban Heat Island analysis for Berlin — satellite, weather, and land use data" \
    --add-topic urban-heat-island \
    --add-topic geospatial \
    --add-topic google-earth-engine \
    --add-topic berlin \
    --add-topic climate \
    --add-topic flask \
    --add-topic python \
    --enable-wiki=false \
    --enable-projects=false

  gh api repos/silas-workspace/heatsense/branches/main/protection \
    --method PUT \
    --field enforce_admins=true \
    --field "required_status_checks=null" \
    --field "required_pull_request_reviews=null" \
    --field "restrictions=null" \
    --field allow_force_pushes=false \
    --field allow_deletions=false
  ```

- [x] 8. Knowledge Capture [AUTO]
  - [x] 8.1 Read `.pi/LESSONS.md` after exec — identify cross-project entries
  - [x] 8.2 Suggest migration of any cross-project entries to `~/.pi/agent/LESSONS.md`
  - [x] 8.3 Note if `.pi/LESSONS.md` ends up empty

- [x] 9. Final Validation [AUTO]
  - [x] 9.1 Run `nox` — all sessions green (lint + typecheck)
  - [x] 9.2 Verify README renders on GitHub

---

## Manual Steps Summary
- Task 5.1: Rebase plan requires explicit user approval before execution
- Task 5.2: Force-push always requires explicit user confirmation

## Success Criteria
- [x] nox passes (lint + typecheck)
- [x] No real secrets in git history (confirmed clean — no action taken)
- [x] README exists and is useful, with correct URLs
- [x] Conventional Commits throughout git history
- [x] pyproject.toml has correct author metadata and project URLs
- [x] `ruff` and `pytest` in dev optional-dependencies, not runtime deps
- [x] noxfile.py present and functional
- [x] Branch protection active on main
- [x] Code behavior unchanged from original
