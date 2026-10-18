# [BUG] [rev] Asset validation rejects Windows absolute paths inside approved roots as remote URLs

## Summary

`validate_asset_reference` first rejects anything `urlparse` reports as having a URL scheme. It tries to exempt Windows drive letters with the regex `^[a-zA-Z]:$`, but `urlparse` returns the scheme without the colon (`"c"`), so the exemption never matches. On Windows, every drive-letter absolute asset path is therefore rejected with "asset paths must be local files inside approved roots", including paths inside a caller-approved root. The validation contract and template-authoring docs say these paths are allowed. CI runs only on Ubuntu and no test covers absolute asset paths, so the gap is unguarded. The desired outcome is that Windows absolute paths inside approved roots validate, while URLs and paths outside approved roots remain rejected.

## Issue Type

Primary type: bug

Labels:
- `bug` (pre-existing)
- `for experienced devs` (pre-existing)

Secondary types: none.

## Readiness Grade

AGENT_READY

The rejection was reproduced on Windows during the pre-issue audit, including the `urlparse` scheme value that defeats the exemption. The faulty condition is a single directly observed line range. The documented contract is explicit. Acceptance criteria are exact validation outcomes. The fix sits in a path-safety guard, so the review focus is called out, but no input is missing.

## Source Context

Path-scoped context in the current repository: `cardiff/src/cardiff/contract/validation.py`, with supporting reads of `cardiff/src/cardiff/rendering/templates.py`, `cardiff/docs/validation-contract.md`, `cardiff/docs/template-authoring.md`, `cardiff/tests/contract/test_security.py`, and `.github/workflows/ci.yml`, plus reporter-supplied reproduction evidence from a pre-issue audit.

## Detection Context

Detected in branch: `rev`

GitHub repository: zcalifornia-ph/cardiff

Local artifact path: `docs/issues/issue-bug-cardiff-src-cardiff-contract-validation--2.md`

Audited at commit `3a29f30`.

## Blockers and Dependencies

No blockers identified from the loaded evidence.

No GitHub issue dependency was attached.

## Scope

In scope:
- The URL-scheme check in `validate_asset_reference`, so Windows drive-letter absolute paths reach the existing absolute-path branch.
- Tests for absolute asset paths inside and outside approved roots.

Out of scope:
- Render-time asset resolution in `cardiff/src/cardiff/rendering/templates.py`. It does not use `urlparse`.
- UNC paths (`\\server\share\...`). Record their behavior in Open Questions if it is touched.
- Allowed extensions, asset slots, or approved-root semantics.

## Current / Observed Behavior

Observed on Windows during the pre-issue audit. The script was run from `cardiff/`:

```python
from pathlib import Path
from urllib.parse import urlparse
from cardiff.contract import AssetReference, validate_asset_reference

root = Path("tests/fixtures/approved-assets").resolve()
logo = root / "brand" / "logo.png"
for candidate in (str(logo), logo.as_posix()):
    print(repr(urlparse(candidate).scheme),
          validate_asset_reference(AssetReference("logo", candidate), [root]))
```

Output (both forms):

```text
'c' (ValidationIssue(code=<ValidationCode.INVALID_ASSET_PATH: 'invalid_asset_path'>, field='assets.logo', message='asset paths must be local files inside approved roots', severity='error'),)
'c' (ValidationIssue(code=<ValidationCode.INVALID_ASSET_PATH: 'invalid_asset_path'>, field='assets.logo', message='asset paths must be local files inside approved roots', severity='error'),)
```

The file exists inside the approved root that was passed in.

Code evidence (directly observed):
- `cardiff/src/cardiff/contract/validation.py:385-395`: `parsed = urlparse(candidate)` and `if parsed.scheme and not re.match(r"^[a-zA-Z]:$", parsed.scheme):` reject. `parsed.scheme` for `C:\...` or `C:/...` is `"c"`, so the regex (which requires a trailing colon) never matches.
- `cardiff/src/cardiff/contract/validation.py:397-409`: the absolute-path branch that should handle these paths is unreachable for drive-letter paths.
- `cardiff/docs/validation-contract.md` (Approved Template Notes) and `cardiff/docs/template-authoring.md` (Asset Packaging Rules) both say absolute paths are acceptable when they resolve inside an approved asset root.
- `.github/workflows/ci.yml` runs on `ubuntu-latest` only. A search of `cardiff/tests` for absolute-path asset cases found none. `cardiff/tests/contract/test_security.py` covers traversal (`:228`) and remote URLs (`:251`).

## Expected / Target Behavior

- On Windows, `C:\...\approved-root\brand\logo.png` and `C:/.../approved-root/brand/logo.png` validate with no issues when the root is approved.
- A drive-letter absolute path outside every approved root is rejected with `invalid_asset_path` and the message `absolute asset paths must stay inside an approved root`.
- `https://...`, `http://...`, and `file://...` asset paths remain rejected with `asset paths must be local files inside approved roots`.

## Reproduction Steps or Validation Steps

Preconditions: Windows; dependencies installed per `README.md` (`python -m pip install -e ".[dev]"`); working directory `cardiff/`.

1. Run the script in Current / Observed Behavior.
2. Observe that the printed scheme is `'c'`.
3. Failing observation: both candidates return an `invalid_asset_path` issue with message `asset paths must be local files inside approved roots`, even though the file is inside the approved root.

## Environment and Evidence

- Operating system: Windows 11 (audit machine).
- Runtime: Python 3.14.0. `urlparse` scheme handling for single-letter schemes is long-standing standard-library behavior. Older supported versions (3.12, 3.13) were not run. Recommended, not run.
- Linux/macOS: not affected by inspection, because POSIX absolute paths have no scheme.
- Script output: quoted in Current / Observed Behavior. Absolute local paths are omitted.

