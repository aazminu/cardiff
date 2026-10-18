# [BUG] [rev] Business-card template fails XeLaTeX compilation on accent color and empty optional fields

## Summary

When `xelatex` is on `PATH`, the CLI picks the real XeLaTeX adapter automatically, and the bundled `business-card` template fails to compile for the documented sample request. Two independent causes were observed: the `accent_hex` value (or its `#000000` default) is substituted into the TeX body unescaped, and empty optional placeholders (`organization`, `address_block`) leave a bare `\\` that LaTeX rejects under `\raggedright`. The result is `tex_compile_failed` (exit `3`) on any machine with a TeX distribution, while the deterministic adapter used by every test hides the problem. The desired outcome is that the bundled template compiles under XeLaTeX for the sample request and for requests that omit optional identity fields.

## Issue Type

Primary type: bug

Labels:
- `bug` (pre-existing)
- `for experienced devs` (pre-existing)

Secondary types: none.

## Readiness Grade

AGENT_READY

Both causes were reproduced with a real XeLaTeX run during the pre-issue audit and isolated independently (the first by the compiler log line, the second by neutralizing the accent line in a template copy). The substitution code, the template lines, and the validation rule that leaves `#` unescaped are all directly observed in the files listed below. Acceptance criteria are observable CLI and test outcomes. The only open questions are non-blocking layout preferences.

## Source Context

Path-scoped context in the current repository: `cardiff/src/cardiff/rendering/pipeline.py` and `cardiff/src/cardiff/templates/business-card/card.tex`, with reporter-supplied reproduction evidence from a pre-issue audit.

## Detection Context

Detected in branch: `rev`

GitHub repository: zcalifornia-ph/cardiff

Local artifact path: `docs/issues/issue-bug-cardiff-src-cardiff-rendering-pipeline.md`

Audited at commit `3a29f30`.

## Blockers and Dependencies

No blockers identified from the loaded evidence.

Related, not blocking: `#4` covers the broader business-card layout specification and may later replace the placeholder `Variant:` / `Accent:` lines. This defect exists today and can be fixed independently.

No GitHub issue dependency was attached.

## Scope

In scope:
- Making the bundled `business-card` template compile under XeLaTeX when `accent_hex` is present or defaulted.
- Making the bundled template compile under XeLaTeX when `identity.organization` and/or `identity.address_lines` are absent.
- Regression coverage for both cases that runs without `xelatex` installed.
- Regenerating `reference-evidence.json` only if the template text change alters `tex_fingerprint`.

Out of scope:
- The full print layout specification, bleed, and field placement (tracked in `#4`).
- Turning `accent_hex` into an applied color.
- Changing the canonical request contract or validation rules for `accent_hex`.
- Adding a TeX distribution to CI (see Open Questions).

## Current / Observed Behavior

Observed during the pre-issue audit with MiKTeX XeLaTeX on `PATH`:

1. `python -m cardiff render tests/fixtures/requests/valid-request.yaml --approved-asset-root tests/fixtures/approved-assets --output <scratch-dir>/real.pdf` (no `--deterministic`) exited `3` with `"failure_class": "tex_compile_failed"` and `"runtime": {"name": "xelatex", ...}`. The compiler log in `diagnostics` contained:

   ```text
   ! You can't use `macro parameter character #' in horizontal mode.
   l.13 Accent: #
                 0055AA\\
   ```

2. With line 13 of a copied template changed to a literal (`Accent: redacted\\`) and passed through `--template-root`, the same sample request rendered successfully (exit `0`, status `succeeded`). The QR include line compiled.

3. With that same neutralized template copy:
   - a request with no `organization` and no `address_lines` failed with `! LaTeX Error: There's no line here to end.`
   - a request with `organization` but no `address_lines` failed with the same error.
   - a request with both `organization` and one address line rendered successfully.

4. Without the template copy, a request that omits `accent_hex` still fails, because the default `#000000` is substituted.

Code evidence (directly observed):
- `cardiff/src/cardiff/rendering/pipeline.py:387` maps a missing organization to `""`; `:392` joins `address_lines` into `address_block` (empty when absent); `:394` substitutes `accent_hex` with default `"#000000"`. No TeX escaping is applied to these values in `_build_placeholder_values` (`:375-396`).
- `cardiff/src/cardiff/contract/validation.py:616-628` normalizes `accent_hex` and checks `HEX_COLOR_PATTERN` (`:254`, `^#[0-9a-fA-F]{6}$`) but does not escape it, unlike identity text, which goes through `sanitize_text`.
- `cardiff/src/cardiff/templates/business-card/card.tex:6` sets `\raggedright`; `:9` is `{{ organization }}\\`; `:11` is `{{ address_block }}\\`; `:13` is `Accent: {{ accent_hex }}\\`.

Why tests pass: rendering and CLI tests use `DeterministicTeXAdapter` or fake adapters, and `DeterministicTeXAdapter.compile` (`cardiff/src/cardiff/rendering/tex.py:268-286`) writes a preview PDF without compiling TeX. `.github/workflows/ci.yml` does not install a TeX distribution.

