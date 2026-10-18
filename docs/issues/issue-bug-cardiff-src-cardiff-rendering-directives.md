# [BUG] [rev] QR vCard payload contains LaTeX escape sequences from sanitized identity fields

## Summary

The QR code embeds a vCard built from the validated identity, but validation stores identity text already LaTeX-escaped. Any `&`, `%`, `$`, `#`, `_`, `{`, `}`, `~`, or `^` in a name, role, email, website, organization, or address therefore reaches the scanned contact as a TeX escape. For example, `ada_lovelace@example.com` becomes `ada\_lovelace@example.com`, which is not the user's address. The tests construct identities directly and never pass through validation, so they do not catch this. The desired outcome is that the vCard carries the user's original text while the TeX output stays escaped.

## Issue Type

Primary type: bug

Labels:
- `bug` (pre-existing)
- `for experienced devs` (pre-existing)

Secondary types: none.

## Readiness Grade

AGENT_READY

The corrupted vCard was reproduced during the pre-issue audit with a short script that uses only public APIs (`validate_render_request`, `build_vcard`). The escaping step and the vCard builder are directly observed in the cited lines. Acceptance criteria are exact string checks. The design question of where to separate raw and escaped text is non-blocking, because every acceptable design must satisfy the same checks.

## Source Context

Path-scoped context in the current repository: `cardiff/src/cardiff/rendering/directives.py`, with supporting reads of `cardiff/src/cardiff/contract/validation.py`, `cardiff/src/cardiff/contract/sanitization.py`, `cardiff/src/cardiff/rendering/pipeline.py`, and `cardiff/tests/rendering/test_directives.py`, plus reporter-supplied reproduction evidence from a pre-issue audit.

## Detection Context

Detected in branch: `rev`

GitHub repository: zcalifornia-ph/cardiff

Local artifact path: `docs/issues/issue-bug-cardiff-src-cardiff-rendering-directives.md`

Audited at commit `3a29f30`.

## Blockers and Dependencies

No blockers identified from the loaded evidence.

Related, not blocking: the same root cause, escaped text stored in the canonical request, also makes `sanitize_render_fields` raise on accepted requests. That defect is tracked in a separate issue filed alongside this one.

No GitHub issue dependency was attached.

## Scope

In scope:
- The vCard text produced for the QR directive when the request came through `validate_render_request` / `load_and_validate_request`.
- Regression tests that build the vCard from a validated request containing LaTeX-special characters.

Out of scope:
- Changing which characters are rejected as unsafe (`UNSAFE_TEXT_PATTERNS`).
- Changing TeX escaping of values inserted into the template.
- vCard 3.0 conformance beyond this defect, such as text-value escaping of `,` and `;` or emitting an `N` property (see Open Questions).
- QR layout, size, or placement.

## Current / Observed Behavior

Observed during the pre-issue audit. The script was run from `cardiff/`:

```python
from cardiff.contract import validate_render_request
from cardiff.rendering import build_vcard

payload = {
    "identity": {"full_name": "Ada Lovelace", "role": "R&D Lead",
                 "email": "ada_lovelace@example.com",
                 "organization": "Analytical Engine Lab, Inc.",
                 "website": "https://example.com/~ada",
                 "address_lines": ["#12 Logic St.", "London"]},
    "template": {"id": "business-card", "options": {"include_qr": True}},
}
result = validate_render_request(payload)
print(result.accepted)
print(repr(build_vcard(result.request.identity)))
```

Output:

```text
True
'BEGIN:VCARD\r\nVERSION:3.0\r\nFN:Ada Lovelace\r\nTITLE:R\\&D Lead\r\nEMAIL:ada\\_lovelace@example.com\r\nORG:Analytical Engine Lab, Inc.\r\nURL:https://example.com/\\textasciitilde{}ada\r\nADR:;;\\#12 Logic St., London;;;;\r\nEND:VCARD'
```

