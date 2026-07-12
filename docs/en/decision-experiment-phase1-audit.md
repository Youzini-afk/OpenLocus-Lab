# Decision-oriented product experiment — Phase 1 audit (executed, provider-free)

> **Stage 1 only. Eligibility / headroom audit — NOT a pain proof, NOT a
> product-effect proof, NOT a downstream-agent evaluation.** No provider and
> no agent runs were executed.

## What was run

A single provider-free execution of
`eval/decision_experiment_phase1_audit.py --audit`, with a self-test pass
(`--self-test`) beforehand. All work is local CPU only; `new_provider_calls = 0`,
`new_provider_or_agent_runs = false`.

- Frozen source cutoff: `056877ff638d59118e05e046bd30d816e70ba2fb` (the only
  SHA permitted in public output).
- Deterministic enumeration of all non-merge commits reachable before the
  cutoff, ordered newest-first then SHA.

## Result

| Field | Value |
|-------|-------|
| Non-merge commits enumerated | 865 |
| Commits considered by the filter | 865 |
| Eligible candidates after filter | 2 |
| Reproducibility checks attempted | 0 (not reached — below min cohort) |
| Headroom gate | not run (insufficient eligible) |
| **Overall gate status** | **STOP** |
| Reason | fewer_than_min_5_eligible_candidates_after_filter |

## Candidate-filter reason buckets (aggregate only)

| Reason bucket | Count |
|---------------|-------|
| excluded_docs_only | 766 |
| excluded_no_prod_source | 80 |
| excluded_not_defect_fix | 15 |
| excluded_msg_test | 1 |
| excluded_no_dev_test_found | 1 |
| eligible_developer_test_resolved | 2 |

No hardcoded favorable candidate list was used. The filter is fully rule-based;
every exclusion carries a fixed reason bucket. Rules were never weakened to
reach a denominator. Reason-bucket counts sum to considered commits (865).

## Rust inline test handling

The audit recognizes `#[cfg(test)] mod tests { ... }` inline test modules in
Rust source files (`crates/*/src/*.rs`) using deterministic brace-balanced
parsing that respects string literals, char literals, raw strings, line
comments, and nested block comments. Malformed or ambiguous regions are
rejected fail-closed (treated as production, conservative).

**Attribute false-positive safety:** the scanner is language-aware —
`#[cfg(test)]` text appearing inside line comments, block comments, regular
string literals, raw string literals, or char literals is **not** treated
as a real test-module attribute. Only attributes found at code positions are
accepted.

**Lifetime/label safety:** the Rust lexer distinguishes lifetimes (`'a`,
`'static`) and labels (`'label:`) from char literals. Only a syntactically
complete char literal (including valid escaped chars) is skipped as a char
literal; lifetimes/labels remain code tokens so brace tracking is not
corrupted. This ensures the test region ends before fixed production code
that uses `&'static str`, byte literals, or raw strings after the module.

**Byte-safe overlay:** inline test-module handling reads and writes raw
`bytes` (no newline translation on Windows). Region detection operates on
the UTF-8-decoded string, but character offsets are mapped back to byte
offsets in the original bytes before slicing. **Enforced real invariants**
(not just self-tests) in `apply_overlay` via **explicit base modes** (never
inferred from contents): `mode="parent"` (buggy parent + overlay / empty
patch — pre-overlay verifies `parent_full_hash`; post-overlay verifies
`parent_prod_hash` + `fixed_test_hash`), `mode="fixed"` (fixed commit + same
developer test — pre-overlay verifies `fixed_full_hash`; post-overlay
verifies `fixed_prod_hash` + `fixed_test_hash`; may be a no-op; never
demands parent hash), and `mode="parent_dev_patch"` (parent + production-only
dev patch + overlay — pre-overlay verifies `fixed_prod_hash` proving only the
frozen developer production patch changed production; post-overlay verifies
`fixed_prod_hash` unchanged + `fixed_test_hash` proving overlay contributes
test bytes only). Any mismatch raises and fails closed. Never
appends/replaces fixed production bytes. Fails closed on invalid UTF-8 or
ambiguous offset mappings. Unknown mode is rejected.

**Ambiguity fail-closed:** if a source file has multiple inline
`#[cfg(test)] mod ...` regions (in either parent or fixed), the
parent/fixed region correspondence is not uniquely determinable. The overlay
is rejected fail-closed (no eligible overlay) rather than silently using
region 0.