Why it matters: `get_default_tex_adapter()` (`cardiff/src/cardiff/rendering/tex.py:377-380`) selects `XeLaTeXAdapter` whenever `xelatex` is on `PATH`, and `README.md` recommends installing `xelatex`. The public acceptance baseline in `REQUIREMENTS.md` states that the approved `business-card` template renders to a requested PDF path.

## Expected / Target Behavior

- With `xelatex` on `PATH`, the documented sample request renders: exit `0`, status `succeeded`, runtime name `xelatex`.
- Requests that omit any optional identity field render under XeLaTeX without a LaTeX error.
- No template placeholder value introduces an unescaped TeX special character such as `#`.
- The deterministic adapter's behavior is unchanged apart from any intentional `tex_fingerprint` change caused by template text edits.

## Reproduction Steps or Validation Steps

Preconditions: a TeX distribution providing `xelatex` on `PATH` (the audit used MiKTeX); dependencies installed per `README.md`; working directory `cardiff/`; `<scratch-dir>` is any writable directory outside the repository.

1. Run `python -m cardiff render tests/fixtures/requests/valid-request.yaml --approved-asset-root tests/fixtures/approved-assets --output <scratch-dir>/card.pdf`.
2. Observe the JSON status line on stdout reports `"runtime": {"name": "xelatex", ...}`.
3. Observe exit code `3`, `"status": "failed"`, and `"failure_class": "tex_compile_failed"`.
4. Observe the `diagnostics` text contains `You can't use `macro parameter character #' in horizontal mode` and `l.13 Accent: #`.
5. Copy `src/cardiff/templates/business-card/` to `<scratch-dir>/tpl/business-card/` and replace `Accent: {{ accent_hex }}` with `Accent: redacted` in the copy.
6. Create `<scratch-dir>/no-optional.yaml` with `identity` containing only `full_name`, `role`, `email`; `template.id: business-card`; `assets.logo: brand/logo.png`.
7. Run `python -m cardiff render <scratch-dir>/no-optional.yaml --approved-asset-root tests/fixtures/approved-assets --template-root <scratch-dir>/tpl --output <scratch-dir>/no-optional.pdf`.
8. Failing observation: exit `3` with `tex_compile_failed` and `LaTeX Error: There's no line here to end.` in `diagnostics`.

## Environment and Evidence

- Operating system: Windows 11 (audit machine).
- Runtime: Python 3.14.0 for the audit; the project declares `requires-python = ">=3.12"` (`cardiff/pyproject.toml`) and CI tests 3.12 and 3.13.
- TeX: `MiKTeX-XeTeX 4.16 (MiKTeX 25.12)`, as reported by the CLI `runtime.version` field.
- Libraries: PyYAML 6.0.3, segno 1.6.6, pytest 8.4.2.
- Test suite: `python -m pytest -q -p no:cacheprovider` in a clean export of commit `3a29f30` reported `48 passed`; no test compiles with XeLaTeX.
- Compiler log excerpts: quoted in Current / Observed Behavior.
- Linux and macOS TeX Live behavior: Not provided / not verified. The `#` error is standard TeX behavior. The `\raggedright` `\\` behavior is standard LaTeX behavior. Both are expected to reproduce on any distribution, but this was not run.

## Relevant Files, Symbols, and Tests

- `cardiff/src/cardiff/rendering/pipeline.py`: `_build_placeholder_values` (`:375-396`), `_render_template_source` (`:399-414`), `render_request_to_pdf` (`:248-372`). Directly observed.
- `cardiff/src/cardiff/templates/business-card/card.tex`: lines 6, 9, 11, 13. Directly observed.
- `cardiff/src/cardiff/contract/validation.py`: `HEX_COLOR_PATTERN` (`:254`), `accent_hex` handling in `_validate_template` (`:616-628`). Directly observed.
- `cardiff/src/cardiff/contract/sanitization.py`: `LATEX_ESCAPE_MAP` (`:224-234`) includes `#`. Directly observed.
- `cardiff/src/cardiff/rendering/tex.py`: `XeLaTeXAdapter.compile` (`:298-360`), `get_default_tex_adapter` (`:377-380`). Directly observed.
- `cardiff/tests/rendering/test_pipeline.py`, `cardiff/tests/rendering/test_determinism.py`, `cardiff/tests/cli/test_cli.py`: existing render tests, all using deterministic or fake adapters. Directly observed.
- `cardiff/tests/fixtures/approved-samples/business-card/reference-evidence.json`: holds `tex_fingerprint`, which changes if the template text changes. Directly observed.
- `.github/workflows/ci.yml`: no TeX installation step. Directly observed.

## Agent Handoff Notes

- Inspect first: `_build_placeholder_values` in `pipeline.py` and `card.tex`. Placeholder values flow request → `_build_placeholder_values` → `_render_template_source` → QR directive resolution → adapter.
- Search terms: `accent_hex`, `#000000`, `address_block`, `\raggedright`, `{{ organization }}`.
- Hypotheses to verify, not instructions:
  - Escaping `#` (for example `\#`) for `accent_hex` at substitution time would remove the first error.
  - Restructuring the template so empty optional values do not produce a line that starts with `\\` would remove the second error. One way is to emit the line break only with non-empty content.
