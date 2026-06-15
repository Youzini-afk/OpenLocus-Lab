# P47 请求更多上下文 / Span-Geometry 诊断

> 中文译本待补充。以下内容保留英文原文以便查阅。

## English source / 英文原文

# P47 Request-More-Context / Span-Geometry Diagnostic

- Schema: `p47-request-more-context-v1`
- Generated: placeholder mirror
- Status: `self_test_only`
- Self-test: True
- Remote calls by P47: 0
- Source reads attempted: False
- Source read availability: `not_attempted_first_tranche`
- AST trim availability: `unavailable_no_source_root`

## Purpose

P47 measures whether enlarging candidate line ranges captures gold spans without reading source files or changing Rust/EvidenceCore semantics. It is a diagnostic-only, SCORE-phase follow-on that uses ephemeral metadata from P25/P46.

## Methodology

- Variants: raw candidate span, ±small neighbor window, ±medium neighbor window with width cap, conservative request-more-context gate, and AST/source-trim (unavailable).
- Metrics are aggregate only: reach, absent rate, file-right-span-wrong, repair-after-expansion, line budgets, and gap-type breakdowns.
- No source files are read; no remote model calls are made.
- Gold spans are used only after RUN for aggregate SCORE-phase metrics.

## Safety posture

- No remote model calls are made during P47 evaluation.
- No source files are read and no AST/source trim is attempted.
- Public outputs contain only aggregate counts/rates by strategy, variant, and gap type.
- `promotion_ready=false`, `default_should_change=false`, `evidencecore_semantics_changed=false`, `candidate_not_fact=true`, `remote_calls_by_p47=0`, `source_reads_attempted=false`.

## Next unlocks

- P48 should test source-materialization gates on the same records.
