# BEA-v1-HAAE-R1E Bounded Private Experiment Material Generation

日期：2026-07-03

BEA-v1-HAAE-R1E 是第一个允许生成少量真实 private experiment material rows
的 bounded 阶段。它只能 local/manual 执行。不在 CI 中运行，不使用 network、clone、
provider/model call、OpenLocus runtime retrieval，也不改变 runtime/default。

## 结果

```text
status: haae_r1e_bounded_private_material_generation_complete_r2_small_experiment_authorized
default status: haae_r1e_unavailable_no_explicit_material_generation_opt_in
self-test: 16 / 16
forbidden scan: pass
source lock: HAAE-R1D checkpoint 9299b0a
source status: haae_r1d_schema_inventory_complete_no_go_bootstrap_placeholders_only
sample bound: 3-5 tasks, candidate depth <=20
required meaningful groups: task_identity, anchor_source, candidate_pool, rank_pack, evidence_core, outcome_metric
optional meaningful group: span_projection
placeholder-allowed groups: scheduler_action, arm_assignment, safety_probe_signal
```

默认模式是安全的：没有显式 opt-in 就不读取 private、不写 private，并生成
unavailable artifact。显式模式要求 `--allow-private-material-generation`、
`--private-output-root <temp-or-ignored-root>`、`--sample-size <=5`、
`--candidate-depth <=20` 和 `--confirm-private-rows-only`。

## Material generation

Evaluator 使用公开的 R14 sanity fixture 作为 task source，只在 explicit private
mode 中读取对应 labels。它只扫描 R14 repo lock 声明的 bounded local Rust corpus。
随后用确定性的本地 lexical 方法生成 material，不调用 OpenLocus runtime retrieval：

- BM25-like normalized lexical scoring。
- Symbol/exact-token overlap scoring。
- RRF-like merge traces。
- 有界 rank packs 与 evidence windows。
- 使用 private label spans 生成 private outcome rows。

Raw task ids、queries、candidate paths、labels、spans、snippets、scores 与 row
diagnostics 只写入调用者显式提供的 private root。

## Public boundary

提交的 artifact 只包含 aggregate。它只发布 buckets 和 booleans：source lock、
mode、private-root boundary result、sample/depth bounds、recipe、schema group
row-count buckets、rank-source presence、evidence/outcome aggregate buckets、
public manifest safety、claim boundary、gates、synthetic validators、stop/go 与
forbidden scan。

它不发布 concrete private paths、filenames、repo ids、task ids、queries、
candidate names、spans、scores、hashes、labels、snippets、line ranges、rows 或
diagnostics。

## Stop/go

因为 explicit run 通过了 source lock、private-root boundary、local-only/no-network/
no-clone gate、sample/depth bounds、required schema-group material rows、BM25-like
与 RRF-like trace gates、readback check 和 public scanner，R1E 只授权一个 small
local HAAE-R2 experiment。

它不授权 CI execution、provider/model calls、broad replay、scoring claims、
selector/reranker execution、BEA-v1-A/P5、runtime/default changes 或 method-winner
claim。

## Artifact

- Helper：`eval/bea_v1_haae_r1e_bounded_private_experiment_material_generation.py`
- Report：`artifacts/bea_v1_haae_r1e_bounded_private_experiment_material_generation/bea_v1_haae_r1e_bounded_private_experiment_material_generation_report.json`