Inline test-region lines are excluded from the `<=100` production changed-line
limit and from the production-file set at the line-by-line level. For EVERY
Rust `prod_src` file (not only large ones), the parent/fixed source and unified
diff are inspected and test-region vs production changed lines are split. A
file counts as a production file only if at least one changed line falls outside
uniquely detected valid test regions. This prevents a small (`<=100` raw lines)
commit that touches only an inline test module from being misclassified as
production. For mixed source files, the scorer-only overlay preserves parent
production bytes exactly and transplants only the exact fixed developer-authored
inline test module bytes — verified by SHA-256 hash assertions on actual on-disk
bytes. Zero fixed production bytes may leak.

This corrected a prior overcount and a prior reason-bucket accounting error.
First, two fix commits that touch production source files with large inline
test modules were previously excluded as `excluded_too_many_prod_lines`; with
inline test detection they pass the line-count filter. Second, the inline
test-region split previously only ran when `raw_total > 100`, so a small
test-only inline-module change could be misclassified as production; the split
now runs for every Rust `prod_src` file. Third, deferred candidates that
successfully resolved an exact developer test overlay were previously left
counted under the `deferred_no_test_in_commit_check_preexisting` bucket; they
are now moved to `eligible_developer_test_resolved` so reason-bucket counts sum
to considered commits and the public report does not describe successful
candidates as deferred.

## Interpretation

The mined internal source (the OpenLocus repository before the cutoff) is
overwhelmingly documentation, protocol freezes, generated artifacts, and
eval-only scripts. Of the small number of product-source defect fixes, two
survive the filter and successfully resolve an exact developer test overlay
(`eligible_developer_test_resolved`) — but this is below the minimum cohort
of 5. No rules were weakened to reach a denominator.

Per the frozen contract, an eligibility failure is a **terminal STOP** for
Stage 1. No task redesign, no easier replacements, no threshold changes, no
new arms, and no package continuation. No pain, product, or effect claim is
made. R14/R20 retrieval labels were not treated as task outcomes; no
sparse/no-context or BEA arm was used; no currentness causal claim was made.

## Production Fast Context path (wired to production CLI schema, not exercised by a candidate)

The control/treatment pack-generation step reuses the **same existing
production `openlocus fast-context` CLI and renderer**:

- treatment: `regex,bm25,symbol,graph` + RRF + final citation/currentness
  validation, `max_evidence=12`, `budget=2000`;
- control: `bm25` only, same builder/renderer/query/caps.

The implementation is wired to the **real production FLATTENED evidence
schema**: `Evidence` is `#[serde(flatten)] pub core: EvidenceCore`, so each
evidence JSON object has directly flattened fields (`path`, `start_line`,
`end_line`, `content_sha`, `score`, `why`, `channels`) plus optional `meta`.
There is **no nested `core` object**; validation fails closed on the nested
pseudo-schema rather than supporting an invented fixture shape. Diagnostics
are validated against the exact known key set (`invalid_citations_dropped`,
`unknown_channels`, `token_budget_enforced`) with correct types and
`unknown_channels` empty. Unexpected non-fusion action channels, top-level
and per-turn `disabled_channels`, and stale freshness are all rejected.
Evidence paths are validated as relative, within-workspace, and existing on
disk. The exact `citations validate` invocation/logic from
`eval/fast_context_smoke.py` is reused against each arm's workspace evidence.
The `<5` audit returned before fast-context, so this step was **not exercised
by a real candidate in this run** — no new two-arm execution claim is made
without a committed aggregate record. Candidate pack generation, repro, and
headroom were not run. The headroom path (warm-repetition validation,
per-run citation rematerialization, before/after-CLI isolation scans,
explicit `isolation_scan_failures` gating) remains **synthetically validated
only** because the `2 < 5` STOP occurred before it.

**Two independent arm workspaces:** treatment and control arms run in
completely separate OS-temp workspaces materialized from the exact same
`parent_sha` via `git archive` (no shared `.openlocus`, index, trace, or
cache). After treatment creates a workspace-local `.openlocus`, control's
`before_cli` scan would necessarily fail in a shared workspace; also
treatment state may contaminate control. Two workspaces eliminate this.
For each arm: before its FIRST invocation use `before_cli`; after each
invocation use `after_cli`; before repetitions 2..5 use `after_cli`
(workspace-local real `.openlocus` may exist). All ancestors remain
marker-free. Both workspaces are scanned before and after every invocation
and explicit counts/failures are aggregated. Cleanup both workspaces in
`finally`. This path is **synthetic-only** because the `2 < 5` STOP
prevented real headroom execution — no real headroom execution claim is
made.

