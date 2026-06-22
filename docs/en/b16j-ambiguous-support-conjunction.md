# B16-J Ambiguous-Support Conjunction Live-Provider Smoke (Public Aggregate-Only Artifact)

## Scope and claim boundary

B16-J is the LAST B16 atom-redesign attempt. It constructs ambiguous-support
tasks where support-only is designed to withhold target binding at the full-
prompt level: each task has multiple safe plausible candidate files/symbols
with role-neutral file names, and the same abstract support rule applies
plausibly to multiple candidates.

- Claim level: `ambiguous_support_conjunction_downstream_smoke_only`.
- Mode: `public_aggregate_synthetic_task_family_matrix`; phase `B16-J`.
- Status enum: `ambiguous_support_conjunction_smoke_pass` on live success;
  `blocked_remote_not_enabled` / `unavailable_no_local_provider_env` when
  remote opt-in not satisfied; `provider_call_failed` /
  `structured_action_parse_failed` / `paired_run_failed` /
  `fail_forbidden_scan` on failures.
- B16-J is **eval/diagnostic only**. Allowed: bounded live-provider behavior
  on synthetic ambiguous-support file-choice tasks. Forbidden: downstream
  value proof, BEA superiority, method/default/winner, benchmark performance,
  real-user-task claim, calibration, promotion, runtime/retriever/pack/
  backend/default-policy/EvidenceCore change.

## Arms

1. **`control_sparse`**: no atoms.
2. **`ambiguous_target_only`**: private target-role file cue + target symbol cue; no support.
3. **`ambiguous_support_only`**: support module cue + ambiguous support rule;
   no target-role filename/symbol/unique noun/exact answer/edit instruction.
4. **`ambiguous_distractor_plus_support`**: private distractor-role binding + support + rule; wrong binding.
5. **`ambiguous_target_plus_support`**: private target-role binding + support + rule (conjunction arm).

Primary contrasts: `ambiguous_target_plus_support` vs `ambiguous_support_only`,
vs `ambiguous_target_only`, vs `ambiguous_distractor_plus_support`.

## Ambiguous support design

Both role-neutral candidate files contain the same symbol. The support rule
applies plausibly to both. Support-only full prompt is self-tested to avoid
target-role lexical cues, target filename, target symbol, unique noun, exact
answer, edit instruction, or test path/name.

## Validation

```text
python3 -m py_compile eval/b16j_ambiguous_support_conjunction.py  => PASS
python3 eval/b16j_ambiguous_support_conjunction.py --self-test  => PASS (329/329 checks)
python3 eval/b16j_ambiguous_support_conjunction.py --out ...  => PASS
  (status: blocked_remote_not_enabled, forbidden_scan: pass,
   self_test_passed: true, phase: B16-J,
   bea_superiority_claimed: false, support_cue_ambiguous: true)
python3 scripts/validate_docs_i18n.py  => PASS
git diff --check  => PASS
```

## Manual CI result

Manual real-provider CI run `27953321504` passed: 8 tasks x 5 arms = 40 live provider calls; forbidden scan pass; private SCORE/event manifests each have `record_count=40` and `path_publicly_serialized=false`; 329/329 self-tests. Results: `control_sparse` solve/test=0.0, selected_target_file_rate=0.125, wrong_file_edit_rate=0.875; `ambiguous_target_only` solve/test=0.0, selected_target_file_rate=1.0; `ambiguous_support_only` solve/test=0.25, selected_target_file_rate=0.25, selected_distractor_file_rate=0.625, wrong_file_edit_rate=0.75; `ambiguous_distractor_plus_support` solve/test=0.625, selected_target_file_rate=0.625, selected_distractor_file_rate=0.375; `ambiguous_target_plus_support` solve/test=1.0, selected_target_file_rate=1.0, wrong_file_edit_rate=0.0. Primary deltas for `ambiguous_target_plus_support`: vs `ambiguous_support_only` solve/test delta=+0.75, wrong_file_edit_rate delta=-0.75, selected_target_file_rate delta=+0.75; vs `ambiguous_target_only` solve/test delta=+1.0; vs `ambiguous_distractor_plus_support` solve/test delta=+0.375, wrong_file_edit_rate delta=-0.375. Mechanism summary: `target_support_conjunction_required_count=6`, `support_only_sufficient_count=2`, `target_only_sufficient_count=0`, `distractor_hurts_count=3`, `ambiguous_support_wrong_binding_count=6`, `wrong_file_selection_count=6`, `all_arms_solved_count=0`, `sparse_solved_count=0`. Interpretation: after role-neutral filenames and full-prompt leakage tests, B16-J finally isolated a bounded target+support conjunction signal on this synthetic slice; support-only was no longer sufficient on most tasks (2/8), target-only solved 0/8, and adding target binding to ambiguous support solved 8/8. This is still a smoke-level synthetic live-provider mechanism result, not downstream value proof, BEA superiority, method-winner/default, benchmark/performance, calibration, promotion, or runtime/EvidenceCore change.

## Caveats

- B16-J is eval/diagnostic only. NOT downstream value/BEA superiority/method
  winner/default/benchmark/calibration/promotion/runtime/EvidenceCore claim.
- Support cue is designed to be ambiguous by construction; support-only withholds
  target binding unless the live model can infer it despite that design.
- Bounded synthetic sample. Sufficiency bounded to "on this bounded synthetic
  ambiguous-support file-choice slice".
- All no-claim/no-runtime-change flags false. Live-run flags true only on live
  run. No runtime/retriever/pack/model/backend/default-policy files modified.
