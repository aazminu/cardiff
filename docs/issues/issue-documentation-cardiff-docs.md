# [DOCUMENTATION] [rev] Fix root-relative links in cardiff/docs that resolve to a non-existent cardiff/cardiff path

## Summary

Seven Markdown links across three files under `cardiff/docs/` use root-relative targets that begin with `/cardiff/cardiff/`. GitHub resolves a leading `/` against the repository root, so these links point to `cardiff/cardiff/...`, a path that does not exist, and return 404. Readers following the cross-references between the validation contract, the render pipeline, the template-authoring guide, and the approved-assets README hit dead ends. The desired outcome is that every one of these links resolves on GitHub and in local Markdown previews.

## Issue Type

Primary type: documentation

Labels:
- `documentation` (pre-existing)
- `good first issue` (pre-existing)
- `light work` (pre-existing)

Secondary types: none.

## Readiness Grade

AGENT_READY

Every affected line is listed. GitHub's rendered `href` for one of the links was captured during the pre-issue audit. The broken and correct URLs were checked with HTTP status codes. Acceptance criteria are a search plus link checks. No open question blocks the change.

## Source Context

Path-scoped context in the current repository: `cardiff/docs`, plus reporter-supplied evidence from a pre-issue audit.

## Detection Context

Detected in branch: `rev`

GitHub repository: zcalifornia-ph/cardiff

Local artifact path: `docs/issues/issue-documentation-cardiff-docs.md`

Audited at commit `3a29f30`.

## Blockers and Dependencies

No blockers identified from the loaded evidence.

No GitHub issue dependency was attached.

## Scope

In scope: the seven links listed below.

| File | Line | Current target |
| --- | --- | --- |
| `cardiff/docs/render-pipeline.md` | 7 | `/cardiff/cardiff/docs/template-authoring.md` |
| `cardiff/docs/render-pipeline.md` | 75 | `/cardiff/cardiff/docs/template-authoring.md` |
| `cardiff/docs/template-authoring.md` | 7 | `/cardiff/cardiff/docs/validation-contract.md` |
| `cardiff/docs/template-authoring.md` | 8 | `/cardiff/cardiff/docs/render-pipeline.md` |
| `cardiff/docs/template-authoring.md` | 9 | `/cardiff/cardiff/tests/fixtures/approved-assets/README.md` |
| `cardiff/docs/template-authoring.md` | 100 | `/cardiff/cardiff/tests/fixtures/approved-assets/README.md` |
| `cardiff/docs/validation-contract.md` | 7 | `/cardiff/cardiff/docs/template-authoring.md` |

Out of scope:
- Rewording the documents.
- Links in other files (`README.md`, `CONTRIBUTING.md`, and others), which were not found to use this pattern.
- Adding a link checker to CI (see Open Questions).

## Current / Observed Behavior

Observed during the pre-issue audit:
- A search of `cardiff/docs/*.md` for `](/cardiff` returned exactly the seven lines in the Scope table.
- The GitHub page for `cardiff/docs/template-authoring.md` on `main` renders the validation-contract link as `href="/zcalifornia-ph/cardiff/blob/main/cardiff/cardiff/docs/validation-contract.md"`.
- `https://github.com/zcalifornia-ph/cardiff/blob/main/cardiff/cardiff/docs/validation-contract.md` returned HTTP `404`.
- `https://github.com/zcalifornia-ph/cardiff/blob/main/cardiff/docs/validation-contract.md` returned HTTP `200`.

## Expected / Target Behavior

- Each of the seven links opens the intended file on GitHub, for any branch.
- Each link also resolves in a local Markdown preview opened from the file's own directory. Plain relative targets such as `template-authoring.md` or `../tests/fixtures/approved-assets/README.md` work in both places.

## Reproduction Steps or Validation Steps

1. From the repository root, search for the pattern, for example with `rg -n "\]\(/cardiff/cardiff/" cardiff/docs`.
2. Observe the seven matches in the Scope table.
3. Open `https://github.com/zcalifornia-ph/cardiff/blob/main/cardiff/docs/template-authoring.md` and click "validation-contract.md" under Canonical references.
4. Failing observation: GitHub shows a 404 page for `cardiff/cardiff/docs/validation-contract.md`.

## Environment and Evidence

- Rendered `href` and HTTP status codes: quoted in Current / Observed Behavior. They were captured against `main` during the audit. The same link text exists on `rev`.
- Local preview behavior in specific editors: Not provided / not verified.

## Relevant Files, Symbols, and Tests

- `cardiff/docs/render-pipeline.md`: lines 7 and 75. Directly observed.
- `cardiff/docs/template-authoring.md`: lines 7, 8, 9, and 100. Directly observed.
- `cardiff/docs/validation-contract.md`: line 7. Directly observed.
- `cardiff/tests/fixtures/approved-assets/README.md`: the link target. Its existence was confirmed from the tracked file list.

## Agent Handoff Notes

- Inspect first: the seven lines above. The change is text-only.
- Search term: `](/cardiff/cardiff/`.
- Hypothesis to verify, not an instruction: links between files in `cardiff/docs/` can be bare file names, and links to the fixtures README can use `../tests/fixtures/approved-assets/README.md`.
- Constraints: keep link text and surrounding prose unchanged.
- Assumptions to avoid: a leading `/` in GitHub Markdown is not relative to the repository owner/name path. It resolves against the repository root on the current branch.

## Acceptance Criteria

- [ ] `rg -n "\]\(/cardiff/cardiff/" cardiff/docs` returns no matches.
- [ ] On GitHub, the two links in `cardiff/docs/render-pipeline.md` open `cardiff/docs/template-authoring.md`.
- [ ] On GitHub, the four links in `cardiff/docs/template-authoring.md` open their intended targets.
- [ ] On GitHub, the link in `cardiff/docs/validation-contract.md` opens `cardiff/docs/template-authoring.md`.
- [ ] No other line in the three files changes.

## Test / Verification Plan

Existing tests to run: none are relevant. This is a Markdown-only change.

Manual checks:
- After pushing the branch, open each of the three files on GitHub and click every changed link. Each should load without a 404.

Regression checks:
- The diff is limited to link targets on the seven listed lines.

## Implementation Boundaries

- Non-goals: content edits; restructuring the docs folder; changing links in other files.
- Forbidden shortcuts: do not replace the links with absolute `https://github.com/...` URLs pinned to `main`, because those break on other branches and forks.
- Project conventions: Conventional Commit type `docs:`.

## Risks and Review Focus

- Documentation drift: a missed link. Review check: the `rg` command in the acceptance criteria returns nothing.
- Correctness: wrong relative depth for the fixtures README. Review check: click-through on GitHub.

## Work Mapping

User-provided context (audit link check) -> `cardiff/docs/render-pipeline.md`, `cardiff/docs/template-authoring.md`, `cardiff/docs/validation-contract.md` -> Acceptance Criteria above -> Test / Verification Plan above.

## Open Questions

- Maintainer, non-blocking: should a Markdown link checker run in CI to prevent regressions?

## Definition of Done

- [ ] code change is scoped to the in-scope list
- [ ] all acceptance criteria are observably met
- [ ] tests in the verification plan are added or updated and passing
- [ ] documentation, ADRs, or runbooks updated when the change requires it
- [ ] reviewer focus areas from the risk section are addressed
- [ ] work-mapping links are populated
- [ ] blocker/dependency status is resolved or explicitly carried forward
- [ ] issue is closed with a brief evidence summary referencing the verifying tests, commands, or screenshots
