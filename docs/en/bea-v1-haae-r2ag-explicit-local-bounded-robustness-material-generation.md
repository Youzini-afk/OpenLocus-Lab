# BEA-v1-HAAE-R2AG Explicit Local Bounded Robustness Material Generation

Date: 2026-07-01

BEA-v1-HAAE-R2AG Explicit Local Bounded Robustness Material Generation is opt-in only after R2AF checkpoint `bad2b33`. Source status is `haae_r2af_real_file_signal_robustness_material_preflight_complete_r2ag_material_generation_authorized`.

```text
phase: BEA-v1-HAAE-R2AG Explicit Local Bounded Robustness Material Generation
status: haae_r2ag_explicit_local_bounded_robustness_material_generation_complete_r2ah_public_audit_authorized
default status: haae_r2ag_unavailable_no_explicit_material_generation_opt_in
self-test: 27/27
source lock: HAAE-R2AF checkpoint bad2b33
source status: haae_r2af_real_file_signal_robustness_material_preflight_complete_r2ag_material_generation_authorized
mode: opt-in only
default mode: no private read/write/source scan/material generation
explicit mode: explicit private output root; bounded local public corpus manifest/allowlist
bounds: target 20 tasks; candidate depth cap 40; private row cap 20000
variants: symbol_content_ablation/query_token_masking/shuffled_content_control/negative_control_strengthening
rank policy: rank_policy_used_gold_bool=false; rank_policy_used_path_bool=false; gold_private_eval_only_bool=true
public artifact: aggregate-only public artifact; no experiment metrics
stop/go: authorize only R2AH public audit/package; no R2AH experiment
```

## Boundary

Default mode performs no private read/write/source scan/material generation. Explicit mode requires `--allow-r2ag-material-generation`, `--private-output-root <root>`, and `--confirm-aggregate-only-publication`; the private root must be outside the public repo and must be empty or already owned by this R2AG package.

Explicit mode scans only the bounded local public corpus manifest/allowlist (`fixtures/r14/repos.lock.jsonl`) and writes private material rows under the explicit private output root. Private rows may contain task/candidate/source/snippet/path/gold/outcome/eval material. Ranking and candidate selection do not use gold paths/spans/hard negatives/outcome labels/task answer labels or candidate path overlap as rank features: `rank_policy_used_gold_bool=false`, `rank_policy_used_path_bool=false`, and `gold_private_eval_only_bool=true` are included in private rows where relevant.

The public report remains aggregate-only: it records source lock, opt-in/default status, target 20 tasks, candidate depth cap 40, private row cap 20000, variant presence, private manifest record count buckets, bounded source scan compliance, root/manifest validity buckets without paths, material QA aggregates, gates, readback records, and stop/go only. It publishes no task ids, queries, candidate ids, repo ids, paths, directories, filenames, snippets, line numbers, gold, hard negatives, root path, manifest path, per-row material, exact ranks/scores, top-k/MRR/hit-rate experiment metrics, method/default/scaling claims, or R2AH experiment authorization.
