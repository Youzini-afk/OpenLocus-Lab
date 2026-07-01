# BEA-v1-HAAE-R2 Small Local Lexical Material Experiment

日期：2026-07-01

BEA-v1-HAAE-R2 是一个 tiny local experiment，只使用已经存在的 R1E private
material。它不创建或 rematerialize candidates，不扫描 source code，不运行 OpenLocus
retrieval，不 clone，不使用 network，不调用 provider/model，不执行 scheduler 或 HAAE
layer，不运行 selector/reranker，也不改变 runtime/default。

## 结果

```text
status: haae_r2_small_local_lexical_material_experiment_complete_r2a_public_audit_authorized
default status: haae_r2_unavailable_no_explicit_r1e_private_material_root
self-test: 15/15
forbidden scan: pass
source lock: HAAE-R1E checkpoint 0135e1f
source status: haae_r1e_bounded_private_material_generation_complete_r2_small_experiment_authorized
private read bucket: count_1_to_10 material groups
private write bucket: count_0
rank sources compared: bm25_like, symbol_overlap, rrf_like
```

默认模式是安全的：没有显式 private-material-root opt-in，就不读取 private、不写入
private，并产生状态 `haae_r2_unavailable_no_explicit_r1e_private_material_root`。

Explicit mode 要求 `--allow-private-material-experiment`、
`--private-material-root <existing-r1e-private-material-root>` 和
`--confirm-aggregate-publication-only`。提供的 root 只读使用，root path 或 basename
绝不发布。

## Experiment

Evaluator 读取已有 R1E material groups，并且只在内存中 join。它使用预先计算的
`rank_pack` rows 和 `outcome_metric` rows，为三个已有 rank sources 计算 aggregate
metrics：

- `bm25_like`
- `symbol_overlap`
- `rrf_like`

公开 report 只记录 buckets：group presence、private row-count buckets、rank-source
trace presence、hit-rate buckets、first-hit position buckets 与 pairwise agreement
buckets。它不发布 task ids、queries、candidate paths、snippets、labels、raw ranks、
scores、hashes、filenames 或 raw rows。

## Stop/go

R2 只授权 **BEA-v1-HAAE-R2A Public Audit Package**。它不授权 R3 scale preflight、
new candidate generation、rematerialization、broad retrieval、scheduler/HAAE-layer
execution、selector/reranker execution、provider/model 或 network use、BEA-v1-A/P5、
runtime/default changes、raw publication 或 method-winner claim。

## Artifact

- Helper：`eval/bea_v1_haae_r2_small_local_lexical_material_experiment.py`
- Report：`artifacts/bea_v1_haae_r2_small_local_lexical_material_experiment/bea_v1_haae_r2_small_local_lexical_material_experiment_report.json`
