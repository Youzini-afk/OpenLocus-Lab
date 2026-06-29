# BEA-v1-N6XR Explicit Bounded Candidate-Pool Recapture Smoke

日期：2026-06-28

BEA-v1-N6XR 是 N6G 关闭 public-source route 之后的显式 bounded candidate-pool recapture smoke。它是 fail-closed preflight：检查能否在不读取 private、不运行 retrieval、不联网、不做 full P4L reconstruction、不执行 selector/reranker、不做 counterfactual、不改 policy/runtime、不生成或 materialize candidate pools 的前提下，本地 recapture 40 个固定 N4/N5 cases。

## 结果

```text
status: no_go_n6xr_requires_full_rerun_or_unavailable_mapping
self-test: 19 / 19
forbidden scan: pass
N4 case count: 40
N5 arm count: 4
bounded replay command identified: false
public arm outcome rows written: 0
N7 authorized: false
```

## 为什么 smoke 在执行前停止

N6XR 没有发现 bounded local recapture path。Public N4 case identifiers 只是 N2 sanitized rows 上的 positional ids；没有 raw-record join key。Public artifacts 不包含 candidate pools、raw ranks 或 raw order fields。所需的 N2-to-raw mapping 与 P4L private reconstruction 在当前授权的 public-only boundary 下本地不可用。

最小 replay route 需要对 locked 272-record denominator 做 full P4L reconstruction，包括 network access、repository clones、OpenLocus baseline retrieval 和 full rerun scope。这超出了 N6XR 的 bounded 40-case smoke authorization。

## Records emitted

Artifact 记录：

- N4/N5/N6/N6F/N6G input artifacts 及其 expected statuses；
- 40 cases 与 4 arms 的 bounded replay preflight；
- positional case ids 与 missing raw join keys 导致的 mapping unavailability；
- 不读取也不列出 private files 的 private inventory summary；
- 显示需要 full P4L reconstruction 的 replay cost boundary；
- canary recapture 未执行；
- private/public/candidate-pool rows written 全为 0；
- 空的 `public_arm_outcome_records`；
- 四个 arms 都标记为 `not_evaluated_no_candidate_pools`。

## 决策

N6XR 在执行前关闭。它并不表示 method failed；它表示在 bounded authorization 内无法重建所需 data surface。下一阶段为 `none_until_bounded_replay_path_or_exact_public_160_row_source_exists`。N6XR 不授权 N7、N6 rerun、full rerun、retrieval、private reads、candidate-pool generation/materialization、selector/reranker execution、counterfactuals、P5、BEA-v1-A、runtime/default changes、method-winner 声明或 downstream-value 声明。

## Artifact

- Script: `eval/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke.py`
- Report: `artifacts/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke/bea_v1_n6xr_explicit_bounded_candidate_pool_recapture_smoke_report.json`
