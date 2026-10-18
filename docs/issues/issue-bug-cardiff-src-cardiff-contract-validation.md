# [BUG] [rev] sanitize_render_fields raises UnsafeContentError on accepted requests containing LaTeX-special characters

## Summary

`sanitize_render_fields` is exported from both `cardiff` and `cardiff.contract` and documented as applying "the canonical sanitization rules to an already-typed request". However, `validate_render_request` already stores LaTeX-escaped text. Passing an accepted request to `sanitize_render_fields` re-runs `sanitize_text`, which treats the backslash it produced as unsafe content. As a result, any accepted request containing `&`, `%`, `$`, `#`, `_`, `{`, `}`, `~`, or `^` makes the function raise `UnsafeContentError`. Nothing in the package calls the function and no test covers it. The desired outcome is that the function can be applied to an accepted request without raising and without escaping text twice.

## Issue Type

Primary type: bug

Labels:
- `bug` (pre-existing)
- `for experienced devs` (pre-existing)

Secondary types: none.

## Readiness Grade

AGENT_READY

The exception was reproduced during the pre-issue audit with public APIs only. The double-escape path is directly observed in `validation.py` and `sanitization.py`. Acceptance criteria are exact return-value and exception checks. The open design question about the function's intended input is non-blocking, because the stated criteria hold under either design.

## Source Context

Path-scoped context in the current repository: `cardiff/src/cardiff/contract/validation.py`, with supporting reads of `cardiff/src/cardiff/contract/sanitization.py`, `cardiff/src/cardiff/contract/__init__.py`, and `cardiff/src/cardiff/__init__.py`, plus reporter-supplied reproduction evidence from a pre-issue audit.

## Detection Context

Detected in branch: `rev`

GitHub repository: zcalifornia-ph/cardiff

Local artifact path: `docs/issues/issue-bug-cardiff-src-cardiff-contract-validation.md`

Audited at commit `3a29f30`.

## Blockers and Dependencies

No blockers identified from the loaded evidence.

Related, not blocking: the QR vCard escape-leak issue filed alongside this one has the same root cause, escaped text stored in the canonical request. A fix for either should be checked against the other.

No GitHub issue dependency was attached.

## Scope

In scope:
- `sanitize_render_fields` behavior when given a request returned by `validate_render_request` / `load_and_validate_request`.
- Tests for `sanitize_render_fields` on validated requests and on directly constructed requests.
- The function's docstring, so it states the expected input.

Out of scope:
- Changing `UNSAFE_TEXT_PATTERNS` or `LATEX_ESCAPE_MAP`.
- Changing which fields `validate_render_request` accepts.
- Wiring `sanitize_render_fields` into the render pipeline (see Open Questions).

## Current / Observed Behavior

Observed during the pre-issue audit. The script was run from `cardiff/`:

```python
from cardiff.contract import validate_render_request, sanitize_render_fields

result = validate_render_request({
    "identity": {"full_name": "Ada Lovelace", "role": "R&D Lead",
                 "email": "ada_lovelace@example.com"},
    "template": {"id": "business-card"},
})
print(result.accepted)
sanitize_render_fields(result.request)
```

Output, with the traceback trimmed to its repository frames:

```text
True
Traceback (most recent call last):
  File "cardiff/src/cardiff/contract/validation.py", line 326, in sanitize_render_fields
    role=sanitize_text(identity.role, field_name="identity.role"),
  File "cardiff/src/cardiff/contract/sanitization.py", line 266, in sanitize_text
    raise UnsafeContentError(
cardiff.contract.sanitization.UnsafeContentError: identity.role contains unsafe template or LaTeX control content
```

Code evidence (directly observed):
- `cardiff/src/cardiff/contract/validation.py:784-796`: validation stores `sanitize_text(...)` output, so `R&D Lead` becomes `R\&D Lead`.
- `cardiff/src/cardiff/contract/validation.py:320-361`: `sanitize_render_fields` calls `sanitize_text` again on every identity field and string option.
- `cardiff/src/cardiff/contract/sanitization.py:236-241`: `UNSAFE_TEXT_PATTERNS` rejects any backslash (`re.compile(r"\\")`), and `:264-268` raises `UnsafeContentError`.
- `cardiff/src/cardiff/contract/__init__.py` and `cardiff/src/cardiff/__init__.py` both export `sanitize_render_fields` in `__all__`.
- A search of `cardiff/src` found no call site other than these exports. A search of `cardiff/tests` found no reference to `sanitize_render_fields`.

## Expected / Target Behavior

- `sanitize_render_fields(accepted_request)` returns a `RenderRequest` and does not raise for text that validation accepted.
- TeX-facing text in the returned request is escaped exactly once. For example, role `R&D Lead` yields `R\&D Lead`, not a doubled backslash.
- Directly constructed requests with seeded TeX control content (for example `full_name="\\input{x}"`) still raise `UnsafeContentError`.

## Reproduction Steps or Validation Steps

Preconditions: dependencies installed per `README.md` (`python -m pip install -e ".[dev]"`); working directory `cardiff/`.

1. Run the script in Current / Observed Behavior.
2. Observe `True` (the request is accepted by validation).
3. Failing observation: `sanitize_render_fields(result.request)` raises `UnsafeContentError` naming `identity.role`.

