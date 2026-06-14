# P21-G2E Remote Dense Hybrid Smoke

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# P21-G2E Remote Dense Hybrid Smoke

P21-G2E tests whether dense context atoms become useful when constrained or fused with RRF/symbol/regex anchors. Dense remains candidate/supporting-only; dense-only rows are diagnostic controls, not promotion candidates.

## Run Set

- successful_runs: `16 / 16`
- embedding_models: `BAAI/bge-m3, Qwen/Qwen3-Embedding-0.6B, Qwen/Qwen3-Embedding-4B, Qwen/Qwen3-Embedding-8B`
- repos: `go_gin, js_express, py_flask, rust_ripgrep`
- tasks_per_run: `[20]`
- dense_strategies: `atom_signature, pack2_evidence_sketch`

## Aggregate Results

| Strategy | Runs | SpanF0.5 avg | FileRecall@5 avg | PFP avg | Gold spans | False spans | False:Gold | ΔSpan vs RRF | Useful runs | Diagnostic only |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| dense_atom_signature_rrf_file_constrained | 16 | 0.162958 | 0.834375 | 0.0 | 315 | 1297 | 4.11746 | 0.012181 | 11 | False |
| dense_pack2_evidence_sketch_symbol_regex_file_constrained | 16 | 0.16181 | 0.74375 | 0.0 | 603 | 1207 | 2.001658 | 0.011034 | 8 | False |
| dense_atom_signature_symbol_regex_file_constrained | 16 | 0.161765 | 0.825 | 0.0 | 303 | 1273 | 4.20132 | 0.010989 | 6 | False |
| dense_pack2_evidence_sketch_rrf_file_constrained | 16 | 0.161041 | 0.803125 | 0.0 | 612 | 1348 | 2.202614 | 0.010265 | 8 | False |
| rrf_dense_pack2_evidence_sketch_late_fusion_anchor_constrained | 16 | 0.156872 | 0.8875 | 0.0 | 833 | 2233 | 2.680672 | 0.006096 | 10 | False |
| query_noise_guard_rrf_dense_pack2_evidence_sketch | 16 | 0.154916 | 0.875 | 0.0 | 822 | 2164 | 2.632603 | 0.00414 | 10 | False |
| rrf_baseline | 16 | 0.150776 | 0.8 | 0.0 | 302 | 2054 | 6.801325 | None | 0 | False |
| rrf_dense_atom_signature_late_fusion_anchor_constrained | 16 | 0.12876 | 0.909375 | 0.0 | 599 | 2432 | 4.0601 | -0.022016 | 5 | False |
| query_noise_guard_rrf_dense_atom_signature | 16 | 0.126572 | 0.903125 | 0.0 | 595 | 2356 | 3.959664 | -0.024204 | 5 | False |
| dense_pack2_evidence_sketch_only | 16 | 0.12546 | 0.8625 | 0.0 | 664 | 2536 | 3.819277 | -0.025316 | 0 | True |
| rrf_plus_dense_pack2_evidence_sketch_supporting | 16 | 0.122496 | 0.8 | 0.0 | 596 | 2470 | 4.144295 | -0.02828 | 0 | False |
| rrf_plus_dense_atom_signature_supporting | 16 | 0.106967 | 0.8 | 0.0 | 449 | 2582 | 5.750557 | -0.043809 | 0 | False |
| dense_atom_signature_only | 16 | 0.102927 | 0.971875 | 0.0 | 355 | 2845 | 8.014085 | -0.047849 | 0 | True |

## Per-Model Selected Strategies

### BAAI/bge-m3

| Strategy | Runs | SpanF0.5 avg | FileRecall@5 avg | Gold | False | Useful runs |
|---|---:|---:|---:|---:|---:|---:|
| rrf_baseline | 4 | 0.151412 | 0.8 | 76 | 513 | 0 |
| dense_atom_signature_rrf_file_constrained | 4 | 0.159594 | 0.85 | 81 | 349 | 2 |
| dense_pack2_evidence_sketch_rrf_file_constrained | 4 | 0.163741 | 0.8125 | 180 | 351 | 2 |
| dense_pack2_evidence_sketch_symbol_regex_file_constrained | 4 | 0.16998 | 0.75 | 175 | 309 | 3 |
| rrf_dense_pack2_evidence_sketch_late_fusion_anchor_constrained | 4 | 0.167801 | 0.8875 | 231 | 547 | 3 |
| dense_atom_signature_only | 4 | 0.105376 | 0.975 | 91 | 709 | 0 |
| dense_pack2_evidence_sketch_only | 4 | 0.1396 | 0.925 | 200 | 600 | 0 |

### Qwen/Qwen3-Embedding-0.6B

