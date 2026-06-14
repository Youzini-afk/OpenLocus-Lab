# Real-Provider CI Scale-Up P8/P9

Date: 2026-06-13

This report summarizes the first controlled scale-up of the real-provider
benchmark workflow on GitHub Actions. It intentionally contains no provider
URLs, API keys, raw source, private labels, or evidence excerpts.

## Scope

- Workflow: `real-provider-benchmark.yml`
- Environment: GitHub `production`
- Remote mode: explicitly enabled via `workflow_dispatch`
- View: `path_plus_symbol` only
- Dataset: `ci_smoke`
- Caps per run: 5 tasks, 60 files/repo, 80 records
- EvidenceCore semantics: unchanged
- Promotion: disabled

## Harness fixes during scale-up

1. `ci_smoke` initially produced a valid CI `repo-lock.json`, but R32 only
   accepted JSONL or `{repos: [...]}` lock shapes. The first public P2 run was
   therefore invalid (`repo_count=0`, `remote_calls=0`).
   - Fixed in commit `7072350`.
   - The invalid run is excluded from quality conclusions.
2. GitHub workflow concurrency initially grouped only by stage, so simultaneous
   model runs could cancel/replace pending runs. The group now includes dataset,
   repo, and embedding model.
3. `BAAI/bge-m3` works with SiliconFlow/OpenAI-compatible embeddings but rejects
   the OpenAI `dimensions` request field. The provider and CI now support
   `OPENLOCUS_EMBEDDING_SEND_DIMENSIONS=0`.

## P8a: single public repo, full P2/P3/P4 path

Repo: `py_flask` (`pallets/flask`)

### P2 embedding view bakeoff

Run: `27460969243`

| metric | value |
|---|---:|
| repo_count | 1 |
| remote_calls | 80 |
| FileRecall@1 | 0.800 |
| FileRecall@3 | 1.000 |
| SpanF0.5 | 0.071 |
| primary_false_positive_rate | 0.000 |
| citation_validity | 1.000 |

Interpretation: real dense retrieval has file-level signal on this bounded Flask
slice, but span quality remains weak. Dense remains supporting-only.

### P3 QuIVer readiness

Run: `27461068409`

| metric | value |
|---|---:|
| record_count | 80 |
| remote_calls | 85 |
| BQ_overlap@10 | 0.680 |
| BQ_overlap@50 | 0.728 |
| BQ_vs_f32_MRR | 1.000 |
| sign_entropy_mean | 0.408 |
| quiver_fit | promising |

Interpretation: BQ diagnostics on this slice are more positive than earlier tiny
self-test results. This is still diagnostics only: no Vamana graph, no ANN
quality claim, and no default QuIVer admission.

### P4 anchor prototype

Run: `27461068846`

Best net strategy: `flat_f32__global_mixed_all__anchor_regex`

| metric | value |
|---|---:|
| FileRecall@1 | 1.000 |
| SpanF0.5 | 0.140 |
| added_gold_span | 3 |
| added_false_span | 15 |
| primary_false_positive_rate | 0.000 |
| semantic_trap_hit_rate | 0.000 |
| citation_validity | 1.000 |

Interpretation: anchor-seeding gave strong file recall, but the added_false_span
count exceeded added_gold_span on this public corpus slice. That weakens the
earlier tiny self-test signal and reinforces that dense/QuIVer expansion must
remain blocked from default primary admission.

## P9a: embedding model bakeoff on `py_flask`

All runs used the same repo/task/file/record caps.

| model | run | dim | FileRecall@1 | FileRecall@3 | SpanF0.5 | PFP | citation_validity |
|---|---:|---:|---:|---:|---:|---:|---:|
| `BAAI/bge-m3` | 27461440365 | 1024 | 1.000 | 1.000 | 0.071 | 0.000 | 1.000 |
| `Qwen/Qwen3-Embedding-0.6B` | 27461440036 | 1024 | 1.000 | 1.000 | 0.071 | 0.000 | 1.000 |
| `Qwen/Qwen3-Embedding-4B` | 27461221703 | 2560 | 1.000 | 1.000 | 0.069 | 0.000 | 1.000 |
| `Qwen/Qwen3-Embedding-8B` | 27461512893 | 4096 | 0.800 | 1.000 | 0.071 | 0.000 | 1.000 |

Interpretation: on this small Flask slice, the smaller Qwen model and bge-m3 are
not worse than 8B. Differences are too small and labels too few for ranking
models, but this supports continuing model bakeoff instead of assuming larger is
better.

## P9b: multilingual smoke repos with `BAAI/bge-m3`

| repo | run | FileRecall@1 | FileRecall@3 | SpanF0.5 | PFP | citation_validity |
|---|---:|---:|---:|---:|---:|---:|
| `js_express` | 27461624956 | 0.400 | 0.800 | 0.067 | 0.000 | 1.000 |
| `go_gin` | 27461625351 | 1.000 | 1.000 | 0.107 | 0.000 | 1.000 |
| `rust_ripgrep` | 27461625762 | 0.800 | 0.800 | 0.143 | 0.000 | 1.000 |
| `py_flask` | 27461440365 | 1.000 | 1.000 | 0.071 | 0.000 | 1.000 |

Interpretation: file-level recall is promising across Go/Rust/Python but weaker
on JavaScript Express under the current tiny caps. SpanF0.5 is low everywhere,
so dense remains a file/candidate-supporting channel rather than an evidence or
primary span channel.

## Safety status

- `citation_validity=1.0` in all valid runs.
- All valid reports keep `promotion_ready=false` and
  `default_should_change=false`.
- The workflow upload excludes private labels and corpus lock/task directories.
- No raw source, private labels, provider URL, or API key is uploaded.

## Updated conclusion

The first real-provider CI scale-up supports this refined position:

1. Real embeddings have useful file-level recall signal on bounded public corpus
   slices.
2. Dense-only and anchor-seeded dense are not yet safe as primary span evidence;
   span precision/recall remains weak and P4 added more false spans than gold on
   Flask.
3. QuIVer BQ diagnostics are encouraging enough to continue sharded/prototype
   experiments, but still diagnostic-only.
4. Smaller/cheaper embedding models should remain in the bakeoff; the first
   small slice does not justify defaulting to the largest model.

Next scale step: increase task/record caps on the same 4 smoke repos, then add
P3/P4 for JS/Go/Rust, then move to a nightly-medium subset.
