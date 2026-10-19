# [BUG] [rev] XeLaTeX compile failures report stderr warnings instead of the TeX error

## Summary

When `xelatex` exits with a non-zero code, `XeLaTeXAdapter.compile` reports only the last non-empty output stream as the failure diagnostic. MiKTeX writes update and privilege warnings to stderr, so on MiKTeX the diagnostic is that warning, and the actual TeX error on stdout (for example `! I can't find file` or `! Undefined control sequence.`) is dropped. This hid the real cause of a CI failure in #54: the logged reason was a MiKTeX update warning, while the actual failure was a TeX error on stdout. With empty stderr, as on TeX Live, the diagnostic is instead the whole stdout transcript as one string. The desired outcome is that a failed XeLaTeX compile always surfaces the TeX error line, whatever the compiler writes to stderr.

## Issue Type

Primary type: bug

Labels:
- `bug` (pre-existing)
- `light work` (pre-existing)

Secondary types: none.

## Readiness Grade

AGENT_READY

The behavior was reproduced with a short script that uses only `XeLaTeXAdapter` and a mocked `subprocess.run` (see Reproduction Steps), so it does not need a TeX installation. The selection logic is directly observed in `cardiff/src/cardiff/rendering/tex.py`. The real-world occurrence is visible in a public CI log. The exact shape of the new diagnostics is an open design question, but it is non-blocking, because every acceptable design must pass the same acceptance checks.

## Source Context

Path-scoped context in the current repository: `cardiff/src/cardiff/rendering/tex.py`. Supporting reads: `cardiff/src/cardiff/rendering/models.py` (`RenderingError`), `cardiff/src/cardiff/rendering/pipeline.py` (where `RenderingError.diagnostics` becomes `RenderResult.diagnostics`), `cardiff/src/cardiff/cli.py` (which prints `render_result.diagnostics`), and `cardiff/tests/rendering/test_pipeline.py`. Reporter-supplied context comes from the CI runs for #54.

## Detection Context

Detected in branch: `rev`

GitHub repository: zcalifornia-ph/cardiff

Local artifact path: `docs/issues/issue-bug-cardiff-src-cardiff-rendering-tex.md`

Line numbers below are from `rev` at commit `c3e14a5`.

## Blockers and Dependencies

No blockers identified from the loaded evidence.

