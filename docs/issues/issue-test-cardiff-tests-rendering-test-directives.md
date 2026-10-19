# [TEST] [rev] Write QR directive test output to tmp_path instead of the tracked _directive-work fixture directory

## Summary

Four tests in `cardiff/tests/rendering/test_directives.py` write QR PNGs into `cardiff/tests/fixtures/approved-samples/business-card/_directive-work/`, a directory inside the tracked fixture tree. Three of those PNGs are committed to git, even though `CHANGELOG.md` has listed `_directive-work/` under "For Deletion" as a generated test work directory since several releases. Every test run recreates the directory, so it cannot be removed, and the CI and release workflows delete it before each run. The desired outcome is that these tests write only to pytest temporary directories, so the tracked fixture tree is never written by a test run. The other tests that wrote into `approved-samples/` were already moved to `tmp_path` in #54; this issue covers the remaining helper.

## Issue Type

Primary type: test

Labels:
- `test` (created before publication)
- `good first issue` (pre-existing)
- `light work` (pre-existing)

Secondary types: none.

## Readiness Grade

AGENT_READY

The writing helper and all four call sites are directly observed in the cited lines. The tracked files are listed by `git ls-files`. The failing observation was reproduced in a disposable clone: delete the directory, run the test module, and the directory is recreated (see Reproduction Steps). That gives a crisp pass/fail oracle. The change is test-only, follows the pattern #54 already applied to the neighboring test modules, and has no blocking open question.

## Source Context

Path-scoped context in the current repository: `cardiff/tests/rendering/test_directives.py`. Supporting reads:
- `cardiff/src/cardiff/rendering/directives.py`: the `generate_qr_png` and `resolve_qr_directives` signatures.
- `.github/workflows/ci.yml` and `.github/workflows/release.yml`: the cleanup steps.
- `CHANGELOG.md`: the For Deletion entries.
- `cardiff/tests/fixtures/approved-samples/business-card/README.md`.

## Detection Context

Detected in branch: `rev`

GitHub repository: zcalifornia-ph/cardiff

Local artifact path: `docs/issues/issue-test-cardiff-tests-rendering-test-directives.md`

Line numbers below are from `rev` at commit `c3e14a5`.

## Blockers and Dependencies

No blockers identified from the loaded evidence.

