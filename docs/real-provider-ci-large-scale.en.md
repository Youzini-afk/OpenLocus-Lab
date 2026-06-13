# Real-Provider CI Large-Repo Slice Results (L1/L2)

Date: 2026-06-13

Status: Research test report, not promotion evidence, no default strategy change.

## 0. Purpose

The previous P8/P9 round only reached small public CI smoke scale: roughly 5 tasks / 80 records / 60 files. This round expands real embeddings to controlled large-repo slices to test:

1. Whether the real provider remains stable under larger CI workloads.
2. Whether dense-only file recall remains stable as scale increases.
3. Whether SpanF0.5 improves to a usable level.
4. Whether primary_false_positive_rate remains controlled.
5. Whether QuIVer BQ readiness and anchor prototypes still show positive signal on large-repo slices.

Important boundary: this is still a **large-repo slice** benchmark, not a full-repo exhaustive benchmark. Each run has task, record, and file caps.

## 1. Safety and Privacy Boundary

- Workflow: `real-provider-benchmark.yml`
- Trigger: `workflow_dispatch`
- Environment: GitHub `production`
- Remote: explicit `enable_remote_models=true`
- Provider view: `path_plus_symbol` only
- Model: `BAAI/bge-m3`
- Provider URL/key: not written to artifacts, docs, or git
- Raw source: not sent and not uploaded
- Private labels: not uploaded
- EvidenceCore semantics: unchanged
- Promotion: disabled

These runs send public repository path/symbol metadata and public query text to the embedding provider. They do not send raw code, provider URLs/keys, private labels, or evidence excerpts.

## 2. Harness Fixes

Two reliability issues were fixed before the larger runs:

1. **R32 remote embeddings were serial and swallowed provider error detail**
   - Fix: batch requests, retries, and sanitized reason codes.
   - Commit: `4ea9025 improve real provider embedding batching`

2. **P2 artifacts counted record embeddings but not query embeddings**
   - Fix: batch query embeddings too and report total `remote_calls` / `remote_requests` / `remote_texts`.
   - Commits: `6c3cdef report real embedding request counts`, `f554ddd raise real provider large test caps`

## 3. L1: Controlled Large-Repo Slice

### 3.1 L1 canary

Repo: `py_django`

Caps: 5 tasks / 80 records / 120 files

Run: `27463000074`

| Metric | Value |
|---|---:|
| provider_status | ok |
| FileRecall@1 | 0.800 |
| FileRecall@3 | 1.000 |
| SpanF0.5 | 0.0179 |
| primary_false_positive_rate | 0.000 |
| citation_validity | 1.000 |

Conclusion: provider and safety boundaries worked, but span quality was already low.

### 3.2 L1 medium caps

Caps: 10 tasks / 100 records / 250 files

| Repo | Run | FileRecall@1 | FileRecall@3 | FileRecall@5 | SpanF0.5 | PFP | Citation |
|---|---:|---:|---:|---:|---:|---:|---:|
| `py_django` | 27463045465 | 0.700 | 0.900 | 0.900 | 0.0089 | 0.000 | 1.000 |
| `rust_deno` | 27463045848 | 0.800 | 0.900 | 0.900 | 0.1042 | 0.000 | 1.000 |
| `ts_nextjs` | 27463104375 | 0.100 | 0.100 | 0.100 | 0.0056 | 0.000 | 1.000 |
| `go_kubernetes` | 27463104726 | 1.000 | 1.000 | 1.000 | 0.0394 | 0.000 | 1.000 |

Conclusion: file recall is highly bucket/repo dependent. Kubernetes, Deno, and Django had file-level signal, while Next.js was weak. SpanF0.5 remained low overall.

### 3.3 L1 max caps

Caps: 20 tasks / 200 records / 500 files

| Repo | Run | FileRecall@1 | FileRecall@3 | FileRecall@5 | SpanF0.5 | PFP | Citation |
|---|---:|---:|---:|---:|---:|---:|---:|
| `py_django` | 27463176417 | 0.750 | 0.900 | 0.950 | 0.0089 | 0.000 | 1.000 |
| `rust_deno` | 27463176822 | 0.000 | 0.000 | 0.000 | 0.0000 | 0.000 | 1.000 |
| `ts_nextjs` | 27463236632 | 0.050 | 0.050 | 0.050 | 0.0050 | 0.000 | 1.000 |
| `go_kubernetes` | 27463236989 | 0.650 | 0.700 | 0.750 | 0.0316 | 0.000 | 1.000 |

Conclusion: after increasing caps, Deno collapsed from 0.8 FileRecall@1 to 0. Dense-only is highly sensitive to slice/cap selection. Django/Kubernetes still had some file recall, but span quality remained weak. Next.js remained weak.

## 4. L1 P3: QuIVer BQ Readiness Subset

Caps: 20 tasks / 200 records / 500 files

| Repo | Run | BQ_overlap@10 | BQ_overlap@50 | BQ_overlap@100 | BQ_vs_f32_MRR | sign_entropy_mean | quiver_fit |
|---|---:|---:|---:|---:|---:|---:|---|
| `py_django` | 27463309315 | 0.605 | 0.679 | 0.791 | 0.790 | 0.623 | promising |
| `go_kubernetes` | 27463309742 | 0.645 | 0.646 | 0.749 | 0.808 | 0.626 | mixed |

