# C5-F RepoQA Method-Matrix Scale Smoke

Date: 2026-06-21

C5-F is a separate 10-needle scale checkpoint for the RepoQA method-matrix
retrieval smoke. It reuses the C5-E RepoQA asset/needle/clone/retrieval/score
pipeline but keeps C5-E unchanged and writes a distinct C5-F artifact.

## Claim boundary

C5-F is `repoqa_retrieval_method_matrix_scale_smoke_only`: a diagnostic,
aggregate-only external-benchmark-shaped retrieval smoke. It is not an external
benchmark performance claim, leaderboard entry, method winner, default-policy
recommendation, downstream-agent value proof, runtime/retriever/pack/backend
change, or EvidenceCore semantic change.

All no-claim flags remain false: `external_benchmark_performance_claimed`,
`leaderboard_entry_claimed`, `downstream_agent_value_proven`, `promotion_ready`,
`default_should_change`, `baseline_is_policy_candidate`, runtime/retriever/pack/
backend/default-policy/EvidenceCore change flags, `provider_calls_made`, and
`remote_provider_calls_made`.

## Evaluator and artifact

- Evaluator: `eval/c5f_repoqa_method_matrix_scale_smoke.py`
- Artifact:
  `artifacts/c5f_repoqa_method_matrix_scale/c5f_repoqa_method_matrix_scale_report.json`
- Schema: `c5f_repoqa_method_matrix_scale_smoke.v1`
- Status: `repoqa_method_matrix_scale_smoke_pass`
- Phase: `C5-F`
- Needle limit: default 10, hard cap 10
- Methods: `bm25,regex,symbol`
- Baseline for deltas: `bm25`
- Query/gold config labels: `needle_description`, `needle_path_line_range`

Raw RepoQA repo values, commits, descriptions, paths, line ranges, source,
generated JSONL, retrieval evidence rows, stdout/stderr, clone paths, row IDs,
hashes, and provider fields are transient only and never committed or uploaded.

## Real smoke result

```text
python3 -m py_compile eval/c5f_repoqa_method_matrix_scale_smoke.py => PASS
python3 eval/c5f_repoqa_method_matrix_scale_smoke.py --self-test => PASS (191/191 checks)
python3 eval/c5f_repoqa_method_matrix_scale_smoke.py \
  --needle-limit 10 --language-filter python --methods bm25,regex,symbol \
  --out artifacts/c5f_repoqa_method_matrix_scale/c5f_repoqa_method_matrix_scale_report.json => PASS
```

Manual CI run `27909885489`
(`c5-repoqa-method-matrix-scale-smoke`,
`enable_external_benchmark_network=true`, `needle_limit=10`,
`methods=bm25,regex,symbol`) completed successfully. The committed artifact now
mirrors that sanitized aggregate CI report.

Aggregate result:

```text
status: repoqa_method_matrix_scale_smoke_pass
needles_seen: 10
methods_successful: 3
methods_failed: 0
forbidden_scan: pass
provider_calls: 0
bm25: file_recall@10=0.5, mrr=0.369216, span_f0.5@10=0.020817, success_rate=1.0
regex: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0
symbol: file_recall@10=0.0, mrr=0.0, span_f0.5@10=0.0, success_rate=1.0
aggregate_runtime_seconds: bm25=19.018, regex=18.181, symbol=28.251
regex-minus-bm25 file_recall@10 delta: -0.5
symbol-minus-bm25 file_recall@10 delta: -0.5
```

These are smoke diagnostics only, not performance, method-winner, or default-policy claims.

## Manual CI

Workflow: `.github/workflows/c5-repoqa-method-matrix-scale-smoke.yml`.

Manual inputs:

```text
enable_external_benchmark_network=true
needle_limit=10
language_filter=python
methods=bm25,regex,symbol
```

The workflow is `workflow_dispatch` only, uses no provider credential/model
environment, and uploads only the aggregate C5-F report. It is fail-closed:
network-enabled CI must produce pass/partial status, `needles_seen > 0`,
`methods_successful > 0`, and `forbidden_scan.status=pass`.