Code evidence (directly observed):
- `cardiff/src/cardiff/contract/validation.py:784-796`: `_validate_text_field` returns `sanitize_text(normalized, ...)`, and that escaped value is what gets stored on `IdentityProfile` (`:310-316`).
- `cardiff/src/cardiff/contract/sanitization.py:224-234` (`LATEX_ESCAPE_MAP`) and `:270-273` perform the escaping.
- `cardiff/src/cardiff/rendering/pipeline.py:304-310` passes `render_request.identity` to `resolve_qr_directives`.
- `cardiff/src/cardiff/rendering/directives.py:305-306` calls `build_vcard(identity)`, then `generate_qr_png`. `build_vcard` (`:231-255`) concatenates fields verbatim.
- `cardiff/tests/rendering/test_directives.py:234-242` (`_make_identity`) and `:251-282` (`TestBuildVcard`) construct `IdentityProfile` directly with plain values, so the validated-input path is untested.

Related observation (inferred from code, not run): `_build_preview_lines` (`cardiff/src/cardiff/rendering/pipeline.py:417-438`) also reads the escaped identity values. The deterministic preview PDF would therefore show text such as `R\&D Lead`.

## Expected / Target Behavior

For the request above, the vCard contains `TITLE:R&D Lead`, `EMAIL:ada_lovelace@example.com`, `URL:https://example.com/~ada`, and an `ADR` street component starting with `#12 Logic St.`. The TeX inserted into the template for the same request still contains the escaped forms (for example `R\&D Lead`).

## Reproduction Steps or Validation Steps

Preconditions: dependencies installed per `README.md` (`python -m pip install -e ".[dev]"`); working directory `cardiff/`.

1. Run the script in Current / Observed Behavior.
2. Observe that `True` is printed (the request is accepted).
3. Observe that the vCard string contains `TITLE:R\&D Lead`.
4. Failing observation: the vCard string contains `EMAIL:ada\_lovelace@example.com` instead of `EMAIL:ada_lovelace@example.com`.

## Environment and Evidence

- Operating system: Windows 11 (audit machine). The defect is platform-independent by code inspection.
- Runtime: Python 3.14.0; PyYAML 6.0.3; segno 1.6.6.
- Script output: quoted in Current / Observed Behavior.
- Actual phone-scanner behavior with the generated QR image: Not provided / not verified.

## Relevant Files, Symbols, and Tests

- `cardiff/src/cardiff/rendering/directives.py`: `build_vcard` (`:231-255`), `resolve_qr_directives` (`:288-311`). Directly observed.
- `cardiff/src/cardiff/contract/validation.py`: `_validate_text_field` (`:722-796`), `validate_render_request` (`:263-317`). Directly observed.
- `cardiff/src/cardiff/contract/sanitization.py`: `LATEX_ESCAPE_MAP`, `sanitize_text`. Directly observed.
- `cardiff/src/cardiff/rendering/pipeline.py`: `render_request_to_pdf` QR branch (`:299-317`), `_build_placeholder_values` (`:375-396`), `_build_preview_lines` (`:417-438`). Directly observed.
- `cardiff/src/cardiff/contract/models.py`: `IdentityProfile` (`:270-302`), `RenderRequest.to_dict` (`:315-329`). Directly observed.
- `cardiff/tests/rendering/test_directives.py`: `TestBuildVcard`. Directly observed.
- `cardiff/tests/fixtures/approved-samples/business-card/reference-evidence.json`: its `request_fingerprint` is computed from `RenderRequest.to_dict()`. That value would change if the canonical model stops storing escaped text. Directly observed.

## Agent Handoff Notes

- Inspect first: where identity text is escaped (`_validate_text_field`) versus where it is consumed (`_build_placeholder_values` for TeX, `build_vcard` for QR, `_build_preview_lines` for the deterministic preview).
- Search terms: `sanitize_text(`, `LATEX_ESCAPE_MAP`, `build_vcard`, `render_request.identity`.
- Hypotheses to verify, not instructions:
  - Keep raw normalized text in the canonical request and apply TeX escaping only when substituting into the template. This changes `request_fingerprint` and requires regenerating `reference-evidence.json`.
  - Alternatively, keep the model as is and derive raw text for non-TeX consumers. That needs a reliable inverse of the escape map.
- Constraints: unsafe-content rejection (backslash, `{{`, `{%`, `%}`) must still happen at validation time. The TeX output must stay escaped.
- Assumptions to avoid: do not "fix" this by stripping backslashes in `build_vcard`. That would hide the issue for `\&` but leave `\textasciitilde{}` and `\textasciicircum{}` corrupted.

