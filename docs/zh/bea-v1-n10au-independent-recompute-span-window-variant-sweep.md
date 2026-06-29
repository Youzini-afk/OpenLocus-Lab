# BEA-v1-N10AU Independent Recompute Exploratory Span-Window Variant Sweep

日期：2026-06-29

BEA-v1-N10AU 在 same scoped private N1 span rows 上独立 recompute N10AS exploratory span-window 的完整 15-variant grid。它只读取 N10AS/N10AT public artifacts 作为 expected aggregate comparison，并只读取 scoped private span-row source 做 recompute。它不 import 或 call N10AS evaluator。

## 结果

```text
status: independent_recompute_span_window_variant_sweep_pass_n10av_authorized
self-test: 14 / 14
forbidden scan: pass
private span rows read: 213
variants recomputed: 15
all N10AS aggregate metrics matched: true
frontier tiers matched: true
N10AS evaluator imported: false
N10AS evaluator called: false
N10AV authorized: true
```

## Matched frontier tiers

N10AU 精确确认 N10AS/N10AT frontier tiers：

| Tier | Variant | top10/top20 | Cost proxy |
| --- | --- | --- | --- |
| low-cost frontier | `pm30` | 18 / 22 | 600 (`low`) |
| balanced frontier | `before25_after75` | 20 / 24 | 1000 (`medium`) |
| balanced frontier | `pm75` | 21 / 25 | 1500 (`medium`) |
| max-recall frontier | `pm200` | 25 / 30 | 4000 (`very_high`) |

全部 15 个 variant aggregates 均匹配 N10AS。Candidate pool/order changed counts 保持为零，没有 rank/order arm sweep，也没有 per-record adaptive windows 或 gold-based window selection。

## Claim boundary

N10AU 仍只是 same-source exploratory N1 span-surface proxy evidence。它不是 heldout validation，不是 N2-equivalent validation，不是 runtime/default behavior，不是 method-winner claim，也不是 downstream-value evidence。

## Handoff

N10AU 只授权 `BEA-v1-N10AV Exploratory Span-Window Variant Sweep Replication Package`，即 public replication/audit package。它不授权 private reads、extra sweeps、new variants、heldout validation claims、runtime/default changes、retrieval/rerun、candidate generation、adaptive tuning、selector/reranker execution、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10au_independent_recompute_span_window_variant_sweep.py`
- Report: `artifacts/bea_v1_n10au_independent_recompute_span_window_variant_sweep/bea_v1_n10au_independent_recompute_span_window_variant_sweep_report.json`
