# [BUG] [rev] XeLaTeX renders leave QR images with contact data in a hidden directory beside the output

## Summary

With a non-deterministic adapter, such as the real XeLaTeX adapter the CLI picks when `xelatex` is installed, and `include_qr: true`, the pipeline writes a QR PNG to `<output-dir>/.cardiff-qr/<output-stem>-cardiff-qr.png` and never removes it. The PNG encodes a vCard with the person's name, title, email, and any phone, website, address, and pronouns. It stays on disk after both successful and failed renders. The documented quickstart commands write output into the tracked fixture tree, and the CI workflows delete that `.cardiff-qr` directory before running tests. The template-authoring guide says QR payloads with personal contact details must not be committed. The desired outcome is that QR images are written only to a render-scoped temporary location and are gone when the render returns.

## Issue Type

Primary type: bug

Labels:
- `bug` (pre-existing)
- `for experienced devs` (pre-existing)

Secondary types: none.

## Readiness Grade

AGENT_READY

The leftover files were observed during the pre-issue audit after one failed and two successful XeLaTeX renders. The code that creates the directory without cleanup is directly observed. The existing test that pins the current location is identified. Acceptance criteria are filesystem checks that can be automated with the existing fake non-deterministic adapter. No real XeLaTeX run is needed.

## Source Context

Path-scoped context in the current repository: `cardiff/src/cardiff/rendering/pipeline.py`, with supporting reads of `cardiff/src/cardiff/rendering/directives.py`, `cardiff/src/cardiff/rendering/tex.py`, `cardiff/tests/rendering/test_pipeline.py`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `cardiff/docs/cli-quickstart.md`, and `cardiff/docs/template-authoring.md`, plus reporter-supplied reproduction evidence from a pre-issue audit.

## Detection Context

Detected in branch: `rev`

GitHub repository: zcalifornia-ph/cardiff

Local artifact path: `docs/issues/issue-bug-cardiff-src-cardiff-rendering-pipeline--2.md`

Audited at commit `3a29f30`.

## Blockers and Dependencies

No blockers identified from the loaded evidence.

Related, not blocking: the XeLaTeX compile-failure issue filed alongside this one. Until it is fixed, a successful real-XeLaTeX render needs a template override. The verification below uses the fake adapter, so it does not depend on that fix.

No GitHub issue dependency was attached.

## Scope

In scope:
- Where the pipeline writes the generated QR PNG for non-deterministic adapters, and its removal after the render returns (success or failure).
- Updating the test that asserts the current `.cardiff-qr/` path in `rendered_tex`.
- New tests asserting no QR artifact remains in the output directory.

Out of scope:
- QR payload content (see the vCard escape issue filed alongside this one).
- The deterministic adapter, which writes no QR image.
- Changing the normalized evidence fields.
- CI workflow cleanup steps, which can be simplified later.

## Current / Observed Behavior

Observed during the pre-issue audit with `xelatex` on `PATH`:
1. `python -m cardiff render tests/fixtures/requests/valid-request.yaml --approved-asset-root tests/fixtures/approved-assets --output <scratch-dir>/out/real.pdf` failed with `tex_compile_failed`, a separate defect. Afterwards `<scratch-dir>/out/.cardiff-qr/real-cardiff-qr.png` (720 bytes) remained.
2. Two further renders to `<scratch-dir>/out/real2.pdf` and `real3.pdf` (the second succeeded with a template override) left `real2-cardiff-qr.png` and `real3-cardiff-qr.png` in the same `.cardiff-qr` directory.

