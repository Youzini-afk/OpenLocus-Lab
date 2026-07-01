# BEA-v1-HAAE-R2W Content-Identifier Material Experiment

Date: 2026-07-01

BEA-v1-HAAE-R2W Content-Identifier Material Experiment reads only an explicit
existing R2U private material root. Default mode reads and writes no private data.

```text
phase: BEA-v1-HAAE-R2W Content-Identifier Material Experiment
default status: haae_r2w_unavailable_no_explicit_r2u_private_material_root
pass statuses: haae_r2w_content_identifier_material_experiment_complete_r2x_public_audit_authorized_signal_present / haae_r2w_content_identifier_material_experiment_complete_r2x_public_audit_authorized_weak_or_no_signal
self-test: 25/25
source lock: HAAE-R2V checkpoint b8522de
source status: haae_r2v_content_identifier_material_public_audit_package_complete_r2w_material_experiment_authorized
R2U source checkpoint bb95f80
mode: explicit private material root; existing R2U material only; aggregate-only metrics
rank sources: seven rank sources
material context: query_derived_identifier_decoys; real_file_candidate_evidence_bool=false; file_retrieval_claim_bool=false; method_winner_claim_bool=false
boundary: no generation/candidate creation/retrieval/runtime/source scan/CI/network/provider/scheduler/selector/default/method/scaling
next phase: BEA-v1-HAAE-R2X Content-Identifier Material Experiment Public Audit Package
```

The public artifact contains only buckets for positive-hit counts, MRR, median
first positive rank, coverage, pairwise overlap, and signal diagnostics. It does
not publish exact ranks, scores, identifiers, task IDs, queries, labels, paths,
snippets, hashes, or private root values.


Result: content_identifier_signal_bucket `signal_present`, rank_spread_bucket `spread_high`, query/fusion/symbol sources have high bucketed signal while control remains low; still not file retrieval evidence.