## Relevant Files, Symbols, and Tests

- `cardiff/src/cardiff/contract/validation.py`: `validate_asset_reference` (`:364-446`), `_validate_assets` (`:638-684`). Directly observed.
- `cardiff/src/cardiff/paths.py`: `normalize_approved_asset_roots`. Directly observed.
- `cardiff/src/cardiff/rendering/templates.py`: `_resolve_asset_reference` (`:383-407`), the render-time counterpart, which uses `Path.is_absolute()` only. Directly observed.
- `cardiff/tests/contract/test_security.py`: `test_parent_traversal_asset_paths_are_rejected` (`:228`), `test_remote_asset_paths_are_rejected` (`:251`). Directly observed.
- `cardiff/docs/validation-contract.md`, `cardiff/docs/template-authoring.md`: the documented contract. Directly observed.

## Agent Handoff Notes

- Inspect first: `validation.py:385-395`.
- Search terms: `urlparse`, `parsed.scheme`, `^[a-zA-Z]:$`, `is_absolute`.
- Hypothesis to verify, not an instruction: the exemption intended to recognize drive letters. One option compares against `^[a-zA-Z]$`. Another checks `Path(candidate).is_absolute()` / `PureWindowsPath(candidate).drive` before the scheme test. The choice affects how `c:foo.png` (a drive-relative path) is treated, which is worth an explicit test.
- Constraints: keep remote-URL rejection, parent-traversal rejection, and the approved-root containment check exactly as strict as today.
- Assumptions to avoid:
  - Do not assume the regex was ever exercised. No test covers it.
  - Do not loosen the check for all one-letter schemes on POSIX without considering that `c:/x.png` is a relative path there.

## Acceptance Criteria

- [ ] On Windows, a backslash-form drive-letter absolute path to an existing file inside an approved root validates with no issues.
- [ ] On Windows, the forward-slash form of the same path validates with no issues.
- [ ] On Windows, a drive-letter absolute path outside every approved root returns `invalid_asset_path` with message `absolute asset paths must stay inside an approved root`.
- [ ] `https://example.com/logo.png` still returns `invalid_asset_path` with message `asset paths must be local files inside approved roots`.
- [ ] `file:///tmp/logo.png` still returns `invalid_asset_path` with message `asset paths must be local files inside approved roots`.
- [ ] A test covers an absolute asset path inside an approved root on the platform where it runs.
- [ ] A test covers an absolute asset path outside approved roots on the platform where it runs.
- [ ] `python -m pytest tests/contract -q -p no:cacheprovider` passes from `cardiff/`.

## Test / Verification Plan

Existing tests to run (from `README.md` and `.github/workflows/ci.yml`; recommended, not run as part of issue authoring):
- `python -m pytest tests/contract -q -p no:cacheprovider`
- `python -m pytest tests/cli -q -p no:cacheprovider`

New tests likely needed:
- In `cardiff/tests/contract/test_security.py`: absolute-path inside and outside approved roots, built from `Path(...).resolve()` so they are valid on the running platform. Optionally add a Windows-only case marked with `pytest.mark.skipif(sys.platform != "win32", ...)`.

Manual checks:
- On Windows, `python -m cardiff validate` on a request whose `assets.logo` is an absolute path inside `--approved-asset-root` exits `0`.

Regression checks:
- `test_parent_traversal_asset_paths_are_rejected` and `test_remote_asset_paths_are_rejected` still pass.

Security checks:
- Confirm `file:`, `http:`, `https:`, and other multi-letter schemes are still rejected.
- Confirm drive-letter paths outside approved roots are still rejected.

## Implementation Boundaries

- Non-goals: adding UNC support; changing render-time resolution; changing allowed extensions.
- Forbidden shortcuts:
  - Do not remove the scheme check.
  - Do not skip the approved-root containment check for absolute paths.
- Compatibility: behavior on Linux and macOS must not change for any input.
- Contracts to preserve: `ValidationCode.INVALID_ASSET_PATH` and the existing message strings.
- Project conventions: security-relevant validation tests live in `cardiff/tests/contract/test_security.py`.

## Risks and Review Focus

- Security: the asset-path guard is a trust boundary. Review check: the tests listed above include at least one URL scheme and one out-of-root absolute path that must still be rejected.
- Regression: POSIX behavior. Review check: CI on Ubuntu stays green with no changed expectations.
- Observability: CI cannot exercise Windows today. Review check: decide whether a Windows CI leg is needed (see Open Questions).

## Work Mapping

User-provided context (audit reproduction on Windows) -> `cardiff/src/cardiff/contract/validation.py` -> Acceptance Criteria above -> Test / Verification Plan above.

## Open Questions

- Maintainer or ops, non-blocking: should CI add a `windows-latest` leg so Windows-only path behavior is exercised?
- Maintainer, non-blocking: should UNC paths inside an approved UNC root be supported? Today they would fall through to the relative-path branch or the scheme check, depending on form. This was not tested in the audit.

## Definition of Done

- [ ] code change is scoped to the in-scope list
- [ ] all acceptance criteria are observably met
- [ ] tests in the verification plan are added or updated and passing
- [ ] documentation, ADRs, or runbooks updated when the change requires it
- [ ] reviewer focus areas from the risk section are addressed
- [ ] work-mapping links are populated
- [ ] blocker/dependency status is resolved or explicitly carried forward
- [ ] issue is closed with a brief evidence summary referencing the verifying tests, commands, or screenshots