Code evidence (directly observed):
- `cardiff/src/cardiff/rendering/pipeline.py:299-310`: for non-deterministic adapters with `include_qr`, the pipeline sets `qr_work_dir = output.parent / ".cardiff-qr"`, creates it, and calls `resolve_qr_directives(..., work_dir=qr_work_dir, qr_filename=f"{output.stem}-cardiff-qr.png")`. No later code removes the file or the directory.
- `cardiff/src/cardiff/rendering/directives.py:305-306`: the PNG content is `build_vcard(identity)`. `build_vcard` (`:231-255`) includes FN, TITLE, EMAIL, and optional ORG, TEL, URL, ADR, and pronouns.
- `cardiff/src/cardiff/rendering/tex.py:317-350`: `XeLaTeXAdapter.compile` already works inside its own `tempfile.TemporaryDirectory()` and copies out only the PDF. The QR image, however, lives outside that directory.
- `cardiff/src/cardiff/rendering/pipeline.py:294-298`: evidence uses `substitute_qr_directives(..., qr_tex_path=CARDIFF_QR_FILENAME)`, so `tex_fingerprint` does not depend on the QR file location.
- `cardiff/tests/rendering/test_pipeline.py:388` asserts `".cardiff-qr/qr-evidence-stability-cardiff-qr.png" in first.rendered_tex`, which pins the current location.
- `.github/workflows/ci.yml` and `.github/workflows/release.yml` both run `rm -rf tests/fixtures/approved-samples/business-card/.cardiff-qr` before the tests.
- `cardiff/docs/cli-quickstart.md` shows render commands with `--output tests/fixtures/approved-samples/business-card/determinism-output.pdf`. Inference: running them without `--deterministic` on a machine with `xelatex` places `.cardiff-qr/` inside the tracked fixture tree.
- `cardiff/docs/template-authoring.md` (Repository packaging boundary) says not to commit "private QR payloads, or production contact data".

## Expected / Target Behavior

- After any render returns (succeeded or failed) with a non-deterministic adapter and `include_qr: true`, the output directory contains no `.cardiff-qr` directory and no `*-cardiff-qr.png` file created by that render.
- The successful render still embeds the QR image in the compiled PDF.
- Normalized evidence (`tex_fingerprint` and the other fields) for a given request is unchanged by the relocation.

## Reproduction Steps or Validation Steps

Preconditions: dependencies installed per `README.md`; working directory `cardiff/`; `<scratch-dir>` is a writable directory outside the repository.

Without `xelatex`, as an automated validation:
1. In a test, call `render_request_to_pdf` with `FakeNonDeterministicAdapter` (`cardiff/tests/rendering/test_pipeline.py`) and a request with `include_qr: true`, writing to `tmp_path / "card.pdf"`.
2. After it returns, list `tmp_path`.
3. Pass/fail oracle: today `tmp_path / ".cardiff-qr" / "card-cardiff-qr.png"` exists (fail). After the fix it does not exist (pass).

With `xelatex` on `PATH`:
1. Run `python -m cardiff render tests/fixtures/requests/valid-request.yaml --approved-asset-root tests/fixtures/approved-assets --output <scratch-dir>/card.pdf`.
2. Failing observation: `<scratch-dir>/.cardiff-qr/card-cardiff-qr.png` exists after the command returns, whatever its exit code.

## Environment and Evidence

- Operating system: Windows 11 (audit machine).
- Runtime: Python 3.14.0; segno 1.6.6; `MiKTeX-XeTeX 4.16 (MiKTeX 25.12)`.
- Leftover file names and size: quoted in Current / Observed Behavior. Local paths are omitted.
- Decoding the leftover PNG to confirm its payload: Not provided / not verified. The payload is established from the code path (`build_vcard` → `generate_qr_png`).

## Relevant Files, Symbols, and Tests

- `cardiff/src/cardiff/rendering/pipeline.py`: `render_request_to_pdf` QR branch (`:283-317`). Directly observed.
- `cardiff/src/cardiff/rendering/directives.py`: `resolve_qr_directives` (`:288-311`), `generate_qr_png` (`:258-267`), `build_vcard` (`:231-255`). Directly observed.
- `cardiff/src/cardiff/rendering/tex.py`: `XeLaTeXAdapter.compile` (`:298-360`), `BaseTeXAdapter` (`:242-258`). Directly observed.
- `cardiff/tests/rendering/test_pipeline.py`: `FakeNonDeterministicAdapter` (`:260-282`), `test_non_deterministic_qr_renders_keep_normalized_evidence_stable` (`:361-389`), `test_qr_preprocessing_failure_is_classified_before_compilation` (`:340`). Directly observed.
- `.github/workflows/ci.yml`, `.github/workflows/release.yml`: cleanup steps. Directly observed.

## Agent Handoff Notes