**Strict per-arm state machine:** each arm of each warm repetition runs as
a fail-closed state machine (in `_run_one_arm`): (1) pre-isolation scan
passes; (2) run `fast-context`; (3) post-fast-context `after_cli` isolation
scan passes; (4) fast-context schema `_valid` is true; (5) ONLY THEN run
`citations validate` on that trusted evidence; (6) an `after_cli` isolation
scan after citation validation (the citation CLI is another invocation)
passes; (7) citation validation is true; (8) only then proceed to the
other arm / next repetition. No untrusted evidence (schema-invalid or
non-isolated) ever reaches the citation CLI. A treatment failure does not
invoke citation/control; a treatment citation failure does not invoke
control; a control failure does not run later repetitions. Any failure
immediately records explicit scans/failures, a fixed private reason bucket,
and returns G_i=0. `TimeoutExpired`/`OSError`/unexpected exceptions from
`run_fast_context`/`validate_citations` are not caught inside the helper —
they propagate to the per-candidate `headroom_for_candidate` boundary where
the existing fail-closed `except` clauses convert them to a fixed reason
bucket (`headroom_subprocess_exception` / `headroom_unexpected_exception`).
Both independent parent workspaces and the first-rep `before_cli` vs later
`after_cli` semantics are preserved.

**Non-object/malformed JSON fail-closed:** `run_fast_context` parses
`json.loads` as `Any`; if the result is not a dict (list/string/number/null),
a safe internal result with `_valid=False`, `_invalid_reason='non_object_json'`,
returncode/latency only is returned — never including arbitrary raw data.
Nonzero exit and malformed JSON similarly return invalid without throwing.
`validate_citations` rejects non-object JSON safely without assigning into a
non-dict or spreading a non-dict with `{**out}`. `TimeoutExpired`, `OSError`,
and unexpected subprocess/validation exceptions are caught at the
per-candidate headroom boundary and converted to a fixed reason bucket
(`headroom_subprocess_exception` / `headroom_unexpected_exception`); the
candidate fails closed, workspaces are cleaned, and the whole audit is never
aborted. Exception details are never published. Integer checks are tightened
to reject `bool` (which is a subclass of `int` in Python) for line numbers,
token counts, diagnostics counts, and citation counts via `type(x) is int`.

**Pack/evidence consistency:** a count match is insufficient. `pack.evidence`
must equal the trusted top-level evidence structurally and in order. The
production Rust construction (`plan.rs`) clones the same `final_evidence`
Vec into both `result.evidence` and `result.pack.evidence`, so they are
always identical in content and order — exact equality is enforced.
`pack.budget_used` must equal top-level `budget_used` since both are built
from the same `latency_ms` / `tokens_estimated` / `remote_cost_estimated`
values in the production Rust construction.

**Byte-exact separate test overlays:** `extract_overlay_test` uses
`_git_bytes` (raw bytes, no newline translation) for separate test files
(commit-added and pre-existing), not `_git(...).encode()` which can normalize
newlines on Windows. A `separate_test_blob_hash` (sha256 of raw git blob
bytes) is enforced in `apply_overlay`: the actual on-disk bytes after write
must hash to exactly this value, proving git blob bytes == overlay bytes ==
on-disk bytes even for CRLF/non-ASCII content. The target path is validated
as relative, with no `..` traversal, and resolved within the workspace
before writing.

## Self-tests

