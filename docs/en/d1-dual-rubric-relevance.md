# D1 Dual-Rubric Relevance (Eval-Layer Scaffold Only)

## Scope and claim boundary

D1 is an **eval-layer scaffold only**. It defines and self-tests a
diagnostic dual-rubric for candidate relevance. It does **not** change
runtime behavior, retriever ranking, pack construction, model calls,
backend storage, default policy, or EvidenceCore semantics.

- Claim level: `eval_layer_rubric_scaffold_only`.
- Rubric version: `d1_dual_rubric_v0`.
- D1 uses **deterministic synthetic / source-backed fixtures only**. It
  does **not** read real P21/private records (deferred to a later D2
  calibration phase).
- This is **not** a benchmark result, **not** a downstream agent value
  claim, **not** a runtime-clean general algorithm claim, **not** an OOD
  temporal support claim, and **not** a QuIVer systems support claim.
- EvidenceCore remains `path + line range + content_sha + score + why +
  channels`; D1 emits no EvidenceCore records and changes none of its
  semantics.

## Dual rubric

D1 separates candidate relevance into two deterministic small-integer
signals:

- **E-score** (semantic / direct-answer evidence): `semantic_direct_match`
  + `answer_bearing_span` (range 0..2).
- **S-score** (dependency / support-structure evidence):
  `import_support` + `dependency_link_support` + `caller_support`
  (range 0..3).

Citation validity, stale source/hash, uncited source, and explicit
no-evidence are **abstention gates** that fire *before* E/S bucket
assignment (per oracle review: invalid/stale citation must force
abstention, and primary evidence must require citation validity).

### Thresholds

- `E_HIGH >= 2`
- `S_HIGH >= 2`
- weak evidence/support if E or S is `>= 1` but below high.

### Classification order (fail-closed)

1. invalid citation, stale source/hash, uncited/no evidence, or explicit
   no-evidence -> `abstained`.
2. E high and citation valid -> `primary_evidence`.
3. S high and E below high -> `dependency_support`.
4. weak nonzero E or S -> `weak_candidates`.
5. else -> `abstained`.

E-high beats S-high: a candidate with both E and S high and a valid
citation is `primary_evidence`, not `dependency_support`. An E-high
candidate with an invalid citation is `abstained` (fail-closed).

## Buckets and legacy aliases

Canonical buckets:

- `primary_evidence`
- `dependency_support`
- `weak_candidates`
- `abstained`

Legacy alias map (kept for compatibility with the existing
expected-behavior enum):

- `dependency_support` -> `supporting_only`
- `abstained` -> `abstain`

## Public artifact (aggregate-only)

The artifact at
`artifacts/d1_dual_rubric_relevance/d1_dual_rubric_relevance_report.json`
is aggregate-only. It contains counts, band counts, reason-code counts,
thresholds, classification order, bucket names, legacy aliases, self-test
check results, no-claim flags, and a forbidden-scan summary.

It does **not** emit task IDs, repo IDs/names, paths/spans/snippets, line
or byte ranges, content hashes, raw candidate text, prompts/responses,
raw private records, labels/qrels, or row-level derived hashes. A strict
forbidden-output scanner runs fail-closed before the JSON artifact is
written.

### No-claim / safety flags

- `aggregate_only_public_artifact=true`, `diagnostic_only=true`,
  `not_evidence=true`.
- `runtime_behavior_changed=false`, `retriever_changed=false`,
  `pack_builder_changed=false`, `model_calls_changed=false`,
  `backend_changed=false`, `default_policy_changed=false`.
- `promotion_ready=false`, `default_should_change=false`,
  `evidencecore_semantics_changed=false`,
  `runtime_clean_general_algorithm_claimed=false`,
  `downstream_agent_value_proven=false`, `ood_temporal_supported=false`,
  `quiver_systems_supported=false`.
- `candidate_text_emitted=false`, `paths_or_spans_emitted=false`,
  `content_sha_emitted=false`, `raw_private_records_read=false`,
  `raw_private_records_persisted=false`,
  `row_level_hashes_emitted=false`,
  `per_candidate_rows_emitted=false`.

## Validation

```text
python3 -m py_compile eval/d1_dual_rubric_relevance.py   => PASS
python3 eval/d1_dual_rubric_relevance.py --self-test     => PASS (46/46 checks)
python3 eval/d1_dual_rubric_relevance.py \
  --out artifacts/d1_dual_rubric_relevance/\
d1_dual_rubric_relevance_report.json                     => PASS
  (status: scaffold_only_self_test_passed,
   forbidden_scan: pass, self_test_passed: true)
python3 scripts/validate_docs_i18n.py                     => PASS
```

## Caveats

- D1 is eval/diagnostic scaffold only. It confers NO empirical support,
  NO benchmark result, NO downstream agent value, NO runtime-clean
  general algorithm claim, NO OOD temporal support, and NO QuIVer
  systems support.
- Synthetic self-test fixtures are deterministic and in-memory only;
  they are never serialized into the public artifact except as aggregate
  counts.
- Reading real P21/private records is explicitly deferred to a later D2
  calibration phase.
