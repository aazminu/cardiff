# [BUG] [rev] Template manifest required_identity_fields is parsed but never enforced

## Summary

Template manifests can declare `required_identity_fields`. The loader type-checks the field and stores it on `TemplateDescriptor`, but no code reads it afterwards. A template that declares, for example, `phone` as required still renders a request that has no phone, and reports success. Template authors are told to treat the manifest as the source of truth for template-specific support, so a declared-but-ignored requirement is misleading. The desired outcome is that a manifest-declared required identity field is enforced before compilation, or that the field is explicitly documented as informational. Which of the two, and with which failure class, is a maintainer decision.

## Issue Type

Primary type: bug

Labels:
- `bug` (pre-existing)
- `question` (pre-existing)
- `help wanted` (pre-existing)
- `for experienced devs` (pre-existing)

Secondary types: none.

## Readiness Grade

HUMAN_READY_BUT_AGENT_NEEDS_CONTEXT

The gap was reproduced during the pre-issue audit. A template copy that requires `phone` rendered the phone-less sample request successfully. A source search shows no consumer of the field. A maintainer can act on this immediately. A coding agent, however, needs a decision first: whether to enforce the field or document it as informational, and if enforcing, which `RenderFailureClass` to use. Adding a class is a public-contract change. That decision is recorded as a blocking open question.

## Source Context

Path-scoped context in the current repository: `cardiff/src/cardiff/rendering/templates.py`, with supporting reads of `cardiff/src/cardiff/rendering/models.py`, `cardiff/src/cardiff/rendering/pipeline.py`, `cardiff/src/cardiff/templates/business-card/manifest.json`, `cardiff/docs/render-pipeline.md`, and `cardiff/docs/template-authoring.md`, plus reporter-supplied reproduction evidence from a pre-issue audit.

## Detection Context

Detected in branch: `rev`

GitHub repository: zcalifornia-ph/cardiff

Local artifact path: `docs/issues/issue-bug-cardiff-src-cardiff-rendering-templates.md`

Audited at commit `3a29f30`.

## Blockers and Dependencies

No blockers identified from the loaded evidence. Implementation should wait for the maintainer answer to the blocking open question below.

No GitHub issue dependency was attached.

## Scope

In scope:
- Behavior of `required_identity_fields` from `manifest.json` during rendering.
- Tests that cover a manifest requiring an identity field the request lacks.
- Documentation of the field in `cardiff/docs/render-pipeline.md` and `cardiff/docs/template-authoring.md`.

Out of scope:
- Changing the canonical request contract's own required fields (`full_name`, `role`, `email`).
- Validating that manifest-listed names are known identity fields (see Open Questions).
- Template layout or the bundled template's field list.

## Current / Observed Behavior

Observed during the pre-issue audit:
1. `cardiff/src/cardiff/templates/business-card/` was copied to a scratch template root, and `"phone"` was added to `required_identity_fields` in the copy's `manifest.json`.
2. From `cardiff/`, `python -m cardiff render tests/fixtures/requests/valid-request.yaml --approved-asset-root tests/fixtures/approved-assets --template-root <scratch-tpl-root> --output <scratch-dir>/reqfields.pdf --deterministic` printed `"status": "succeeded"` and exited `0`.
3. `tests/fixtures/requests/valid-request.yaml` contains no `phone` field.

Code evidence (directly observed):
- `cardiff/src/cardiff/rendering/templates.py:356` parses `required_identity_fields` with a default of `["full_name", "role", "email"]` and validates it as a list of strings. `:369` stores it on the descriptor.
- `cardiff/src/cardiff/rendering/models.py:269` declares `TemplateDescriptor.required_identity_fields`, and `:292` serializes it in `to_dict`.
- `cardiff/src/cardiff/rendering/templates.py:273-278` enforces `supported_variants`, and `:306-316` enforces `required_asset_slots`. There is no equivalent check for identity fields.
- A search of `cardiff/src` for `required_identity_fields` found only the parse, store, and serialize sites above.
- `cardiff/src/cardiff/templates/business-card/manifest.json` declares `required_identity_fields: ["full_name", "role", "email"]`, the same as the contract's required fields, so the bundled template does not expose the gap.
- `cardiff/docs/render-pipeline.md` (Template Directory Contract) lists manifest contents as metadata, page geometry, supported variants, and required asset slots, without identity fields. `cardiff/docs/template-authoring.md` says contributors "should treat the manifest as the final source of truth for template-specific support".

## Expected / Target Behavior

If enforcement is chosen (recommended):
- Rendering a request that lacks a manifest-required identity field stops before TeX compilation.
- The result has `status` `failed`, a stable failure class, a diagnostic naming the missing field, and no PDF written.

If informational is chosen instead:
- The docs state that the field is informational and not enforced, and nothing else changes.

## Reproduction Steps or Validation Steps

Preconditions: dependencies installed per `README.md`; working directory `cardiff/`; `<scratch-dir>` is a writable directory outside the repository.

1. Copy `src/cardiff/templates/business-card/` to `<scratch-dir>/tpl/business-card/`.
2. In the copy's `manifest.json`, set `"required_identity_fields": ["full_name", "role", "email", "phone"]`.
3. Run `python -m cardiff render tests/fixtures/requests/valid-request.yaml --approved-asset-root tests/fixtures/approved-assets --template-root <scratch-dir>/tpl --output <scratch-dir>/out.pdf --deterministic`.
4. Failing observation: exit `0` and `"status": "succeeded"`, although the request has no `phone`.