## Environment and Evidence

- Operating system: Windows 11 (audit machine). The defect is platform-independent by code inspection.
- Runtime: Python 3.14.0; PyYAML 6.0.3.
- Script output: quoted in Current / Observed Behavior.

## Relevant Files, Symbols, and Tests

- `cardiff/src/cardiff/contract/validation.py`: `sanitize_render_fields` (`:320-361`), `_validate_text_field` (`:722-796`), `_sanitize_optional_text` (`:803-806`). Directly observed.
- `cardiff/src/cardiff/contract/sanitization.py`: `UNSAFE_TEXT_PATTERNS`, `sanitize_text`, `UnsafeContentError`. Directly observed.
- `cardiff/src/cardiff/contract/__init__.py`, `cardiff/src/cardiff/__init__.py`: public exports. Directly observed.
- `cardiff/tests/contract/test_security.py`, `cardiff/tests/contract/test_models.py`, `cardiff/tests/contract/test_validation.py`: existing contract tests, none of which reference `sanitize_render_fields`. Observed by search.

## Agent Handoff Notes

- Inspect first: the contrast between `_validate_text_field` (escapes) and `sanitize_render_fields` (escapes again).
- Search terms: `sanitize_render_fields`, `sanitize_text(`, `UNSAFE_TEXT_PATTERNS`.
- Hypotheses to verify, not instructions:
  - If the canonical request is changed to hold raw text (see the related vCard issue), `sanitize_render_fields` becomes the single escape step and this defect disappears. The pipeline would then need to call it.
  - If the model keeps escaped text, the function needs to be idempotent on already-escaped input without weakening rejection of user-supplied backslashes.
- Constraints: user-supplied backslashes, `{{`, `{%`, and `%}` must stay rejected.
- Assumptions to avoid: do not make the function skip all validation for requests that "look validated". There is no marker on `RenderRequest` that distinguishes validated from directly constructed requests.

## Acceptance Criteria

- [ ] `sanitize_render_fields` applied to an accepted request with role `R&D Lead` does not raise.
- [ ] The returned request's role equals `R\&D Lead`.
- [ ] The returned request's email for input `ada_lovelace@example.com` equals `ada\_lovelace@example.com`.
- [ ] `sanitize_render_fields` applied to a directly constructed `RenderRequest` whose `full_name` is `\input{x}` raises `UnsafeContentError`.
- [ ] A test covers `sanitize_render_fields` on a validated request.
- [ ] A test covers `sanitize_render_fields` on a directly constructed request.
- [ ] `python -m pytest tests/contract -q -p no:cacheprovider` passes from `cardiff/`.

## Test / Verification Plan

Existing tests to run (from `README.md` and `.github/workflows/ci.yml`; recommended, not run as part of issue authoring):
- `python -m pytest tests/contract -q -p no:cacheprovider`
- `python -m pytest tests/rendering -q -p no:cacheprovider`

New tests likely needed:
- In `cardiff/tests/contract/test_validation.py` or `test_security.py`: the cases listed in the acceptance criteria.

Regression checks:
- `tests/contract/test_security.py::test_seeded_latex_commands_are_rejected` still passes.

Security checks:
- Fuzz a few values containing a backslash followed by a command name, and confirm they are rejected on both entry paths.

## Implementation Boundaries

- Non-goals: renaming or removing the public function; changing `ValidationCode` values.
- Forbidden shortcuts:
  - Do not catch and swallow `UnsafeContentError` inside the function.
  - Do not remove the backslash pattern from `UNSAFE_TEXT_PATTERNS`.
- Compatibility: `sanitize_render_fields` stays exported from `cardiff` and `cardiff.contract` with the same signature.
- Contracts to preserve: `RenderRequest` field names; `UnsafeContentError` as the raised type for unsafe content.
- Project conventions: contract tests live under `cardiff/tests/contract/`.

## Risks and Review Focus

- Security: an idempotency fix could let a user-supplied `\&` or `\textbf` through. Review check: tests include user-supplied backslash sequences on a directly constructed request.
- Correctness: double escaping. Review check: tests assert exact output strings, not just "does not raise".
- Maintainability: two entry points that escape differently. Review check: the docstring states which input the function expects.

## Work Mapping

User-provided context (audit reproduction via public APIs) -> `cardiff/src/cardiff/contract/validation.py`, `cardiff/src/cardiff/contract/sanitization.py` -> Acceptance Criteria above -> Test / Verification Plan above.

## Open Questions

- Maintainer, non-blocking: is `sanitize_render_fields` meant to be the render-time escape step for directly constructed requests (and so be called by the pipeline), or a public helper only? The answer decides whether the pipeline should call it, which is out of scope here.

## Definition of Done

- [ ] code change is scoped to the in-scope list
- [ ] all acceptance criteria are observably met
- [ ] tests in the verification plan are added or updated and passing
- [ ] documentation, ADRs, or runbooks updated when the change requires it
- [ ] reviewer focus areas from the risk section are addressed
- [ ] work-mapping links are populated
- [ ] blocker/dependency status is resolved or explicitly carried forward
- [ ] issue is closed with a brief evidence summary referencing the verifying tests, commands, or screenshots