| Strategy | Runs | SpanF0.5 avg | FileRecall@5 avg | Gold | False | Useful runs |
|---|---:|---:|---:|---:|---:|---:|
| rrf_baseline | 4 | 0.150176 | 0.8 | 75 | 514 | 0 |
| dense_atom_signature_rrf_file_constrained | 4 | 0.161794 | 0.85 | 80 | 331 | 3 |
| dense_pack2_evidence_sketch_rrf_file_constrained | 4 | 0.162801 | 0.8 | 150 | 337 | 2 |
| dense_pack2_evidence_sketch_symbol_regex_file_constrained | 4 | 0.162479 | 0.7375 | 149 | 302 | 1 |
| rrf_dense_pack2_evidence_sketch_late_fusion_anchor_constrained | 4 | 0.15608 | 0.875 | 206 | 557 | 2 |
| dense_atom_signature_only | 4 | 0.103227 | 0.975 | 89 | 711 | 0 |
| dense_pack2_evidence_sketch_only | 4 | 0.127487 | 0.8375 | 159 | 641 | 0 |

### Qwen/Qwen3-Embedding-4B

| Strategy | Runs | SpanF0.5 avg | FileRecall@5 avg | Gold | False | Useful runs |
|---|---:|---:|---:|---:|---:|---:|
| rrf_baseline | 4 | 0.150183 | 0.8 | 75 | 514 | 0 |
| dense_atom_signature_rrf_file_constrained | 4 | 0.167455 | 0.7875 | 76 | 300 | 3 |
| dense_pack2_evidence_sketch_rrf_file_constrained | 4 | 0.163036 | 0.8 | 152 | 324 | 2 |
| dense_pack2_evidence_sketch_symbol_regex_file_constrained | 4 | 0.161112 | 0.7375 | 153 | 299 | 2 |
| rrf_dense_pack2_evidence_sketch_late_fusion_anchor_constrained | 4 | 0.157175 | 0.9 | 205 | 562 | 2 |
| dense_atom_signature_only | 4 | 0.099878 | 0.9375 | 86 | 714 | 0 |
| dense_pack2_evidence_sketch_only | 4 | 0.127026 | 0.8375 | 165 | 635 | 0 |

### Qwen/Qwen3-Embedding-8B

| Strategy | Runs | SpanF0.5 avg | FileRecall@5 avg | Gold | False | Useful runs |
|---|---:|---:|---:|---:|---:|---:|
| rrf_baseline | 4 | 0.151333 | 0.8 | 76 | 513 | 0 |
| dense_atom_signature_rrf_file_constrained | 4 | 0.162988 | 0.85 | 78 | 317 | 3 |
| dense_pack2_evidence_sketch_rrf_file_constrained | 4 | 0.154588 | 0.8 | 130 | 336 | 2 |
| dense_pack2_evidence_sketch_symbol_regex_file_constrained | 4 | 0.153669 | 0.75 | 126 | 297 | 2 |
| rrf_dense_pack2_evidence_sketch_late_fusion_anchor_constrained | 4 | 0.146431 | 0.8875 | 191 | 567 | 3 |
| dense_atom_signature_only | 4 | 0.103227 | 1.0 | 89 | 711 | 0 |
| dense_pack2_evidence_sketch_only | 4 | 0.107726 | 0.85 | 140 | 660 | 0 |

## Per-Repo SpanF0.5 Selected

| Repo | RRF baseline | atom_signature RRF-file constrained | pack2 RRF-file constrained |
|---|---:|---:|---:|
| go_gin | 0.235076 | 0.134121 | 0.202801 |
| js_express | 0.112611 | 0.152257 | 0.154053 |
| py_flask | 0.115405 | 0.222676 | 0.160535 |
| rust_ripgrep | 0.140012 | 0.142776 | 0.126776 |

## Conclusion

- Best average supporting strategy: `dense_atom_signature_rrf_file_constrained`.
- Dense-only controls are not acceptable as primary/default despite high FileRecall; they remain diagnostic only.
- Constrained dense can improve average SpanF0.5 modestly without PFP increase, but the gain is repo-dependent and false spans remain non-trivial.
- Next LLM rich-context pilot should consume constrained candidate packs, not naked dense outputs.

## Run IDs

- `27484545086` — `BAAI/bge-m3` on `go_gin`
- `27484544445` — `BAAI/bge-m3` on `js_express`
- `27484543793` — `BAAI/bge-m3` on `py_flask`
- `27484545901` — `BAAI/bge-m3` on `rust_ripgrep`
- `27484542465` — `Qwen/Qwen3-Embedding-0.6B` on `go_gin`
- `27484541789` — `Qwen/Qwen3-Embedding-0.6B` on `js_express`
- `27484541177` — `Qwen/Qwen3-Embedding-0.6B` on `py_flask`
- `27484543119` — `Qwen/Qwen3-Embedding-0.6B` on `rust_ripgrep`
- `27484539801` — `Qwen/Qwen3-Embedding-4B` on `go_gin`
- `27484539118` — `Qwen/Qwen3-Embedding-4B` on `js_express`
- `27484538409` — `Qwen/Qwen3-Embedding-4B` on `py_flask`
- `27484540490` — `Qwen/Qwen3-Embedding-4B` on `rust_ripgrep`
- `27484536949` — `Qwen/Qwen3-Embedding-8B` on `go_gin`
- `27484536190` — `Qwen/Qwen3-Embedding-8B` on `js_express`
- `27484535456` — `Qwen/Qwen3-Embedding-8B` on `py_flask`
- `27484537684` — `Qwen/Qwen3-Embedding-8B` on `rust_ripgrep`

