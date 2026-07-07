# Interventional Evidence Acquisition Phase 2 Comparison Design

日期：2026-07-07

Status: `phase2_small_fair_local_comparison_no_claim`

Authorization：low-resource local pilot 已完成，private rows 只在 ignored `runs/` 下。本文仍不授权 CI changes、model work、provider/network use、runtime/default changes、product promotion 或 method-winner claims。

Latest result：public aggregate-only report [`phase2_small_fair_local_comparison_pilot_report.json`](../../artifacts/phase2_small_fair_local_comparison_pilot/phase2_small_fair_local_comparison_pilot_report.json)，status 为 `phase2_small_fair_local_comparison_no_claim`，recommendation 为 `phase2_positive_screen_no_promotion`。

## Phase 1 说明了什么

Phase 1 有用，但范围有限：

- Local scripts 可以安全运行 tiny experiments。
- Real current-source reads 和 hashes 可以被检查。
- Private rows 保持在 ignored `runs/` storage 下。
- Public reports 保持 aggregate-only。
- 仍然没有证明任何 evidence-finding method 优于其他方法。

Phase 1E 只是 diagnostic screen。它没有排序 policies，也没有提出 method claim。

## 下一个真实问题

如果之后运行更公平的比较，是否有任何 small local evidence-finding strategy 能在 hard tasks 上超过 best fixed local baseline？

比较对象必须是 best fixed local baseline，而不只是 `stop` 或 `abstain` controls。

## Proposed Phase 2 shape

Pilot 使用了该形态：

- 24-40 个 hard tasks。
- 除非另有单独决定，否则使用同样 7 个 local labels/families：
  - `bm25_then_read_top1`
  - `bm25_then_read_next_unique_file`
  - `symbol_regex_then_read_top1`
  - `symbol_regex_then_read_next_unique_file`
  - `read_related_test_when_available`
  - `stop`
  - `abstain`
- 不使用 LLM/provider/network actions。
- 不做 model training。
- 不改 runtime/default。
- 不新增 retrieval families。
- Private rows 只写入 ignored `runs/`。
- Public report 只包含 aggregate 信息。

## 公平比较规则

- 运行前预先声明 success threshold。
- Candidate strategies 必须与 best fixed local baseline 比较。
- Counted success 需要 actual current-source read，并包含 range、content hash、currentness re-read 和 range/content match。
- Candidate found 不算 evidence。
- `stop` 和 `abstain` 必须保持 controls。
- Public reporting 不得包含 exact paths、ranges、hashes、snippets、task text、row IDs、run paths、private manifest paths 或 exact singleton private counts。

## Stop/go outcomes

- `stop_no_claim`：没有超过 best fixed baseline 的 margin。
- `repair_design_no_claim`：instrumentation、task mix 或 privacy boundary 有问题。
- `phase2_positive_screen_no_promotion`：只是 positive screen；仍然没有 product/default claim。
- 除非后续 independent validation 确认，否则没有 method winner。

已完成 pilot 选择 `phase2_positive_screen_no_promotion`。这只表示 aggregate screen 足够正向，可保留 future explicit decision 的可能；它不是 winner、lift、signal、product 或 default claim。

## Forbidden list

Phase 2 design 不授权：

- LLM/provider/network actions。
- Model training、model scaling 或 RPM-D2 work。
- Runtime/default changes。
- New retrieval families。
- CI gates 或 required CI changes。
- Product/default promotion。
- OpenLocus v3 branding。
- 在执行和 independent validation 之前提出 method-winner、signal/lift 或 efficacy claims。
- 重启已关闭的 HAAE-A2/v2、RPM-D2、FRK、LDI/static support、provider/network、runtime/default 或 method-winner routes。

## Decision checkpoint

任何 Phase 2 execution 前，都必须有单独 explicit decision 批准 task set、success threshold、comparison rule、private-row schema 和 public aggregate report shape。
