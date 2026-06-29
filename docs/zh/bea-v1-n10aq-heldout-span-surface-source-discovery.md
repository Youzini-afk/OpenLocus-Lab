# BEA-v1-N10AQ Heldout Span-Surface Validation Source Discovery

日期：2026-06-29

BEA-v1-N10AQ 是 bounded local discovery 与 schema sniffing，用来寻找可支持未来 N10AR validation 的 existing heldout/external span-surface row source。它不是 validation。它不运行 N10AO/N10AL metrics、retrieval、reruns、OpenLocus、candidate generation、selector/reranker logic、runtime/default changes 或 downstream/method claims。

## 结果

```text
status: no_go_n10aq_candidate_sources_not_heldout
self-test: 15 / 15
forbidden scan: pass
max scanned entries: 50000
candidate files schema-sniffed: 84
max rows sniffed per file: 5
eligible heldout source count: 0
N10AR authorized: false
```

## Discovery finding

Bounded scan 遵守 approved roots 与 caps。它发现 candidate JSON/JSONL files，并且只 sniff schema metadata。唯一具备 required span-surface shape 的 candidate 被分类为 existing N10 source 或无法与其区分；因此它不是 valid heldout source。其他 candidates schema-incomplete 或 too small，不能用于 N10AR。

Public output 不公开 exact paths、filenames、raw rows、snippets、spans、line values、candidate lists、gold paths、hashes、repo/task identifiers 或 provider payloads。

## 决策

N10AQ 以 heldout validation source discovery No-Go 关闭。Next allowed phase 为 `none_until_heldout_span_surface_rows_are_supplied`。它不授权 N10AR、private reads、validation execution、runtime/default enablement、retrieval/rerun、candidate generation、selector/reranker、P5、BEA-v1-A、method-winner claims 或 downstream-value claims。

## Artifact

- Script: `eval/bea_v1_n10aq_heldout_span_surface_source_discovery.py`
- Report: `artifacts/bea_v1_n10aq_heldout_span_surface_source_discovery/bea_v1_n10aq_heldout_span_surface_source_discovery_report.json`