Recommended sequencing (text-only, no dependency attached because #54 is a pull request, not an issue): start after #54 is merged. #54 moves the other rendering and CLI tests off the tracked `approved-samples/` directory and documents that in the fixture `README.md`. This issue should follow the same pattern on the same base.

## Scope

In scope:
- Replace the four `_work_dir(...)` call sites in `cardiff/tests/rendering/test_directives.py` with paths under pytest's `tmp_path` fixture.
- Remove the `_work_dir` helper and the module-level `APPROVED_SAMPLES` and `FIXTURES_ROOT` constants once they are unused, along with the `from pathlib import Path` import if nothing else uses it.

Out of scope:
- Deleting the tracked files under `cardiff/tests/fixtures/approved-samples/business-card/_directive-work/`. They are already listed under "For Deletion" in `CHANGELOG.md` for a maintainer to remove.
- Editing the `Clean transient test work directories` steps in `.github/workflows/ci.yml` and `.github/workflows/release.yml`.
- Changing `cardiff/src/cardiff/rendering/directives.py` or any other source module.
- Changing what the tests assert.

## Current / Observed Behavior

Observed in `cardiff/tests/rendering/test_directives.py`:

- Lines 232-233 define `FIXTURES_ROOT` and `APPROVED_SAMPLES = FIXTURES_ROOT / "approved-samples" / "business-card"`.
- Lines 247-250 define the helper:

  ```python
  def _work_dir(name: str) -> Path:
      path = APPROVED_SAMPLES / "_directive-work" / name
      path.mkdir(parents=True, exist_ok=True)
      return path
  ```

- Four tests write through it:
  - line 314: `TestGenerateQrPng.test_creates_valid_png` writes `_directive-work/png/test.png`.
  - line 326: `TestResolveQrDirectives.test_enabled_replaces_with_includegraphics` writes `_directive-work/enabled/cardiff-qr.png`.
  - line 339: `TestResolveQrDirectives.test_disabled_emits_nothing` creates an empty `_directive-work/disabled/`.
  - line 351: `TestResolveQrDirectives.test_options_pass_through` writes `_directive-work/options/cardiff-qr.png`.
- `git ls-files` lists three committed outputs: `_directive-work/enabled/cardiff-qr.png`, `_directive-work/options/cardiff-qr.png`, and `_directive-work/png/test.png`.
- `.github/workflows/ci.yml` line 74 and `.github/workflows/release.yml` line 72 `rm -rf` that directory in the `Clean transient test work directories` step. Each CI run therefore deletes tracked files in its checkout before the tests recreate them.
- `CHANGELOG.md` lists `cardiff/tests/fixtures/approved-samples/business-card/_directive-work/` under "For Deletion" as a "generated QR directive test work directory" in six release sections, starting at line 30.

`git status` does not reveal the writes, because the regenerated PNGs are byte-identical to the committed ones. The writes are only visible when the directory is absent before the run.

## Expected / Target Behavior

Running `cardiff/tests/rendering/test_directives.py` creates nothing under `cardiff/tests/fixtures/`. Every PNG the tests produce lives under a pytest temporary directory, and all ten tests in the module still pass with unchanged assertions.

## Reproduction Steps or Validation Steps

1. Make a disposable clone of the repository at `rev` and change into its `cardiff/` directory. Do not run this in a working copy you care about, because step 2 deletes tracked files.
2. Delete the directory: `rm -rf tests/fixtures/approved-samples/business-card/_directive-work`.
3. Run `python -m pytest tests/rendering/test_directives.py -q -p no:cacheprovider` and observe `10 passed`.
4. Run `find tests/fixtures/approved-samples/business-card/_directive-work | sort`.
5. Failing observation: the directory exists again and contains `disabled/`, `enabled/cardiff-qr.png`, `options/cardiff-qr.png`, and `png/test.png`. After the fix, step 4 reports that the path does not exist.

## Environment and Evidence

- **Operating system and runtime:** reproduced on Windows 11 with Python 3.14.0 in a disposable clone at commit `c3e14a5`. The behavior is OS-independent; the paths come from `Path(__file__)`.
- **Commands:** taken from the steps above and `CONTRIBUTING.md` Verification Notes.
- **Logs, stack traces, screenshots:** not applicable; no test fails today.

## Relevant Files, Symbols, and Tests

- `cardiff/tests/rendering/test_directives.py`: directly observed.
  - Constants and helper: `FIXTURES_ROOT`, `APPROVED_SAMPLES`, and `_work_dir`.
  - Tests: `TestGenerateQrPng.test_creates_valid_png` and `TestResolveQrDirectives.test_enabled_replaces_with_includegraphics`, `test_disabled_emits_nothing`, and `test_options_pass_through`.
- `cardiff/src/cardiff/rendering/directives.py`: directly observed.
  - `generate_qr_png(data, output_path, *, scale=4)` writes the PNG to the given path.
  - `resolve_qr_directives(..., work_dir=...)` writes its PNG into `work_dir`.
- `.github/workflows/ci.yml` line 74 and `.github/workflows/release.yml` line 72: cleanup entries for `_directive-work`. Directly observed; out of scope.
- `CHANGELOG.md`: "For Deletion" entries for `_directive-work/`. Directly observed.
- `cardiff/tests/fixtures/approved-samples/business-card/README.md`: after #54, it says the test suites do not rewrite the listed sample files. Directly observed.

## Agent Handoff Notes

- Inspect `_work_dir` and its four call sites first; that is the whole change surface.
- Search terms: `_work_dir`, `_directive-work`, `APPROVED_SAMPLES`.
- **Pattern to follow:** #54 converted `cardiff/tests/rendering/test_pipeline.py`, `cardiff/tests/rendering/test_determinism.py`, and `cardiff/tests/cli/test_cli.py` by adding a `tmp_path` parameter and building output paths from it. Pytest injects `tmp_path` into methods of plain test classes the same way, for example `def test_creates_valid_png(self, tmp_path):`.
- **Constraints:**
  - Keep the test names and assertions unchanged.
  - Keep the existing Apache attribution header at the top of the module (see `CONTRIBUTING.md`).
- **Assumptions to avoid:**
  - Do not treat a clean `git status` after a run as proof the tests no longer write into fixtures; the regenerated PNGs are byte-identical.
  - Use the deleted-directory oracle in the Reproduction Steps instead.

## Acceptance Criteria

- [ ] `cardiff/tests/rendering/test_directives.py` contains no reference to `_directive-work`.
- [ ] `cardiff/tests/rendering/test_directives.py` contains no reference to `APPROVED_SAMPLES`.
- [ ] With `_directive-work/` deleted first, running `python -m pytest tests/rendering/test_directives.py -q -p no:cacheprovider` from `cardiff/` does not recreate `tests/fixtures/approved-samples/business-card/_directive-work`.
- [ ] `python -m pytest tests/rendering/test_directives.py -q -p no:cacheprovider` reports `10 passed`.
- [ ] `python -m pytest tests/rendering -q -p no:cacheprovider` passes from `cardiff/`.
- [ ] No file under `cardiff/src/` is modified.

## Test / Verification Plan

- **Existing tests to run** (commands from `CONTRIBUTING.md` Verification Notes, run from `cardiff/`): `python -m pytest tests/rendering -q -p no:cacheprovider`. Run `tests/contract` and `tests/cli` as a regression sweep.
- **New tests likely needed:** none. This change relocates where existing tests write.
- **Manual check:** the deleted-directory oracle in the Reproduction Steps, run in a disposable clone.
- **Regression checks:**
  - `TestGenerateQrPng.test_creates_valid_png` still checks the PNG signature `\x89PNG`.
  - The three `TestResolveQrDirectives` tests still check the emitted `\includegraphics` text.
- **Security checks:** not applicable. The generated QR payload uses the fixed test identity `Ada Lovelace`.
- **Performance checks:** not applicable.

## Implementation Boundaries

- **Non-goals:**
  - Do not delete the tracked `_directive-work/` files.
  - Do not edit the workflow cleanup steps.
  - Do not touch `cardiff/src/`.
- **Forbidden shortcuts:**
  - Do not add `_directive-work/` to `.gitignore` as a substitute for moving the writes.
  - Do not mark the tests as skipped.
- **Compatibility:**
  - Python 3.12 and 3.13.
  - Windows and Linux CI legs.
- **Conventions:** follow the existing class-based test style in the module and the `tmp_path` usage introduced in #54.

## Risks and Review Focus

- **Regression:** a test that silently stops exercising PNG generation. Check that every converted test still asserts on the file or on emitted TeX, as before.
- **Documentation drift:** once the tracked files are deleted in a later maintainer change, the "For Deletion" entries in `CHANGELOG.md` and the cleanup steps in both workflows become stale. Not required here, but worth noting in the pull request.

## Work Mapping

Reporter-supplied context (follow-up from #54 review) -> `cardiff/tests/rendering/test_directives.py` -> acceptance criteria above -> verification plan above.

## Open Questions

- **Non-blocking, maintainer:** should the tracked `_directive-work/` files and the matching cleanup-step entries be removed in the same pull request as this change, or in a separate maintainer cleanup?

## Definition of Done

- [ ] code change is scoped to the in-scope list
- [ ] all acceptance criteria are observably met
- [ ] tests in the verification plan are added or updated and passing
- [ ] documentation, ADRs, or runbooks updated when the change requires it
- [ ] reviewer focus areas from the risk section are addressed
- [ ] work-mapping links are populated
- [ ] blocker/dependency status is resolved or explicitly carried forward
- [ ] issue is closed with a brief evidence summary referencing the verifying tests, commands, or screenshots
