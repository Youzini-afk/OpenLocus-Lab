# Interventional Evidence Acquisition Candidate Route

Date: 2026-07-07

Status: `candidate_route_phase1_hard_source_private_pilot_complete_no_claim`

Authorization: `hard_source_local_private_pilot_confirmed_ignored_private_rows`

Route relation: `new_candidate_route_not_reopening_closed_v2_lines`

This note records a Phase 0 candidate-route design and the later minimal Phase 1 local private pilot for interventional evidence acquisition. It is not OpenLocus v3 branding and does not authorize provider/network work, training, runtime/default changes, or method-winner claims.

## Boundary

This candidate route does not reopen HAAE-A2/v2 trace-driven policy, RPM-D2/model scaling, FRK repair, LDI/static support, provider/network, runtime/default, or method-winner routes. Existing closure context remains authoritative; see [`current-route-closure.md`](./current-route-closure.md), [`state-action-trace-v2-bootstrap.md`](./state-action-trace-v2-bootstrap.md), and [`openlocus-v2-rpm-d1-learning-smoke.md`](./openlocus-v2-rpm-d1-learning-smoke.md) instead of duplicating those route histories here.

Phase 1 private pilot output still requires explicit `--confirm-private-output`. Without that flag, the runner must not write private rows. This pilot does not authorize provider/LLM plumbing, runtime/default changes, CI gates, model changes, training, source scans, or README changes.

## Phase 1 local private pilot status

The minimal local pilot runner is `eval/interventional_evidence_acquisition_phase1_local_episode_runner.py`. A confirmed low-resource local run previously wrote private rows only under ignored `runs/` storage after `--confirm-private-output`. The current public aggregate report at `artifacts/interventional_evidence_acquisition_phase1_local_episode_runner/interventional_evidence_acquisition_phase1_local_episode_runner_report.json` was regenerated as a methodology-repair `phase1_preflight` dry run with no private rows written.

The report is aggregate-only: no private row contents, task text, paths, ranges, hashes, snippets, provider payloads, or per-episode details are public. No provider/network actions were authorized or executed, no training or runtime/default change was authorized, no method-winner claim is made, and the next authorized action remains `stop/request next explicit decision`.

## Hard-source preflight status

The hard-source preflight script is `eval/interventional_evidence_acquisition_phase1_hard_source_preflight.py`. It generated `artifacts/interventional_evidence_acquisition_phase1_hard_source_preflight/interventional_evidence_acquisition_phase1_hard_source_preflight_report.json` with status `phase1_hard_source_preflight_no_private_rows`.

This is not a confirmed private capture. It checks 32 synthetic/local hard task shapes across 8 family buckets and publishes only aggregate buckets for balance, structural availability, candidate ambiguity, baseline non-saturation, EvidenceCore summary, and privacy summary. It does not write private rows and does not authorize provider/network work, training, runtime/default changes, new retrieval families, method-winner claims, or route reopening.

## Hard-source private pilot status

The same script now supports explicit `--confirm-private-output` mode. A confirmed local private pilot wrote private rows only under ignored `runs/` storage and updated the same public report to status `phase1_hard_source_private_pilot_complete_no_claim`.

The public report remains aggregate-only: task/action/family count buckets, candidate-found buckets, materialized buckets, evidence-success buckets, baseline/non-saturation buckets, privacy summary, and no-claim attestations. Retrieval-only actions may find candidates but do not count as evidence success without current-source materialization. No provider/network work, training, runtime/default changes, new retrieval families, method-winner claims, or route reopening are authorized.

## Candidate question

Can a tiny, local, randomized intervention over existing evidence-acquisition actions produce clearer product-workflow evidence than passive trace review, while preserving EvidenceCore and privacy invariants?

The intended evidence is decision-quality, not branding: whether controlled action choice helps find current, rematerializable evidence sooner on hard product-workflow episodes.

## Phase 1 local pilot shape

