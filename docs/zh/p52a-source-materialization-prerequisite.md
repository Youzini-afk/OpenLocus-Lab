# P52A 源代码物化 / 局部验证器前置条件

> 中文译本待补充。本文档目前保留英文原文，以便内容不丢失。

## English source / 英文原文

# P52A Source Materialization / Local Verifier Prerequisite

P52A reads local source files only for bounded aggregate materialization
prerequisite diagnostics. It is a SCORE-phase-only evaluator, not a verifier
pass/fail phase.

P52A stores no raw source, snippets, digests, paths, or spans. Source read is
not Evidence, and materialized candidate is not Evidence. P52A does not validate
EvidenceCore, does not produce verifier pass/fail or default/promotion claims,
does not call an LLM, and does not make remote calls.

See `docs/en/p52a-source-materialization-prerequisite.md` for the generated
detailed report.
