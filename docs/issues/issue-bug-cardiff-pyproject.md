# [BUG] [rev] Built wheel omits the bundled business-card template and the project README

## Summary

A wheel built from `cardiff/` contains only Python modules. It does not include `cardiff/templates/business-card/card.tex` or `manifest.json`, so a standard (non-editable) install of `cardiff-cli` cannot render the bundled template and fails with `template_not_found`. The same build also warns that `README.md` cannot be found, which leaves the package metadata without a long description. The release workflow publishes distributions to PyPI but verifies only an editable install, so neither gap is caught. The desired outcome is a wheel that renders the bundled template after a normal install and carries a non-empty project description.

## Issue Type

Primary type: bug

Labels:
- `bug` (pre-existing)
- `for experienced devs` (pre-existing)

Secondary types: none.

## Readiness Grade

AGENT_READY

The defect was reproduced end to end during the pre-issue audit. The steps were: build the wheel, list its contents, install it into a fresh virtual environment, and run the documented render command, which returned `template_not_found`. The configuration lines responsible are directly observed in `cardiff/pyproject.toml`. Acceptance criteria are checkable by inspecting the wheel and running the installed CLI. The open question about which README to ship is non-blocking.

## Source Context

Path-scoped context in the current repository: `cardiff/pyproject.toml`, with supporting reads of `.github/workflows/release.yml`, `cardiff/src/cardiff/rendering/templates.py`, and `README.md`, plus reporter-supplied reproduction evidence from a pre-issue audit.

## Detection Context

Detected in branch: `rev`

GitHub repository: zcalifornia-ph/cardiff

Local artifact path: `docs/issues/issue-bug-cardiff-pyproject.md`

Audited at commit `3a29f30`.

## Blockers and Dependencies

No blockers identified from the loaded evidence.

No GitHub issue dependency was attached.

## Scope

In scope:
- Packaging configuration so built distributions include `cardiff/templates/business-card/card.tex` and `cardiff/templates/business-card/manifest.json`. Any future template package under `cardiff/templates/` should also be included.
- Packaging configuration so the `readme` reference resolves and the distribution metadata carries a long description.
- A CI or release check that fails if a built wheel lacks the bundled template files.

Out of scope:
- Changing the template content or the template resolution logic in `templates.py`.
- Changing the distribution name, version, entry point, or dependencies.
- Publishing a release.

## Current / Observed Behavior

Observed during the pre-issue audit (setuptools 82.0.0):

1. From `cardiff/`, `python -m pip wheel . --no-deps --no-build-isolation -w <scratch-dir>/wheel` produced `cardiff_cli-0.1.7-py3-none-any.whl`. Its file list was:

   ```text
   cardiff/__init__.py
   cardiff/__main__.py
   cardiff/cli.py
   cardiff/paths.py
   cardiff/contract/{__init__,errors,loaders,models,sanitization,validation}.py
   cardiff/rendering/{__init__,directives,models,pipeline,templates,tex}.py
   cardiff_cli-0.1.7.dist-info/{METADATA,WHEEL,entry_points.txt,top_level.txt,RECORD}
   ```

   No file under `cardiff/templates/` was present.

2. The verbose build output included `SetuptoolsWarning: File '<checkout>/cardiff/README.md' cannot be found`. The resulting `METADATA` was 283 bytes, with `Description-Content-Type: text/markdown` and no description body.

3. After installing that wheel into a fresh virtual environment, `cardiff render tests/fixtures/requests/valid-request.yaml --approved-asset-root tests/fixtures/approved-assets --output <scratch-dir>/installed.pdf --deterministic` (run from `cardiff/`) exited `3` with:

   ```text
   "failure_class": "template_not_found"
   template 'business-card' is not available under '<venv>/Lib/site-packages/cardiff/templates'
   ```