- Constraints: keep `sanitize_text` and unsafe-content rejection unchanged. Keep `TEMPLATE_PLACEHOLDER_UNKNOWN` behavior. Keep placeholder names stable, because they are documented in `cardiff/docs/template-authoring.md`.
- Assumptions to avoid:
  - The deterministic adapter does not validate TeX, so a green test suite proves nothing about XeLaTeX compilation.
  - Do not assume `accent_hex` is already escaped because identity text is.
  - The first LaTeX error hides later ones because the adapter passes `-halt-on-error`.

## Acceptance Criteria

- [ ] With `xelatex` on `PATH`, `python -m cardiff render tests/fixtures/requests/valid-request.yaml --approved-asset-root tests/fixtures/approved-assets --output <dir>/card.pdf` exits `0`.
- [ ] That run reports `"status": "succeeded"` and runtime name `xelatex`.
- [ ] A request containing only `full_name`, `role`, `email`, `template.id`, and `assets.logo` renders under XeLaTeX with exit `0`.
- [ ] A request without `template.options.accent_hex` renders under XeLaTeX with exit `0`.
- [ ] The `rendered_tex` for the sample request contains no `#` character that is not preceded by a backslash.
- [ ] An automated test that does not require `xelatex` covers the `accent_hex` substitution case.
- [ ] An automated test that does not require `xelatex` covers the empty `organization` / `address_block` case.
- [ ] `python -m pytest tests -q -p no:cacheprovider` passes from `cardiff/`.
- [ ] Any change to `reference-evidence.json` is limited to `tex_fingerprint`.

## Test / Verification Plan

Existing tests to run (from `README.md` and `.github/workflows/ci.yml`; recommended, not run as part of issue authoring):
- `python -m pytest tests/contract -q -p no:cacheprovider`
- `python -m pytest tests/rendering -q -p no:cacheprovider`
- `python -m pytest tests/cli -q -p no:cacheprovider`

New tests likely needed:
- In `cardiff/tests/rendering/test_pipeline.py`: assert that `rendered_tex` escapes `accent_hex` and does not produce a line that starts with `\\` when optional fields are empty. A deterministic adapter is enough, because `rendered_tex` is returned on `RenderResult`.
- Optional: one XeLaTeX smoke test guarded by `pytest.mark.skipif(shutil.which("xelatex") is None, ...)`.

Manual checks:
- With `xelatex` installed, run the reproduction steps above. Each should exit `0` and produce a non-empty PDF.

Regression checks:
- `--deterministic` render of the sample request still exits `0`.
- Reference-evidence comparison passes after any intentional regeneration.

## Implementation Boundaries

- Non-goals: layout redesign; applying `accent_hex` as a color; new template options.
- Forbidden shortcuts:
  - Do not disable `-halt-on-error`.
  - Do not catch and ignore compile failures.
  - Do not loosen `HEX_COLOR_PATTERN`.
  - Do not remove the `Accent:` / `Variant:` lines without maintainer agreement (see Open Questions).
- Compatibility: Python `>=3.12`; behavior must hold on Windows, Linux, and macOS TeX distributions.
- Contracts to preserve: documented placeholder names; `RenderFailureClass` values; CLI exit codes `0`-`4`; JSON status payload shape.
- Project conventions: tests live under `cardiff/tests/rendering/` and use fixtures under `cardiff/tests/fixtures/`.

## Risks and Review Focus

- Correctness: the escaping must apply to every TeX-bound option value, not just `accent_hex`. Review check: grep `_build_placeholder_values` for values that skip `sanitize_text`.
- Regression: template edits change `tex_fingerprint`. Review check: the diff to `reference-evidence.json` touches only `tex_fingerprint`.
- Documentation drift: if the template's visible lines change, `cardiff/docs/template-authoring.md` should still describe the placeholders accurately. Review check: compare the placeholder list in the doc against `card.tex`.

## Work Mapping

User-provided context (audit reproduction with XeLaTeX) -> `cardiff/src/cardiff/rendering/pipeline.py`, `cardiff/src/cardiff/templates/business-card/card.tex`, `cardiff/src/cardiff/contract/validation.py` -> Acceptance Criteria above -> Test / Verification Plan above.

## Open Questions

- Maintainer, non-blocking: should the placeholder `Variant:` / `Accent:` debug lines stay in the bundled template until `#4` lands, or be removed now? The smallest fix keeps them and escapes the value.
- Maintainer or ops, non-blocking: should CI gain a job that installs a TeX distribution and runs one XeLaTeX smoke render, so this class of defect is caught automatically?

## Definition of Done

- [ ] code change is scoped to the in-scope list
- [ ] all acceptance criteria are observably met
- [ ] tests in the verification plan are added or updated and passing
- [ ] documentation, ADRs, or runbooks updated when the change requires it
- [ ] reviewer focus areas from the risk section are addressed
- [ ] work-mapping links are populated
- [ ] blocker/dependency status is resolved or explicitly carried forward
- [ ] issue is closed with a brief evidence summary referencing the verifying tests, commands, or screenshots