All thirty self-tests pass (synthetic temporary git fixtures only, no
network/provider calls): deterministic enumeration, rule-based filter,
byte-exact test transplant, isolation (no `.git` linkage, OS temp outside
REPO_ROOT, no ancestor marker — real production topology), stable fail/pass
repro, aggregate privacy scan, fail-closed gate behavior, Rust inline test
region detection (including braces in string literals), test-line exclusion
from the production-line count, byte-safe overlay preservation of parent
production + fixed test bytes (raw on-disk byte hash verification, enforced
in real `apply_overlay` via explicit base modes — not just self-tests),
malformed inline module fail-closed rejection, no-fixed-production-bytes-leak
assertion, multiple valid inline test modules fail-closed rejection
(ambiguity), `#[cfg(test)]` attribute false positives in comments / string
literals / raw strings rejected, small (`<100` raw lines) test-only
inline-module change excluded as test-only, lifetime/label boundary (lifetimes
`'a`/`'static` and labels `'label:` not mistaken for char literals — test
region ends before fixed production), ancestor marker rejection (workspace
nested in a `.git` parent rejected), enforced real overlay hash rejection
(wrong-commit workspace rejected via `parent_full_hash`), parent-only headroom
materialization (no fixed implementation bytes in either retrieval arm),
flattened Fast Context evidence schema validation (real `#[serde(flatten)]`
schema — `path`/`start_line`/`end_line`/`content_sha`/`score`/`why`/
`channels` are direct fields plus optional `meta`; nested `core` object
rejected fail-closed; diagnostics exact keys/types; `unknown_channels` empty;
unexpected non-fusion action channels and top-level/per-turn
`disabled_channels` rejected; stale freshness rejected; evidence path resolved
within workspace and file exists), non-vacuous isolation/citation GO
conditions (GO requires `isolation_scans > 0` and `isolation_scan_failures
== 0`), outside-repo workspace topology, **inline overlay base-mode
round-trip** (mode=parent/fixed/parent_dev_patch all succeed on the real
Rust inline repo; wrong workspace or missing dev patch fails closed; unknown
mode rejected — proves each repro path can actually reproduce rather than
necessarily failing), **warm-repetition aggregation** (first-of-five invalid
then later valid still fails; one citation failure still fails; one
post-command isolation failure increments explicit `isolation_scan_failures`
and blocks GO — a later valid run does not erase an earlier failure), and
**after-CLI isolation mode** (workspace-local `.openlocus` directory allowed
only if real non-symlink; file/symlink `.openlocus` always rejected;
`.git` always rejected), **two-arm workspace independence** (treatment and
control materialized in completely separate OS-temp workspaces from the same
`parent_sha` — distinct roots, both parent-exact, no marker/state crossing,
repetition 2 accepts only a real local `.openlocus` dir while rejecting
file/symlink/ancestor markers), **non-object/malformed JSON fail-closed**
(JSON array/string/number/null returns `_valid=False` with
`_invalid_reason='non_object_json'` without throwing or including arbitrary
raw data; `TimeoutExpired`/`OSError`/unexpected exceptions caught at the
per-candidate headroom boundary and converted to a fixed reason bucket;
malformed citation output fails closed; boolean-as-integer rejected for line
numbers, token counts, diagnostics counts, and citation counts), **pack/
evidence consistency** (`pack.evidence` must equal top-level `evidence`
structurally and in order; `pack.budget_used` must equal top-level
`budget_used`), **byte-exact separate test overlays** (separate test
files use `_git_bytes` for exact blob bytes including CRLF/non-ASCII;
`separate_test_blob_hash` enforced in `apply_overlay`; target path validated
as relative/no `..`/within-workspace), and **headroom arm state-machine
ordering / short-circuit** (mocked `run_fast_context`/`validate_citations`
with the real `_do_isolation_scan` driven by workspace marker state proves:
treatment schema invalid → zero citation calls and zero control calls;
treatment post-fast-context isolation failure → zero citation/control and
the failure is counted; treatment citation failure → zero control calls;
control schema invalid → no later repetition — exactly one treatment + one
control fast-context call and one citation call; and the citation CLI's
post-call `after_cli` isolation failure is counted and blocks GO — no
untrusted evidence reaches the citation CLI).

## Validation

- `python -m py_compile eval/decision_experiment_phase1_audit.py` — passed.
- Self-test (`--self-test`) — all 30 passed.
- Public privacy scan (`public_privacy_scan`) — clean
  (`forbidden_public_key_scan_clean: true`). The only field resembling a
  private value is the intentionally-public frozen cutoff SHA, which the
  contract permits and the scanner whitelists.
- The existing public report (`phase1_public_report.json`) was validated
  against the updated report schema/invariants and privacy scan. Its
  aggregate (`865` considered, `2` eligible) and `generated_at` are
  unchanged — these fixes affect only unreachable-after-STOP execution
  paths and the Rust lexer is not changed, so no full real audit re-run
  was warranted.
- `runs/` private tree confirmed gitignored; public artifact is not gitignored.

## Next step

Stage 1 STOPs. Stage 2 (paired agent harness), the live GO thresholds, and the
Defects4J confirmation were not reached and must not run under this frozen
contract — this is an empirical gate result, not a user-approval gate. A future
Stage 1 would require a different mined internal source with enough small,
test-backed product defect fixes — not a weakening of these rules. The two
eligible candidates are insufficient for a cohort (minimum 5).