Code and configuration evidence (directly observed):
- `cardiff/pyproject.toml:9` declares `readme = "README.md"`. There is no `README.md` inside `cardiff/`; the project README is at the repository root.
- `cardiff/pyproject.toml:25-29` configures `package-dir` and `packages.find` with no package-data or manifest rules for non-Python files.
- `cardiff/src/cardiff/rendering/templates.py:236-239` (`get_default_template_root`) resolves templates from the installed package directory (`<package>/templates`).
- `.github/workflows/release.yml`: the `test` job installs with `pip install -e ".[dev]"` (editable). The `build` job runs `python -m build` and the `publish` job uploads `dist/` to PyPI. No step installs or inspects the built wheel.
- `README.md` states the `cardiff ...` command works "after editable or standard installation".

## Expected / Target Behavior

- A wheel built from `cardiff/` contains `cardiff/templates/business-card/card.tex` and `cardiff/templates/business-card/manifest.json`.
- After a standard install of that wheel, the documented deterministic render of the sample request exits `0`.
- The build emits no "README.md cannot be found" warning, and `METADATA` contains a non-empty long description.
- The release pipeline fails before publishing if the built wheel lacks the template files.

## Reproduction Steps or Validation Steps

Preconditions: Python `>=3.12` with `pip` and `setuptools`; working directory `cardiff/`; `<scratch-dir>` is a writable directory outside the repository.

1. Run `python -m pip wheel . --no-deps -w <scratch-dir>/wheel`.
2. List the wheel contents, for example with `python -m zipfile -l <scratch-dir>/wheel/cardiff_cli-0.1.7-py3-none-any.whl`.
3. Observe that no entry starts with `cardiff/templates/`.
4. Create a fresh virtual environment, then install the wheel into it with `<venv-python> -m pip install <scratch-dir>/wheel/cardiff_cli-0.1.7-py3-none-any.whl`.
5. From `cardiff/`, run `<venv>/bin/cardiff render tests/fixtures/requests/valid-request.yaml --approved-asset-root tests/fixtures/approved-assets --output <scratch-dir>/installed.pdf --deterministic`. On Windows the executable is `<venv>\Scripts\cardiff`.
6. Failing observation: exit code `3` and `"failure_class": "template_not_found"` in the JSON status line.

## Environment and Evidence

- Operating system: Windows 11 (audit machine).
- Runtime: Python 3.14.0, pip 25.2, setuptools 82.0.0.
- Build path used in the audit: `pip wheel --no-build-isolation`. The release workflow's `python -m build` path (sdist, then wheel) was not run. Recommended, not run. Inference: it reads the same `pyproject.toml` with no package-data or `MANIFEST.in` rules, so it is expected to omit the same files.
- Linux/macOS: Not provided / not verified.
- Wheel listing, warning text, and CLI failure text: quoted in Current / Observed Behavior. The local absolute paths are replaced with placeholders.

## Relevant Files, Symbols, and Tests

- `cardiff/pyproject.toml`: `readme` (`:9`), `[tool.setuptools]` and `[tool.setuptools.packages.find]` (`:25-29`). Directly observed.
- `cardiff/src/cardiff/templates/business-card/card.tex` and `manifest.json`: the files missing from the wheel. Directly observed.
- `cardiff/src/cardiff/rendering/templates.py`: `get_default_template_root` (`:236-239`), `resolve_template` (`:242-292`). Directly observed.
- `.github/workflows/release.yml`: `test`, `build`, and `publish` jobs. Directly observed.
- `.github/workflows/ci.yml`: editable install only. Directly observed.
- `README.md`: installation statements. Directly observed.

## Agent Handoff Notes

- Inspect first: `cardiff/pyproject.toml`. The data flow is install location → `get_default_template_root()` → `resolve_template()`.
- Search terms: `package-data`, `include-package-data`, `MANIFEST.in`, `readme`, `get_default_template_root`.
- Hypotheses to verify, not instructions:
  - Declaring package data for `cardiff/templates/**` (via `[tool.setuptools.package-data]` or a `MANIFEST.in` with `include-package-data`) would include the files.
  - Setuptools may refuse a `readme` path outside the project directory. A README inside `cardiff/` may be needed.
