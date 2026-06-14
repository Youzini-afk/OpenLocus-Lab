# P21-G1E Remote Embedding Context Smoke

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# P21-G1E Remote Embedding Context Smoke

## Scope

- 16 successful remote workflow runs: 4 embedding models × 4 repos.
- Stage: `p21_embedding_context`.
- Caps: `max_tasks=20`, `max_records=80`, `max_files_per_repo=120`.
- Strategies: `atom_path_symbol`, `atom_signature`, `atom_matched_lines`, `atom_body_window`, `pack1_metadata`, `pack2_evidence_sketch`, `pack3_local_code`, `pack5_contrastive`.

## Safety

- raw_text_stored: `false`
- raw_snippets_committed: `false`
- private_labels_committed: `false`
- artifact_privacy_violations: `0`
- remote_file_filter_applied: `true`
- promotion_ready: `false`
- default_should_change: `false`

## Model-Averaged Strategy Results

| Strategy | Avg FileRecall@5 | Avg SpanF0.5 | Avg PFP | Gold spans | False spans | False:Gold | Avg input chars | Avg remote calls |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| pack2_evidence_sketch | 0.8625 | 0.1260 | 0.0000 | 667 | 2533 | 3.80 | 6135.0 | 100.0 |
| atom_signature | 0.9719 | 0.1032 | 0.0000 | 356 | 2844 | 7.99 | 4141.2 | 100.0 |
| pack1_metadata | 0.9531 | 0.1015 | 0.0000 | 374 | 2826 | 7.56 | 5144.5 | 100.0 |
| atom_matched_lines | 0.7125 | 0.0948 | 0.0000 | 280 | 2120 | 7.57 | 6082.5 | 75.0 |
| pack3_local_code | 0.6281 | 0.0938 | 0.0000 | 467 | 1933 | 4.14 | 9541.8 | 75.0 |
| atom_path_symbol | 0.8250 | 0.0866 | 0.0000 | 320 | 2880 | 9.00 | 5941.8 | 100.0 |
| pack5_contrastive | 0.6094 | 0.0760 | 0.0000 | 407 | 1993 | 4.90 | 11578.5 | 75.0 |
| atom_body_window | 0.0563 | 0.0006 | 0.0000 | 5 | 795 | 159.00 | 33259.0 | 25.0 |

## By Embedding Model

| Model | Best span strategy | Best file strategy | Gold spans | False spans | False:Gold |
|---|---|---|---:|---:|---:|
| BAAI/bge-m3 | pack2_evidence_sketch | pack1_metadata | 816 | 4384 | 5.37 |
| Qwen/Qwen3-Embedding-0.6B | pack2_evidence_sketch | atom_signature | 723 | 4477 | 6.19 |
| Qwen/Qwen3-Embedding-4B | pack2_evidence_sketch | pack1_metadata | 714 | 4486 | 6.28 |
| Qwen/Qwen3-Embedding-8B | pack2_evidence_sketch | atom_signature | 623 | 4577 | 7.35 |

## Conclusion

- `pack2_evidence_sketch` is the strongest model-averaged SpanF0.5 strategy in this smoke.
- `atom_signature` is the strongest model-averaged FileRecall@5 strategy.
- All naked dense context strategies still add far more false spans than gold spans, so dense remains candidate/supporting-only.
- Do not expand naked dense primary. Move to P21-G2E: constrained/fused dense hybrid with symbol/regex/RRF anchors, late fusion, and hard-negative checks.