Conclusion: BQ diagnostics are non-empty on large-repo slices. Django looks more promising; Kubernetes is mixed. This is still not QuIVer graph/ANN quality evidence: no Vamana graph, no ANN backend quality claim.

## 5. L1 P4: Anchor Prototype Subset

Caps: 20 tasks / 200 records / 500 files

| Repo | Run | Best strategy | FileRecall@1 | FileRecall@3 | SpanF0.5 | added_gold_span | added_false_span | hard_negative_hit_rate | Citation |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| `py_django` | 27463384236 | `flat_f32__source_vs_test_split__anchor_regex` | 0.850 | 0.950 | 0.000 | 0 | 40 | 0.350 | 1.000 |
| `go_kubernetes` | 27463384579 | `flat_f32__global_mixed_all__anchor_regex` | 0.650 | 0.700 | 0.074 | 5 | 44 | 0.100 | 1.000 |

Conclusion: The anchor prototype did not solve the file/span tradeoff. It improved Django FileRecall@1 versus L1 max P2, but Kubernetes was roughly unchanged; both repos added many more false spans than gold. This strongly supports keeping default expansion blocked.

## 6. L2: Larger Large-Repo Slice

Caps: 60 tasks / 1000 records / 2000 files

Each run sent about 1060 embedding texts, batched into about 67 HTTP requests.

| Repo | Run | FileRecall@1 | FileRecall@3 | FileRecall@5 | SpanF0.5 | PFP | Citation | remote_texts | remote_requests |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `py_django` | 27463522968 | 0.250 | 0.283 | 0.283 | 0.0042 | 1.000 | 1.000 | 1060 | 67 |
| `go_kubernetes` | 27463605172 | 0.267 | 0.267 | 0.267 | 0.0223 | 1.000 | 1.000 | 1060 | 67 |
| `ts_nextjs` | 27463605587 | 0.017 | 0.017 | 0.017 | 0.0030 | 1.000 | 1.000 | 1060 | 67 |
| `rust_deno` | 27463711523 | 0.000 | 0.000 | 0.000 | 0.0000 | 1.000 | 1.000 | 1060 | 67 |

Conclusion: once the slice increased to 60 tasks / 1000 records / 2000 files, dense-only file recall became unstable and generally poor. SpanF0.5 stayed extremely low. primary_false_positive_rate was 1.0 on all four repos. Dense-only / global dense is not safe as primary or default.

## 7. Updated Research Conclusions

1. **We have now run larger real-provider tests, but still as large-repo slices rather than full-repo exhaustive benchmarks.**
2. **Real embeddings have candidate/file-level signal on smaller slices, but the signal is not stable.** In L2, Django/Kubernetes dropped to about 0.25 FileRecall@1, while Next.js/Deno were near zero.
3. **In these bge-m3 `path_plus_symbol` dense-only L2 slices, SpanF0.5 did not improve.** The best L2 SpanF0.5 was only about `0.022`.
4. **Dense-only primary is clearly unsafe.** All four L2 repos had PFP=1.0.
5. **Anchor prototype is still not safe for default expansion.** In L1 P4, added_false was much larger than added_gold.
6. **QuIVer BQ diagnostics remain worth continuing, but diagnostic-only.** BQ overlap is non-empty, but there is still no graph/ANN quality evidence.
7. **Citation gates and artifact privacy checks passed on all valid runs.** citation_validity was `1.0`, and uploaded artifacts contained no provider secrets, raw source, private labels, or evidence excerpts.

## 8. Impact on Research Direction

This round moves the conclusion from:

```text
Real embeddings are promising but need larger validation.
```

to:

```text
Real embeddings have candidate/file-level signal, but are unstable on larger slices; dense-only / global dense cannot be primary/default.
```

More specifically:

- Dense/QuIVer must remain supporting-only.
- Research should not keep optimizing global dense top-k alone.
- Next work should focus on:
  - better view construction, not only `path_plus_symbol`;
  - lexical/symbol seeded retrieval;
  - admission_v2 with dense score as a supporting feature only;
  - source/test/generated/vendor sharding;
  - span targeting rather than file recall alone.

## 9. Next Steps

1. Run L2/P21-G multi-view/context-injection comparisons in explicit public/opt-in rich-context mode: raw chunks, snippet windows, signature/body windows, path-symbol-raw hybrids, model profiles, and context packs. Continue excluding secrets, ignored files, provider keys, and private labels/gold answers.
2. Cluster L2 false positives: generated/vendor, test/source confusion, same-name symbol, path-only noise.
3. Add lexical-anchor seeded P2/P4 variants so dense does not run global top-k over 1000 records.
4. Freeze L2 tasks into a reproducible suite to avoid task generation drift.
5. Add span-aware rerank/line localization to P4; file recall alone is not turning into SpanF0.5.

## 10. Bottom Line

These large-repo-slice real-provider tests do not support promotion. They show that global dense-only retrieval is not enough: real embeddings have file-level signal on smaller slices, but larger large-repo slices quickly expose instability, low SpanF0.5, and high primary false-positive risk. Dense must remain a supporting/candidate layer and must not enter the default primary path. The next quality-oriented step is not more metadata-only `path_plus_symbol`; it is richer code context with measured latency/cost and EvidenceCore still serving as final authority.
