# BEA-v1-HAAE-R2AG Explicit Local Bounded Robustness Material Generation

日期：2026-07-01

BEA-v1-HAAE-R2AG Explicit Local Bounded Robustness Material Generation 是 R2AF checkpoint `bad2b33` 之后的 opt-in only 阶段。Source status 为 `haae_r2af_real_file_signal_robustness_material_preflight_complete_r2ag_material_generation_authorized`。

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

Default mode no private read/write/source scan/material generation。Explicit mode 需要 `--allow-r2ag-material-generation`、`--private-output-root <root>` 和 `--confirm-aggregate-only-publication`；private root 必须在 public repo 之外，并且为空或已由本 R2AG package 拥有。

Explicit mode 只扫描 bounded local public corpus manifest/allowlist（`fixtures/r14/repos.lock.jsonl`），并把 private material rows 写入 explicit private output root。Private rows 可以包含 task/candidate/source/snippet/path/gold/outcome/eval material。Ranking 和 candidate selection 不使用 gold paths/spans/hard negatives/outcome labels/task answer labels，也不把 candidate path overlap 作为 rank feature：相关 private rows 包含 `rank_policy_used_gold_bool=false`、`rank_policy_used_path_bool=false`、`gold_private_eval_only_bool=true`。

Public report 保持 aggregate-only public artifact：只记录 source lock、opt-in/default status、target 20 tasks、candidate depth cap 40、private row cap 20000、variant presence、private manifest record count buckets、bounded source scan compliance、无路径的 root/manifest validity buckets、material QA aggregates、gates、readback records 和 stop/go。它不发布 task ids、queries、candidate ids、repo ids、paths、directories、filenames、snippets、line numbers、gold、hard negatives、root path、manifest path、per-row material、exact ranks/scores、top-k/MRR/hit-rate experiment metrics、method/default/scaling claims，也不授权 R2AH experiment。
