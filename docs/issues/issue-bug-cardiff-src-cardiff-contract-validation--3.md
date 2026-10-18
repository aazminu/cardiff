# [BUG] [rev] Request validation crashes with TypeError on non-string YAML mapping keys

## Summary

PyYAML turns keys such as `1`, `on`, `yes`, or `null` into non-string Python values. When such a key appears at the top level of a request and any other issue is present, or appears anywhere under `assets`, validation sorts mixed `int`/`str` values and raises `TypeError`. The CLI then prints a Python traceback, emits no JSON status line, and exits `1`. Exit code `1` is the code documented for "canonical validation rejected the request", so a crash is indistinguishable from a rejection by exit code alone. The desired outcome is a structured rejection with string field names.

## Issue Type

Primary type: bug

Labels:
- `bug` (pre-existing)
- `good first issue` (pre-existing)
- `light work` (pre-existing)

Secondary types: none.

## Readiness Grade

AGENT_READY

Two crash paths were reproduced with the CLI during the pre-issue audit, and the failing sort calls are directly observed at the cited lines. Inputs are tiny YAML files that can be recreated exactly. Acceptance criteria are CLI-observable. No open question blocks the fix.

## Source Context

Path-scoped context in the current repository: `cardiff/src/cardiff/contract/validation.py`, with supporting reads of `cardiff/src/cardiff/contract/models.py`, `cardiff/src/cardiff/cli.py`, and `cardiff/docs/cli-quickstart.md`, plus reporter-supplied reproduction evidence from a pre-issue audit.

## Detection Context

Detected in branch: `rev`

GitHub repository: zcalifornia-ph/cardiff

Local artifact path: `docs/issues/issue-bug-cardiff-src-cardiff-contract-validation--3.md`

Audited at commit `3a29f30`.

## Blockers and Dependencies

No blockers identified from the loaded evidence.

No GitHub issue dependency was attached.

## Scope

In scope:
- Validation of request mappings whose keys are not strings, at the top level and inside `identity`, `template`, `template.options`, and `assets`.
- Tests for those cases.

Out of scope:
- Switching YAML loaders or YAML versions.
- Catch-all exception handling in the CLI. A separate encoding issue covers loader crashes.
- Changing the set of supported fields.

## Current / Observed Behavior

Observed during the pre-issue audit, with commands run from `cardiff/`.

Case A, a top-level non-string key plus a missing `identity`:

```yaml
1: stray
template:
  id: business-card
```

`python -m cardiff validate <case-a>.yaml` printed a traceback ending in:

```text
    return tuple(sorted(issues, key=lambda issue: (issue.field, issue.code, issue.message)))
TypeError: '<' not supported between instances of 'str' and 'int'
```

The process exited `1` with nothing on stdout.

Case B, a non-string key inside `assets`:

```yaml
identity:
  full_name: A
  role: B
  email: a@b.c
template:
  id: business-card
assets:
  1: x.png
  logo: brand/logo.png
```

`python -m cardiff validate <case-b>.yaml --approved-asset-root tests/fixtures/approved-assets` printed a traceback ending in `TypeError: '<' not supported between instances of 'str' and 'int'` and exited `1`.

Non-string keys nested under `identity` and `template.options` (`1:` and `on:`) did not crash. They were reported as `identity.1` and `template.options.True` because those field names are built with f-strings.

Code evidence (directly observed):
- `cardiff/src/cardiff/contract/validation.py:285-293`: top-level unknown keys are sorted (`sorted(set(payload) - TOP_LEVEL_FIELDS)`) and stored with `field=field`, which is the raw key and not a string.
- `cardiff/src/cardiff/contract/validation.py:799-800`: `_finalize_issues` sorts by `(issue.field, ...)`, which fails when a raw `int` field sits next to a `str` field.
- `cardiff/src/cardiff/contract/validation.py:655`: `_validate_assets` runs `for slot in sorted(payload):` on raw keys.
- `cardiff/src/cardiff/contract/models.py:239-245`: `ValidationIssue.field` is annotated `str`.
- `cardiff/docs/cli-quickstart.md` (Exit Codes) documents `1` as "canonical validation rejected the request". `cardiff/src/cardiff/cli.py:309-314` (`main`) has no exception handling around the handlers.

## Expected / Target Behavior

- Case A and Case B are rejected with structured issues, exit `1`, and one JSON status object on stdout with `"status": "rejected"`.
- Every `ValidationIssue.field` value is a `str`. For example, the top-level key `1` is reported as `"1"`.
- No traceback is printed for any YAML mapping key type that `yaml.safe_load` can produce.

## Reproduction Steps or Validation Steps

Preconditions: dependencies installed per `README.md`; working directory `cardiff/`; `<scratch-dir>` is a writable directory outside the repository.

1. Write the Case A YAML above to `<scratch-dir>/case-a.yaml`.
2. Run `python -m cardiff validate <scratch-dir>/case-a.yaml`.
3. Observe the process exit code is `1`.
4. Failing observation: stdout is empty and stderr ends with `TypeError: '<' not supported between instances of 'str' and 'int'`.