## Environment and Evidence

- Operating system: Windows 11 (audit machine). The defect is platform-independent by code inspection.
- Runtime: Python 3.14.0.
- CLI outcome: quoted in Current / Observed Behavior. Local paths are omitted.

## Relevant Files, Symbols, and Tests

- `cardiff/src/cardiff/rendering/templates.py`: `_load_descriptor` (`:321-371`), `resolve_template` (`:242-292`), `resolve_asset_paths` (`:295-318`). Directly observed.
- `cardiff/src/cardiff/rendering/models.py`: `TemplateDescriptor`, `RenderFailureClass` (`:234-243`). Directly observed.
- `cardiff/src/cardiff/rendering/pipeline.py`: `render_request_to_pdf` (`:248-372`). Directly observed.
- `cardiff/src/cardiff/templates/business-card/manifest.json`. Directly observed.
- `cardiff/tests/rendering/test_template_resolution.py`: the existing manifest and resolution tests, where new cases would live. Location is inferred from the file name and was not read in full.
- `cardiff/docs/render-pipeline.md`, `cardiff/docs/template-authoring.md`. Directly observed.

## Agent Handoff Notes

- Inspect first: `resolve_asset_paths`, the existing pattern for enforcing a manifest requirement before compile, and `RenderFailureClass`.
- Search terms: `required_identity_fields`, `required_asset_slots`, `TEMPLATE_ASSET_MISSING`, `RenderFailureClass`.
- Hypothesis to verify, not an instruction: a check placed next to `resolve_asset_paths` in `render_request_to_pdf` (before `output.parent.mkdir`) would mirror how missing assets fail today.
- Constraints: `RenderFailureClass` string values are part of the CLI JSON contract (`failure_class`). Adding or reusing a value is a public decision. Do not pick one without the maintainer's answer.
- Assumptions to avoid: do not reuse `template_manifest_invalid`. The manifest is valid; the request is what lacks the field.

## Acceptance Criteria

These assume the recommended enforcement option. Replace them with a single documentation criterion if the informational option is chosen.

- [ ] Rendering a request missing a manifest-required identity field returns `status` `failed`.
- [ ] That failure happens before the adapter's `compile` is called.
- [ ] No PDF is written at the requested output path for that failure.
- [ ] The failure diagnostics name the missing field, for example `identity.phone`.
- [ ] The failure class is the value agreed in Open Questions.
- [ ] `cardiff/docs/render-pipeline.md` documents `required_identity_fields` and the failure class.
- [ ] The sample request still renders with the bundled `business-card` manifest.

## Test / Verification Plan

Existing tests to run (from `README.md` and `.github/workflows/ci.yml`; recommended, not run as part of issue authoring):
- `python -m pytest tests/rendering -q -p no:cacheprovider`
- `python -m pytest tests/cli -q -p no:cacheprovider`

New tests likely needed:
- In `cardiff/tests/rendering/`: a temporary template whose manifest requires `phone`, rendered with a compile-tracking adapter. Assert failure, no compile call, and the diagnostic text. `CompileTrackingAdapter` in `cardiff/tests/rendering/test_pipeline.py` is a usable pattern.

Regression checks:
- Deterministic sample render and reference-evidence comparison are unchanged.

## Implementation Boundaries

- Non-goals: changing contract-level required fields; adding new identity fields.
- Forbidden shortcuts: do not move the check into contract validation. Validation runs before a template is resolved, and it must stay template-agnostic.
- Compatibility: manifests without `required_identity_fields` keep the current default.
- Contracts to preserve: existing `RenderFailureClass` values and CLI exit code `3` for render failures.
- Project conventions: rendering tests under `cardiff/tests/rendering/`.

## Risks and Review Focus

- API compatibility: a new failure class changes the set of values CLI consumers may see. Review check: the docs and the PR description list the new value.
- Correctness: the field-name mapping between manifest entries and `IdentityProfile` attributes, for example `address_lines` being a tuple. Review check: tests cover a scalar field and `address_lines`.

## Work Mapping

User-provided context (audit reproduction with a modified template copy) -> `cardiff/src/cardiff/rendering/templates.py`, `cardiff/src/cardiff/rendering/pipeline.py`, `cardiff/src/cardiff/rendering/models.py` -> Acceptance Criteria above -> Test / Verification Plan above.

## Open Questions

- Maintainer, blocking: should `required_identity_fields` be enforced at render time or documented as informational? If enforced, should it use a new `RenderFailureClass` value (for example `template_field_missing`) or an existing one? The recommendation is to enforce it with a new, documented value.
- Maintainer, non-blocking: should manifests that list unknown identity field names be rejected as `template_manifest_invalid`?

## Definition of Done

- [ ] code change is scoped to the in-scope list
- [ ] all acceptance criteria are observably met
- [ ] tests in the verification plan are added or updated and passing
- [ ] documentation, ADRs, or runbooks updated when the change requires it
- [ ] reviewer focus areas from the risk section are addressed
- [ ] work-mapping links are populated
- [ ] blocker/dependency status is resolved or explicitly carried forward
- [ ] issue is closed with a brief evidence summary referencing the verifying tests, commands, or screenshots