- Inspect first: `pipeline.py:299-317` and how `rendered_tex` is passed to `adapter.compile`.
- Search terms: `.cardiff-qr`, `qr_work_dir`, `qr_filename`, `TemporaryDirectory`.
- Hypothesis to verify, not an instruction: create the QR in a `tempfile.TemporaryDirectory()` owned by `render_request_to_pdf`, spanning the `adapter.compile` call, and reference it by absolute path in `rendered_tex`. The image is then deleted when the context exits. The alternative of moving QR generation into the adapter would change the `BaseTeXAdapter` contract.
- Constraints: `tex_fingerprint` must keep using the location-independent `CARDIFF_QR_FILENAME` substitution. `RenderResult.rendered_tex` may legitimately point at a now-deleted temp path. Decide whether that is acceptable (see Open Questions).
- Assumptions to avoid: the `.cardiff-qr` location is not a documented public contract. It is pinned only by the test at `test_pipeline.py:388`, which needs updating.

## Acceptance Criteria

- [ ] After a successful `render_request_to_pdf` call with `FakeNonDeterministicAdapter` and `include_qr: true`, the output directory contains no `.cardiff-qr` entry.
- [ ] After a failed render with a non-deterministic adapter and `include_qr: true`, the output directory contains no `*-cardiff-qr.png` file.
- [ ] The adapter still receives TeX whose `\includegraphics` path points to an existing PNG at compile time.
- [ ] `RenderResult.evidence` for the sample request is identical before and after the change.
- [ ] `cardiff/tests/rendering/test_pipeline.py` no longer asserts a `.cardiff-qr/` path in `rendered_tex`.
- [ ] `python -m pytest tests -q -p no:cacheprovider` passes from `cardiff/`.

## Test / Verification Plan

Existing tests to run (from `README.md` and `.github/workflows/ci.yml`; recommended, not run as part of issue authoring):
- `python -m pytest tests/rendering -q -p no:cacheprovider`
- `python -m pytest tests/cli -q -p no:cacheprovider`

New tests likely needed:
- In `cardiff/tests/rendering/test_pipeline.py`: success and failure cases writing to `tmp_path` with a fake non-deterministic adapter. The adapter records whether the referenced PNG existed during `compile`, and the test asserts the output directory is clean afterwards.

Manual checks:
- With `xelatex` installed and a template that compiles, render with `include_qr: true` and confirm the PDF shows the QR code and no `.cardiff-qr` directory remains.

Regression checks:
- The normalized-evidence stability test still passes.
- The QR preprocessing failure classification test (`:340`) still passes.

Security checks:
- Confirm no personal-data artifact remains outside the system temp location after the render returns.

## Implementation Boundaries

- Non-goals: QR payload changes; adapter API redesign; CI workflow edits.
- Forbidden shortcuts:
  - Do not write the QR image into the repository or the current working directory.
  - Do not keep the file and merely rename the directory.
- Compatibility: Windows, Linux, and macOS temp-directory semantics. On Windows, the file must not be held open while XeLaTeX reads it.
- Contracts to preserve: `RenderResult` fields; normalized evidence fields; `BaseTeXAdapter.compile` signature.
- Project conventions: tests write to `tmp_path`, not to the tracked fixture tree.

## Risks and Review Focus

- Security/privacy: the QR image contains contact data. Review check: the tests assert the output directory has no PNG after both success and failure paths.
- Correctness: deleting the image before the adapter reads it. Review check: the fake adapter asserts the PNG exists during `compile`.
- Regression: evidence stability. Review check: the existing evidence-stability test passes unchanged except for the path assertion.

## Work Mapping

User-provided context (audit observation of leftover QR files) -> `cardiff/src/cardiff/rendering/pipeline.py`, `cardiff/src/cardiff/rendering/directives.py`, `cardiff/tests/rendering/test_pipeline.py` -> Acceptance Criteria above -> Test / Verification Plan above.

## Open Questions

- Maintainer, non-blocking: is it acceptable for `RenderResult.rendered_tex` to reference a temporary QR path that no longer exists after the call returns? Callers that reuse `rendered_tex` to recompile would then need to regenerate the image.
- Maintainer, non-blocking: once this is fixed, should the `.cardiff-qr` cleanup lines be removed from both workflows?

## Definition of Done

- [ ] code change is scoped to the in-scope list
- [ ] all acceptance criteria are observably met
- [ ] tests in the verification plan are added or updated and passing
- [ ] documentation, ADRs, or runbooks updated when the change requires it
- [ ] reviewer focus areas from the risk section are addressed
- [ ] work-mapping links are populated
- [ ] blocker/dependency status is resolved or explicitly carried forward
- [ ] issue is closed with a brief evidence summary referencing the verifying tests, commands, or screenshots
