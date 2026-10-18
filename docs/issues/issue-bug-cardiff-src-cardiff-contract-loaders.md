# [BUG] [rev] Request loading crashes on non-UTF-8 files and rejects UTF-8 BOM JSON

## Summary

`load_request_document` reads request files with `encoding="utf-8"` and does not handle decode errors. A UTF-16 request file therefore crashes the CLI with a `UnicodeDecodeError` traceback, no JSON status line, and exit `1`. That is the same exit code the CLI documents for a validation rejection. Separately, a UTF-8 file with a byte-order mark is accepted when it is YAML but rejected with `contract_error` when it is JSON, so the two documented formats behave differently for the same encoding. The desired outcome is consistent BOM handling across formats and a structured, documented failure for undecodable input.

## Issue Type

Primary type: bug

Labels:
- `bug` (pre-existing)
- `good first issue` (pre-existing)
- `light work` (pre-existing)

Secondary types: none.

## Readiness Grade

AGENT_READY

All three behaviors were reproduced with the CLI during the pre-issue audit, using re-encoded copies of the committed sample requests. The decoding call sites are directly observed. Acceptance criteria are CLI-observable. The exit-code choice for undecodable input has a recommended default and is non-blocking.

## Source Context

Path-scoped context in the current repository: `cardiff/src/cardiff/contract/loaders.py`, with supporting reads of `cardiff/src/cardiff/cli.py` and `cardiff/docs/cli-quickstart.md`, plus reporter-supplied reproduction evidence from a pre-issue audit.

## Detection Context

Detected in branch: `rev`

GitHub repository: zcalifornia-ph/cardiff

Local artifact path: `docs/issues/issue-bug-cardiff-src-cardiff-contract-loaders.md`

Audited at commit `3a29f30`.

## Blockers and Dependencies

No blockers identified from the loaded evidence.

No GitHub issue dependency was attached.

## Scope

In scope:
- Decoding request files in `load_request_document` (path inputs), including UTF-8 with BOM and undecodable bytes.
- Making `validate` and `render` emit a JSON status object and a documented exit code when a request file cannot be decoded.
- Tests and the `cardiff/docs/cli-quickstart.md` exit-code note for the chosen behavior.

Out of scope:
- Supporting arbitrary legacy encodings beyond what is decided in Open Questions.
- Changing JSON/YAML format detection.
- Reference-evidence file loading in `cli.py`, which already catches `OSError` and `JSONDecodeError`.

## Current / Observed Behavior

Observed during the pre-issue audit. Copies of `tests/fixtures/requests/valid-request.yaml` and `valid-request.json` were re-encoded with Python's `utf-16` and `utf-8-sig` codecs, then each was run through `python -m cardiff validate <file> --approved-asset-root tests/fixtures/approved-assets` from `cardiff/`:

| Input | Exit | stdout | stderr tail |
| --- | --- | --- | --- |
| UTF-16 YAML | `1` | empty | `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xff in position 0: invalid start byte` (traceback) |
| UTF-8 BOM JSON | `1` | JSON, `"status": "rejected"`, `contract_error`: `failed to parse json: Unexpected UTF-8 BOM (decode using utf-8-sig): line 1 column 1 (char 0)` | issue lines |
| UTF-8 BOM YAML | `0` | JSON, `"status": "accepted"` | `Validated ...` |

Code evidence (directly observed):
- `cardiff/src/cardiff/contract/loaders.py:247` and `:256`: `read_text(encoding="utf-8")` for `Path` and existing-path string inputs.
- `cardiff/src/cardiff/contract/loaders.py:271-300`: `parse_render_request` catches `TypeError`, `json.JSONDecodeError`, and `yaml.YAMLError`, but decoding happens earlier in `load_request_document`.
- `cardiff/src/cardiff/cli.py:332` (`run_validate`) and `:425` (`run_render`) call `load_request_document(request_path)` without handling decode errors.
- `cardiff/docs/cli-quickstart.md` (Exit Codes) lists `1` as "canonical validation rejected the request" and `2` as "CLI usage or required file/path error".

## Expected / Target Behavior

- A UTF-8 JSON request with a BOM validates the same as one without a BOM (exit `0` for the sample).
- A UTF-8 YAML request with a BOM keeps validating (exit `0` for the sample).
- An undecodable request file produces no traceback. Both `validate` and `render` emit one JSON status object on stdout and exit with a documented code (see Open Questions).

## Reproduction Steps or Validation Steps

Preconditions: dependencies installed per `README.md`; working directory `cardiff/`; `<scratch-dir>` is a writable directory outside the repository.

1. Run `python -c "import pathlib; pathlib.Path('<scratch-dir>/utf16.yaml').write_text(pathlib.Path('tests/fixtures/requests/valid-request.yaml').read_text(encoding='utf-8'), encoding='utf-16')"`.
2. Run `python -m cardiff validate <scratch-dir>/utf16.yaml --approved-asset-root tests/fixtures/approved-assets`.
3. Observe exit code `1`.
4. Failing observation: stdout is empty and stderr ends with a `UnicodeDecodeError` traceback.
5. Run `python -c "import pathlib; pathlib.Path('<scratch-dir>/bom.json').write_text(pathlib.Path('tests/fixtures/requests/valid-request.json').read_text(encoding='utf-8'), encoding='utf-8-sig')"`.
6. Run `python -m cardiff validate <scratch-dir>/bom.json --approved-asset-root tests/fixtures/approved-assets`.
7. Failing observation: exit `1` with a `contract_error` mentioning `Unexpected UTF-8 BOM`, while the same content as BOM-prefixed YAML is accepted.

