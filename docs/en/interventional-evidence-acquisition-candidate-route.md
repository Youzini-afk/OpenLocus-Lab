# Interventional Evidence Acquisition Candidate Route

Date: 2026-07-07

Status: `candidate_route_design_only`

Authorization: `design_only_not_implementation`

Route relation: `new_candidate_route_not_reopening_closed_v2_lines`

This note records a Phase 0 candidate-route design for interventional evidence acquisition. It is not OpenLocus v3 branding, not an implementation authorization, and not a public artifact/report creation step.

## Boundary

This candidate route does not reopen HAAE-A2/v2 trace-driven policy, RPM-D2/model scaling, FRK repair, LDI/static support, provider/network, runtime/default, or method-winner routes. Existing closure context remains authoritative; see [`current-route-closure.md`](./current-route-closure.md), [`state-action-trace-v2-bootstrap.md`](./state-action-trace-v2-bootstrap.md), and [`openlocus-v2-rpm-d1-learning-smoke.md`](./openlocus-v2-rpm-d1-learning-smoke.md) instead of duplicating those route histories here.

Phase 1 requires a separate explicit route decision. Nothing in Phase 0 authorizes artifacts, scripts, evaluators, schema validators, row/report creation, trace capture, retrieval implementation, provider/LLM plumbing, runtime/default changes, CI gates, model changes, training, source scans, or README changes.

## Candidate question

Can a tiny, local, randomized intervention over existing evidence-acquisition actions produce clearer product-workflow evidence than passive trace review, while preserving EvidenceCore and privacy invariants?

The intended evidence is decision-quality, not branding: whether controlled action choice helps find current, rematerializable evidence sooner on hard product-workflow episodes.

## Phase 1 shape, if later authorized

Phase 1 would be a private randomized local pilot only:

- 24-40 hard product-workflow episodes.
- Maximum 7 existing local actions: `retrieve_bm25`, `retrieve_symbol_regex`, `read_top1`, `read_next_unique_file`, `read_related_test`, `stop`, `abstain`.
- No LLM/provider/network actions.
- No model training or model scaling.
- No new retrieval channel families.
- No runtime/default changes.
- No method-winner, scale, default, or product-readiness claim.

## Private row schema proposal

If Phase 1 is explicitly authorized, private rows may use a small fail-closed schema such as:

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

This is a proposal only. Phase 0 creates no row artifact and no validator.

## Aggregate-only public report shape

If Phase 1 is later run, any public report should be aggregate/sanitized only, for example:

- route/status/authorization fields;
- episode-count and step-count buckets;
- action coverage and randomization health buckets;
- EvidenceCore rematerialization pass/fail buckets;
- success/failure-safe aggregate buckets by action family;
- stop/abstain and budget buckets;
- privacy scan summary;
- stop/go recommendation with no private rows.

The public report must not include private traces, prompts, responses, snippets, gold labels, provider payloads, exact paths, exact ranges, hashes, private refs, raw task text, raw row values, or per-episode details. Phase 0 creates no report.

## EvidenceCore and privacy invariants

- Counted evidence must rematerialize current source path/range/content/currentness.
- Candidate evidence is not fact until it passes the currentness and content checks.
- Public outputs are aggregate/sanitized only.
- Private traces, prompts, responses, snippets, gold, provider payloads, exact paths, exact ranges, hashes, and private refs stay private.
- State/action fields must remain label-blind; labels/outcomes are post-action or offline-only.

## Phase 0 to Phase 1 go criteria

Phase 1 may be considered only if all are true:

1. A separate explicit route decision names this candidate route and authorizes the tiny private pilot.
2. The episode source is bounded to 24-40 hard product-workflow episodes.
3. The action set remains limited to the 7 existing local actions listed above.
4. The private row schema and aggregate-only report contract are accepted before any capture.
5. EvidenceCore rematerialization and privacy checks are required from the first row.
6. The decision explicitly preserves all closed-route boundaries listed in this note.

## Phase 1 stop/go criteria

If Phase 1 is later authorized and completed, stop unless the private pilot shows all of:

1. Schema-valid private rows with no label leakage into state/action fields.
2. EvidenceCore rematerialization meets the predeclared minimum needed for counted evidence to be trusted.
3. No public/private privacy boundary failures.
4. Randomization health meets predeclared checks for the tiny pilot's aggregate comparison.
5. Predeclared aggregate stop/go thresholds are met, including a practical aggregate signal that randomized existing-local-action choice improves hard product-workflow evidence acquisition versus the best fixed local-action baseline under the same 7-action, same-budget setup, not merely versus stop/abstain.

Even if all criteria pass, the only possible next step is another explicit route decision. Phase 1 would not authorize runtime/default changes, provider/network work, training, new retrieval families, or method-winner claims.