## Environment and Evidence

- Operating system: Windows 11 (audit machine). The defect is platform-independent by code inspection.
- Runtime: Python 3.14.0; PyYAML 6.0.3. PyYAML resolves `on`/`yes` to booleans under YAML 1.1 rules, which matches the `template.options.True` output observed.
- Traceback tail: quoted in Current / Observed Behavior. Local paths are omitted.

## Relevant Files, Symbols, and Tests

- `cardiff/src/cardiff/contract/validation.py`: `validate_render_request` (`:263-317`), `_validate_identity` (`:449-507`), `_validate_template` (`:510-635`), `_validate_assets` (`:638-684`), `_finalize_issues` (`:799-800`). Directly observed.
- `cardiff/src/cardiff/contract/models.py`: `ValidationIssue`. Directly observed.
- `cardiff/src/cardiff/cli.py`: `main`, `run_validate`, `run_render`. Directly observed.
- `cardiff/tests/contract/test_validation.py`: existing validation tests; none cover non-string keys. Directly observed by search.

## Agent Handoff Notes

- Inspect first: the three places that sort or store raw keys, at `validation.py:285-293`, `:655`, and `:799-800`.
- Search terms: `sorted(set(payload)`, `sorted(payload)`, `field=field`, `_finalize_issues`.
- Hypothesis to verify, not an instruction: converting keys to `str` before comparison and before storing them in `ValidationIssue.field` would remove both crash paths. Decide whether a non-string key that equals a supported name after `str()` (for example a YAML key that loads as a non-string) should still be rejected as `unknown_field`.
- Constraints: `ValidationCode` values and the CLI JSON payload shape are public contracts.
- Assumptions to avoid: JSON input cannot produce non-string keys, so JSON-only tests will not catch this.

## Acceptance Criteria

- [ ] Case A exits `1`.
- [ ] Case A prints exactly one JSON object on stdout with `"status": "rejected"`.
- [ ] Case A's JSON `issues` include an `unknown_field` issue whose `field` is the string `"1"`.
- [ ] Case B exits `1` with a JSON status object whose `status` is `"rejected"`.
- [ ] Neither case prints `Traceback` on stderr.
- [ ] Every `ValidationIssue.field` returned by `validate_render_request` for a payload with integer, boolean, and null keys is a `str`.
- [ ] Tests cover non-string keys at the top level, in `identity`, in `template.options`, and in `assets`.

## Test / Verification Plan

Existing tests to run (from `README.md` and `.github/workflows/ci.yml`; recommended, not run as part of issue authoring):
- `python -m pytest tests/contract -q -p no:cacheprovider`
- `python -m pytest tests/cli -q -p no:cacheprovider`

New tests likely needed:
- In `cardiff/tests/contract/test_validation.py`: parametrized YAML payloads with `1:`, `on:`, and `null:` keys at each level.
- In `cardiff/tests/cli/test_cli.py`: one CLI case asserting the JSON payload and exit code for Case A.

Regression checks:
- Existing unknown-field tests keep their exact field names and ordering for string keys.

## Implementation Boundaries

- Non-goals: YAML 1.2 migration; accepting non-string keys as valid.
- Forbidden shortcuts:
  - Do not wrap validation in a broad `except Exception`.
  - Do not drop non-string keys silently.
- Compatibility: issue ordering for string-keyed payloads must stay deterministic and unchanged.
- Contracts to preserve: `ValidationCode` values; JSON status payload fields; CLI exit codes `0`-`4`.
- Project conventions: contract tests in `cardiff/tests/contract/`, CLI tests in `cardiff/tests/cli/`.

## Risks and Review Focus

- Regression: deterministic issue ordering. Review check: existing tests that assert issue order still pass unchanged.
- Correctness: a stringified key could collide with a supported field name. Review check: a test with a key that stringifies to a supported name confirms the agreed behavior.

## Work Mapping

User-provided context (audit CLI reproduction) -> `cardiff/src/cardiff/contract/validation.py` -> Acceptance Criteria above -> Test / Verification Plan above.

## Open Questions

- Maintainer, non-blocking: should a non-string key whose `str()` matches a supported field (for example a numeric-looking key) be rejected as `unknown_field` or `invalid_type`? The recommended default is `unknown_field`, which matches the current nested-field behavior.

## Definition of Done

- [ ] code change is scoped to the in-scope list
- [ ] all acceptance criteria are observably met
- [ ] tests in the verification plan are added or updated and passing
- [ ] documentation, ADRs, or runbooks updated when the change requires it
- [ ] reviewer focus areas from the risk section are addressed
- [ ] work-mapping links are populated
- [ ] blocker/dependency status is resolved or explicitly carried forward
- [ ] issue is closed with a brief evidence summary referencing the verifying tests, commands, or screenshots