## Environment and Evidence

- Operating system: Windows 11 (audit machine). The behavior is platform-independent by code inspection.
- Runtime: Python 3.14.0; PyYAML 6.0.3.
- Outputs: summarized in the table in Current / Observed Behavior. Local paths are omitted.
- How often BOM or UTF-16 request files occur in practice (for example from Windows shells or editors): Not provided / not verified.

## Relevant Files, Symbols, and Tests

- `cardiff/src/cardiff/contract/loaders.py`: `load_request_document` (`:234-268`), `parse_render_request` (`:271-300`), `_decode_mapping` (`:315-323`). Directly observed.
- `cardiff/src/cardiff/cli.py`: `run_validate` (`:317-378`), `run_render` (`:381-552`), `_emit_cli_error` (`:664-686`). Directly observed.
- `cardiff/docs/cli-quickstart.md`: Exit Codes section. Directly observed.
- `cardiff/tests/cli/test_cli.py`, `cardiff/tests/contract/test_validation.py`: existing tests; none cover encodings. Directly observed by search.

## Agent Handoff Notes

- Inspect first: `load_request_document`, then how `run_validate` / `run_render` consume it.
- Search terms: `read_text(encoding="utf-8")`, `UnicodeDecodeError`, `utf-8-sig`, `_emit_cli_error`.
- Hypotheses to verify, not instructions:
  - Reading with `utf-8-sig` handles the BOM for both formats.
  - Undecodable input can surface either as a `ValidationResult` with `contract_error`, through the existing `parse_render_request` error style, or as a CLI usage error through `_emit_cli_error`.
- Constraints: `load_request_document` is public API (exported from `cardiff` and `cardiff.contract`) and also accepts streams and raw strings. Keep those paths working.
- Assumptions to avoid: the YAML-with-BOM success is PyYAML stripping the BOM. It is not a deliberate Cardiff behavior, so do not rely on it for JSON.

## Acceptance Criteria

- [ ] A UTF-8-with-BOM copy of `tests/fixtures/requests/valid-request.json` validates with exit `0`.
- [ ] A UTF-8-with-BOM copy of `tests/fixtures/requests/valid-request.yaml` validates with exit `0`.
- [ ] `validate` on a UTF-16 copy of `valid-request.yaml` prints no `Traceback` on stderr.
- [ ] `validate` on that UTF-16 copy prints exactly one JSON object on stdout whose `status` is not `accepted`.
- [ ] `render` on that UTF-16 copy prints no `Traceback` and prints one JSON status object on stdout.
- [ ] The exit code for undecodable input matches the code documented for it in `cardiff/docs/cli-quickstart.md`.
- [ ] Tests cover BOM JSON, BOM YAML, and undecodable input.

## Test / Verification Plan

Existing tests to run (from `README.md` and `.github/workflows/ci.yml`; recommended, not run as part of issue authoring):
- `python -m pytest tests/contract -q -p no:cacheprovider`
- `python -m pytest tests/cli -q -p no:cacheprovider`

New tests likely needed:
- In `cardiff/tests/cli/test_cli.py`: CLI cases writing re-encoded fixtures to `tmp_path` and asserting exit code and JSON payload.
- In `cardiff/tests/contract/`: `load_and_validate_request` on a BOM JSON path.

Regression checks:
- Plain UTF-8 JSON and YAML fixtures still validate.
- Stream and raw-string inputs to `load_request_document` are unchanged.

## Implementation Boundaries

- Non-goals: encoding auto-detection libraries; new dependencies.
- Forbidden shortcuts:
  - Do not wrap `main()` in a blanket `except Exception` that hides programming errors.
  - Do not decode with `errors="ignore"` or `errors="replace"`, because that would silently corrupt identity text.
- Compatibility: Python `>=3.12`; public `load_request_document` signature unchanged.
- Contracts to preserve: CLI JSON payload shape; exit codes `0`-`4` and their documented meanings.
- Project conventions: tests use fixtures under `cardiff/tests/fixtures/`. Generated files belong in `tmp_path`.

## Risks and Review Focus

- Correctness: lossy decoding. Review check: no `errors=` relaxation in the diff.
- Documentation drift: the chosen exit code must be documented. Review check: `cardiff/docs/cli-quickstart.md` is updated in the same change.

## Work Mapping

User-provided context (audit CLI reproduction with re-encoded fixtures) -> `cardiff/src/cardiff/contract/loaders.py`, `cardiff/src/cardiff/cli.py` -> Acceptance Criteria above -> Test / Verification Plan above.

## Open Questions

- Maintainer, non-blocking: should undecodable input be exit `1` (`contract_error` validation rejection) or exit `2` (CLI usage/file error)? The recommended default is `contract_error`, so library callers of `load_and_validate_request` also get a structured result instead of an exception.
- Maintainer, non-blocking: should UTF-16 with BOM be decoded and accepted rather than rejected? The recommended default is to reject it with a clear message and document UTF-8 as the supported encoding.

## Definition of Done

- [ ] code change is scoped to the in-scope list
- [ ] all acceptance criteria are observably met
- [ ] tests in the verification plan are added or updated and passing
- [ ] documentation, ADRs, or runbooks updated when the change requires it
- [ ] reviewer focus areas from the risk section are addressed
- [ ] work-mapping links are populated
- [ ] blocker/dependency status is resolved or explicitly carried forward
- [ ] issue is closed with a brief evidence summary referencing the verifying tests, commands, or screenshots