## Acceptance Criteria

- [ ] For a request accepted by `validate_render_request` with email `ada_lovelace@example.com`, the QR vCard text contains `EMAIL:ada_lovelace@example.com`.
- [ ] For the same path with role `R&D Lead`, the vCard text contains `TITLE:R&D Lead`.
- [ ] For the same path with website `https://example.com/~ada`, the vCard text contains `URL:https://example.com/~ada`.
- [ ] The vCard text for that request contains no `\textasciitilde{}` substring.
- [ ] The rendered TeX for the same request still contains `R\&D Lead`.
- [ ] A test builds the vCard from a request that passed validation and contains at least `&`, `_`, and `~`.
- [ ] `python -m pytest tests -q -p no:cacheprovider` passes from `cardiff/`.

## Test / Verification Plan

Existing tests to run (from `README.md` and `.github/workflows/ci.yml`; recommended, not run as part of issue authoring):
- `python -m pytest tests/rendering -q -p no:cacheprovider`
- `python -m pytest tests/contract -q -p no:cacheprovider`
- `python -m pytest tests/cli -q -p no:cacheprovider`

New tests likely needed:
- In `cardiff/tests/rendering/test_directives.py`: a vCard test whose identity comes from `validate_render_request`.
- In `cardiff/tests/rendering/test_pipeline.py`: a QR-enabled render with `FakeNonDeterministicAdapter` that captures the data passed to `generate_qr_png` (the existing test already patches it) and asserts the raw email.

Manual checks:
- Optionally decode the generated QR PNG with a scanner app and confirm the email field.

Regression checks:
- `tests/contract/test_security.py::test_seeded_latex_commands_are_rejected` still passes.
- The reference-evidence comparison passes after any intentional regeneration.

Security checks:
- Seeded TeX commands in any identity field are still rejected before rendering.

## Implementation Boundaries

- Non-goals: vCard 4.0 migration; new identity fields; QR payload policy work.
- Forbidden shortcuts:
  - Do not disable escaping for the TeX path.
  - Do not widen `UNSAFE_TEXT_PATTERNS` exemptions.
  - Do not silently regenerate reference evidence without noting the fingerprint change in the PR.
- Compatibility: the public API names exported from `cardiff` and `cardiff.contract` stay available.
- Contracts to preserve: `ValidationCode` values; the CLI JSON payload shape; normalized-evidence field names.
- Project conventions: tests under `cardiff/tests/`; fixtures under `cardiff/tests/fixtures/`.

## Risks and Review Focus

- Security: moving escaping later must not let unescaped text reach TeX. Review check: every value inserted by `_render_template_source` is escaped exactly once.
- Data compatibility: `request_fingerprint` may change. Review check: the `reference-evidence.json` diff and PR description explain the change.
- Correctness: double escaping or missed escaping. Review check: tests assert both the vCard (raw) and the rendered TeX (escaped) for the same input.

## Work Mapping

User-provided context (audit reproduction via public APIs) -> `cardiff/src/cardiff/rendering/directives.py`, `cardiff/src/cardiff/contract/validation.py`, `cardiff/src/cardiff/rendering/pipeline.py` -> Acceptance Criteria above -> Test / Verification Plan above.

## Open Questions

- Maintainer, non-blocking: should the canonical request keep raw text, with escaping at the TeX boundary, or keep escaped text, with non-TeX consumers deriving raw text? The first option is cleaner but changes `request_fingerprint`.
- Maintainer, non-blocking: should vCard 3.0 conformance gaps be tracked as a follow-up? These are text-value escaping of `,` and `;` (for example `ORG:Analytical Engine Lab, Inc.`) and the `N` property, which the vCard 3.0 specification (RFC 2426) requires. They were not verified against a scanner during the audit.

## Definition of Done

- [ ] code change is scoped to the in-scope list
- [ ] all acceptance criteria are observably met
- [ ] tests in the verification plan are added or updated and passing
- [ ] documentation, ADRs, or runbooks updated when the change requires it
- [ ] reviewer focus areas from the risk section are addressed
- [ ] work-mapping links are populated
- [ ] blocker/dependency status is resolved or explicitly carried forward
- [ ] issue is closed with a brief evidence summary referencing the verifying tests, commands, or screenshots