Phase 1 was run as a private randomized local pilot only:

- 24-40 hard product-workflow episodes.
- Maximum 7 existing local actions: `retrieve_bm25`, `retrieve_symbol_regex`, `read_top1`, `read_next_unique_file`, `read_related_test`, `stop`, `abstain`.
- No LLM/provider/network actions.
- No model training or model scaling.
- No new retrieval channel families.
- No runtime/default changes.
- No method-winner, scale, default, or product-readiness claim.

## Private row schema

The confirmed run used a small fail-closed private row shape with:

- `schema_version`: fixed candidate schema id.
- `episode_id`, `step_index`, `randomization_block_id`: private identifiers.
- `task_bucket`: coarse product-workflow task family, not raw prompt text.
- `state`: label-blind pre-action fields such as remaining budget bucket, seen file count bucket, candidate count bucket, ambiguity bucket, and evidence coverage bucket.
- `action`: one of the 7 local actions above.
- `randomization`: eligible action set, assignment policy id, probability bucket, and seed/reference kept private.
- `observation`: cost bucket, file/read result bucket, abstain/stop marker, and failure-safe reason bucket.
- `evidence_core`: private source path, range, content/currentness check result, and rematerialization status.
- `outcome`: post-action success/failure-safe label and reason bucket, filled only after action/offline review.
- `privacy`: private-only markers for prompt/response/snippet/gold/provider/path/range/hash/reference containment.

Private rows stay under ignored `runs/` storage and are not public artifacts.

## Aggregate-only public report shape

The public report is aggregate/sanitized only and contains:

- route/status/authorization fields;
- episode-count and step-count buckets;
- action coverage and randomization health buckets;
- EvidenceCore rematerialization pass/fail buckets;
- success/failure-safe aggregate buckets by action family;
- stop/abstain and budget buckets;
- privacy scan summary;
- stop/go recommendation with no private rows.

The public report must not include private traces, prompts, responses, snippets, gold labels, provider payloads, exact paths, exact ranges, hashes, private refs, raw task text, raw row values, or per-episode details.

## EvidenceCore and privacy invariants

- Counted evidence must rematerialize current source path/range/content/currentness.
- Candidate evidence is not fact until it passes the currentness and content checks.
- Public outputs are aggregate/sanitized only.
- Private traces, prompts, responses, snippets, gold, provider payloads, exact paths, exact ranges, hashes, and private refs stay private.
- State/action fields must remain label-blind; labels/outcomes are post-action or offline-only.

## Phase 0 to Phase 1 decision record

Phase 1 was allowed only after these conditions were met:

1. A separate explicit route decision names this candidate route and authorizes the tiny private pilot.
2. The episode source is bounded to 24-40 hard product-workflow episodes.
3. The action set remains limited to the 7 existing local actions listed above.
4. The private row schema and aggregate-only report contract are accepted before any capture.
5. EvidenceCore rematerialization and privacy checks are required from the first row.
6. The decision explicitly preserves all closed-route boundaries listed in this note.

## Phase 1 stop/go status

Phase 1 completed as a no-claim pilot. It must stop unless a separate later decision is made, because the public report deliberately makes no signal or method-winner claim. Future continuation would require all of:

1. Schema-valid private rows with no label leakage into state/action fields.
2. EvidenceCore rematerialization meets the predeclared minimum needed for counted evidence to be trusted.
3. No public/private privacy boundary failures.
4. Randomization health meets predeclared checks for the tiny pilot's aggregate comparison.
5. Predeclared aggregate stop/go thresholds are met, including a practical aggregate signal that randomized existing-local-action choice improves hard product-workflow evidence acquisition versus the best fixed local-action baseline under the same 7-action, same-budget setup, not merely versus stop/abstain.

Even if all criteria pass, the only possible next step is another explicit route decision. Phase 1 would not authorize runtime/default changes, provider/network work, training, new retrieval families, or method-winner claims.