- Note: `templates/business-card/` has no `__init__.py`, and `business-card` is not a valid Python identifier. Check how the chosen package-data mechanism treats that directory before relying on it.
- Constraints: keep the distribution name `cardiff-cli` and the console script `cardiff` (`cardiff/pyproject.toml:31-32`). Keep `get_default_template_root()` semantics.
- Assumptions to avoid: an editable install passing tests does not prove a standard install works, because editable installs read templates from the source tree.

## Acceptance Criteria

- [ ] A wheel built from `cardiff/` contains `cardiff/templates/business-card/card.tex`.
- [ ] A wheel built from `cardiff/` contains `cardiff/templates/business-card/manifest.json`.
- [ ] After a standard install of that wheel, the deterministic render of `tests/fixtures/requests/valid-request.yaml` exits `0`.
- [ ] Building the wheel emits no `README.md cannot be found` warning.
- [ ] The built wheel's `METADATA` contains a non-empty long description.
- [ ] A CI or release workflow step fails when a built wheel lacks `cardiff/templates/business-card/manifest.json`.

## Test / Verification Plan

Existing tests to run (from `README.md` and `.github/workflows/ci.yml`; recommended, not run as part of issue authoring):
- `python -m pytest tests/contract -q -p no:cacheprovider`
- `python -m pytest tests/rendering -q -p no:cacheprovider`
- `python -m pytest tests/cli -q -p no:cacheprovider`

New checks likely needed:
- A workflow step that runs `python -m build`, installs the wheel into a clean environment (non-editable), and runs `cardiff render ... --deterministic` against the sample request. Place it in `.github/workflows/release.yml` before `publish`, and optionally in `ci.yml`.

Manual checks:
- Inspect the wheel listing for `cardiff/templates/business-card/`.
- Inspect `METADATA` for the description body.

Regression checks:
- Editable install (`pip install -e ".[dev]"`) still works and the existing suites still pass.

## Implementation Boundaries

- Non-goals: refactoring template discovery; moving templates out of the package; adding new templates.
- Forbidden shortcuts:
  - Do not hardcode a source-tree path into `get_default_template_root()`.
  - Do not ship test fixtures inside the wheel to make the render work.
- Compatibility: Python `>=3.12`; setuptools `>=68` per `[build-system]`; Windows, Linux, and macOS installs.
- Contracts to preserve: distribution name, version, console script, and the `--template-root` override behavior.
- Project conventions: Conventional Commits; changes to release automation go in `.github/workflows/`.

## Risks and Review Focus

- Deployment: the release workflow publishes to PyPI on `v*` tags. Review check: a dry-run build in CI shows the template files in the wheel before any tag is pushed.
- Regression: a package-data glob that is too broad could ship unintended files. Review check: the diff of the wheel file list is limited to `cardiff/templates/**`.
- Documentation drift: the README installation section should match the verified install path. Review check: a fresh-install smoke run follows `README.md` exactly.

## Work Mapping

User-provided context (audit wheel build and installed-CLI run) -> `cardiff/pyproject.toml`, `.github/workflows/release.yml` -> Acceptance Criteria above -> Test / Verification Plan above.

## Open Questions

- Maintainer, non-blocking: which README should become the package long description? Options are a package-specific `cardiff/README.md` or a copy of the root `README.md`. The root README contains repository-level sections that may not suit a PyPI page.
- Maintainer, non-blocking: has any version already been published to PyPI from this configuration? If so, a follow-up release note may be needed.

## Definition of Done

- [ ] code change is scoped to the in-scope list
- [ ] all acceptance criteria are observably met
- [ ] tests in the verification plan are added or updated and passing
- [ ] documentation, ADRs, or runbooks updated when the change requires it
- [ ] reviewer focus areas from the risk section are addressed
- [ ] work-mapping links are populated
- [ ] blocker/dependency status is resolved or explicitly carried forward
- [ ] issue is closed with a brief evidence summary referencing the verifying tests, commands, or screenshots