Recommended sequencing (text-only, no dependency attached because #54 is a pull request, not an issue): start after #54 is merged. #54 changes the same `subprocess.run` call in `XeLaTeXAdapter.compile` (it now runs `xelatex` with `cwd` set to the temp directory and a bare file name). Working from `main` before #54 merges will conflict.

## Scope

In scope:
- The failure branch of `XeLaTeXAdapter.compile` (`if completed.returncode != 0:`), which builds the message passed to `RenderingError`.
- A regression test in `cardiff/tests/rendering/` that mocks `subprocess.run`, so it runs without `xelatex` installed.

Out of scope:
- The success branch's `TeXCompileArtifact.diagnostics`, which carries both full streams.
- Writing or attaching the `.log` file from the temp directory.
- `DeterministicTeXAdapter`, the CLI JSON shape, and `RenderFailureClass` values.
- MiKTeX or TeX Live installation in CI (handled in #54).

## Current / Observed Behavior

Observed in `cardiff/src/cardiff/rendering/tex.py`, lines 337-344 on `rev` at `c3e14a5`:

```python
if completed.returncode != 0:
    diagnostics = tuple(
        line for line in (completed.stdout, completed.stderr) if line.strip()
    )
    raise RenderingError(
        RenderFailureClass.TEX_COMPILE_FAILED,
        diagnostics[-1] if diagnostics else "xelatex compilation failed",
    )
```

`diagnostics` holds whole streams, not lines. `diagnostics[-1]` is therefore stderr whenever stderr is non-empty, and the full stdout transcript otherwise. `RenderingError.__init__` (`cardiff/src/cardiff/rendering/models.py`) stores that single message as `diagnostics = (message,)`. The pipeline returns it as `RenderResult.diagnostics`, and the CLI prints it.

Observed outcomes:
- **Non-empty stderr (MiKTeX):** the diagnostic is the stderr warning text, and the TeX error from stdout is absent. Reproduced locally; see Reproduction Steps.
- **Empty stderr (typical TeX Live):** the diagnostic is the entire stdout transcript as a single string. It contains the `!` error line, but buried in the full log. Reproduced locally with the same mock and `stderr=""`.
- **In CI:** a `windows-latest` run for #54 (https://github.com/zcalifornia-ph/cardiff/actions/runs/39106949757, commit `dee324e`) failed `test_bundled_template_compiles_with_xelatex` with only this diagnostic: `xelatex: security risk: running with elevated privileges` / `xelatex: major issue: So far, you have not checked for updates as a MiKTeX user.`
  - In that run, a minimal XeLaTeX compile earlier in the job had succeeded. The real cause was a TeX `! I can't find file` error on stdout, triggered by a `~` in the temp path.
  - It was found only by reproducing locally, then fixed in `c3e14a5`, after which the same job passed.

## Expected / Target Behavior

When `xelatex` exits non-zero, `RenderingError.diagnostics` includes the TeX error line or lines from stdout (lines beginning with `! `), whether or not stderr is empty. Stderr warnings must not replace the TeX error. If stdout has no `! ` line, the diagnostics stay non-empty and still describe the failure. The failure class stays `tex_compile_failed`, and no PDF is written.

## Reproduction Steps or Validation Steps

1. From `cardiff/`, on any OS, with or without `xelatex` installed, save this script as `repro_diagnostics.py`:

   ```python
   import subprocess
   from unittest.mock import patch

   from cardiff.rendering.models import RenderingError
   from cardiff.rendering.tex import XeLaTeXAdapter

   version = subprocess.CompletedProcess([], 0, stdout="XeTeX 3.141592653\n", stderr="")
   failed = subprocess.CompletedProcess(
       [],
       1,
       stdout="This is XeTeX\n! Undefined control sequence.\n",
       stderr="xelatex: major issue: So far, you have not checked for updates as a MiKTeX user.\n",
   )

   with patch("cardiff.rendering.tex.shutil.which", return_value="xelatex"), patch(
       "cardiff.rendering.tex.subprocess.run", side_effect=[version, failed]
   ):
       try:
           XeLaTeXAdapter().compile(
               "unused", "out.pdf", page_size_pt=(252.0, 144.0), preview_lines=(), title="t"
           )
       except RenderingError as error:
           print(error.failure_class.value)
           print(error.diagnostics)
   ```

   The first mocked `subprocess.run` result answers the `--version` probe in `XeLaTeXAdapter.__init__`; the second is the failed compile.
2. Run `python repro_diagnostics.py` (with the package installed via `pip install -e ".[dev]"`, or with `PYTHONPATH=src`).
3. Observe the first line: `tex_compile_failed`.
4. Observe the second line, which is the failing observation: `('xelatex: major issue: So far, you have not checked for updates as a MiKTeX user.\n',)`. The `! Undefined control sequence.` line from stdout is missing.

## Environment and Evidence

- **Operating system and runtime:** reproduced on Windows 11 with Python 3.14.0. The mock makes the reproduction independent of OS and TeX distribution. The CI occurrence was on `windows-latest` (Windows Server 2025) with MiKTeX 26.5, Python 3.12 and 3.13.
- **CI log:** https://github.com/zcalifornia-ph/cardiff/actions/runs/39106949757, job `Test (windows-latest, Python 3.13)`, step `Run rendering tests`.
- **Package manifest, stack traces, screenshots:** not relevant. The failure is a returned diagnostic, not an exception escaping to the user.

## Relevant Files, Symbols, and Tests

- `cardiff/src/cardiff/rendering/tex.py`: `XeLaTeXAdapter.compile`, failure branch at lines 337-344. Directly observed.
- `cardiff/src/cardiff/rendering/tex.py`: `XeLaTeXAdapter.compile`, success branch building `TeXCompileArtifact.diagnostics` at lines 353-355. Directly observed; out of scope.
- `cardiff/src/cardiff/rendering/models.py`: `RenderingError.__init__` sets `self.diagnostics = (message,)`. Directly observed.
- `cardiff/src/cardiff/rendering/pipeline.py`: `except RenderingError as error:` returns `RenderResult(..., diagnostics=error.diagnostics)` at lines 379-385. Directly observed.
- `cardiff/src/cardiff/cli.py`: render output includes `list(render_result.diagnostics)`. Directly observed.
- `cardiff/tests/rendering/test_pipeline.py`: `test_bundled_template_compiles_with_xelatex` and `test_xelatex_compiles_when_the_temp_directory_contains_a_tilde` assert success and print `result.diagnostics` on failure. They are the tests whose failure output this bug degrades. Directly observed.

## Agent Handoff Notes

- Start at the `if completed.returncode != 0:` block in `XeLaTeXAdapter.compile`.
- Search terms: `diagnostics[-1]`, `xelatex compilation failed`, `RenderFailureClass.TEX_COMPILE_FAILED`.
- **Data flow:** `subprocess.run` -> `CompletedProcess.stdout`/`.stderr` -> `RenderingError(message)` -> `RenderingError.diagnostics` -> `RenderResult.diagnostics` -> CLI JSON payload and stderr message.
- **Constraint:** `RenderingError` takes a single `message`, and `diagnostics` is derived as a one-element tuple. Supporting several entries means either joining them into one message or extending `RenderingError`, so keep any change there minimal and backward compatible for existing callers.
- **Hypothesis to verify, not an instruction:** extract stdout lines starting with `! ` (and possibly the following `l.<n>` context line), put them first, and keep stderr as secondary context or a fallback.
- **Assumptions to avoid:** TeX errors do not go to stderr; TeX writes them to stdout and the `.log`. Do not depend on the `.log` file, which lives in the temp directory that is deleted when `compile` returns.
- **Test approach:** reuse the mocking pattern from the reproduction (`patch("cardiff.rendering.tex.shutil.which")` plus `patch("cardiff.rendering.tex.subprocess.run", side_effect=[version, failed])`) so the test runs without TeX.

## Acceptance Criteria

- [ ] With the reproduction's mocked failed run (TeX error on stdout, MiKTeX warning on stderr), `RenderingError.diagnostics` contains a string that includes `! Undefined control sequence.`.
- [ ] With the same mocked stdout and `stderr=""`, `RenderingError.diagnostics` contains a string that includes `! Undefined control sequence.`.
- [ ] With the same mocked stdout and `stderr=""`, no single diagnostics entry equals the entire stdout transcript.
- [ ] With a mocked failed run whose stdout has no line starting with `! ` and whose stderr is empty, `RenderingError.diagnostics` is non-empty.
- [ ] In every case above, `RenderingError.failure_class` is `RenderFailureClass.TEX_COMPILE_FAILED`.
- [ ] A regression test covering the first criterion exists under `cardiff/tests/rendering/` and passes without `xelatex` on `PATH`.
- [ ] `python -m pytest tests/rendering -q -p no:cacheprovider` passes from `cardiff/`.
- [ ] `python -m pytest tests/cli -q -p no:cacheprovider` passes from `cardiff/`.

## Test / Verification Plan

- **Existing tests to run** (commands from `CONTRIBUTING.md` Verification Notes, run from `cardiff/`): `python -m pytest tests/contract -q -p no:cacheprovider`, `python -m pytest tests/rendering -q -p no:cacheprovider`, and `python -m pytest tests/cli -q -p no:cacheprovider`.
- **New tests likely needed:** one or more tests in `cardiff/tests/rendering/test_pipeline.py`, or a new adapter-focused test module, that mock `subprocess.run` as in the reproduction and assert on `RenderingError.diagnostics` for the stderr-present, stderr-empty, and no-`!`-line cases.
- **Manual check:** with a real `xelatex`, render a template containing an undefined macro, and confirm the reported diagnostic names the undefined control sequence.
- **Regression checks:** the XeLaTeX success path still returns `RenderStatus.SUCCEEDED` with `runtime_name == "xelatex"` (`test_bundled_template_compiles_with_xelatex`), and the deterministic adapter's diagnostics are unchanged.
- **Security checks:** diagnostics are user-visible. Confirm the change does not add new content beyond compiler output Cardiff already returns today, such as environment variables or the full temp path.
- **Performance checks:** not applicable.

## Implementation Boundaries

- **Non-goals:**
  - Do not change the success-path diagnostics.
  - Do not add `.log` file capture.
  - Do not change CLI exit codes or the JSON field names.
- **Forbidden shortcuts:** do not swallow stderr entirely without keeping a fallback for runs whose stdout has no `!` line.
- **Compatibility:**
  - Python 3.12 and 3.13 (the CI matrix).
  - TeX Live and MiKTeX output conventions.
  - Windows and Linux.
- **Contracts to preserve:**
  - `RenderFailureClass.TEX_COMPILE_FAILED`.
  - The `RenderResult.diagnostics` tuple type.
  - `RenderingError(failure_class, message)` for existing callers.
- **Conventions:** keep the existing Apache attribution header in edited Python files (see `CONTRIBUTING.md`). Follow the test style in `cardiff/tests/rendering/test_pipeline.py`.

## Risks and Review Focus

- **Correctness:** a TeX error can span several lines (`! ...` followed by `l.<n> ...`). Check that the extracted text is enough to act on, using a real undefined-macro compile.
- **Regression:** callers or tests that compare the full diagnostic string. Search `tests/` for assertions on `diagnostics` from XeLaTeX runs.
- **Documentation drift:** if diagnostics shape is documented later, keep it consistent. No current doc in `cardiff/docs/` describes XeLaTeX failure diagnostics.

## Work Mapping

Reporter-supplied context (#54 CI runs and local reproduction) -> `cardiff/src/cardiff/rendering/tex.py` `XeLaTeXAdapter.compile` failure branch -> acceptance criteria above -> verification plan above.

## Open Questions

- **Non-blocking, owner:** should failure diagnostics keep the stderr warnings as a separate trailing entry, or drop them when a TeX `!` error line is found?
- **Non-blocking, owner:** should the success path also stop carrying full stdout and stderr in `TeXCompileArtifact.diagnostics`? Out of scope here; a separate issue if wanted.

## Definition of Done

- [ ] code change is scoped to the in-scope list
- [ ] all acceptance criteria are observably met
- [ ] tests in the verification plan are added or updated and passing
- [ ] documentation, ADRs, or runbooks updated when the change requires it
- [ ] reviewer focus areas from the risk section are addressed
- [ ] work-mapping links are populated
- [ ] blocker/dependency status is resolved or explicitly carried forward
- [ ] issue is closed with a brief evidence summary referencing the verifying tests, commands, or screenshots
