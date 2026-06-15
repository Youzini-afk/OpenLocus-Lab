# P52B 源代码支撑局部验证器特征矩阵

> 中文译本待补充。本文档目前保留英文原文，以便内容不丢失。

## English source / 英文原文

# P52B Source-Backed Local Verifier Feature Matrix

P52B reads local source files only for bounded aggregate source-shape heuristic diagnostics and source-feature risk buckets. It is a SCORE-phase-only feature matrix, not a verifier pass/fail phase and not an Evidence producer.

P52B computes source-shape heuristics from bounded candidate spans only. AST/query-dependent features remain unavailable. It stores no raw source, snippets, digests, paths, or spans. Source-feature buckets are diagnostic only; they are not Evidence and do not admit candidates. P52B does not validate EvidenceCore, does not produce a verifier pass/fail or local verifier score, does not prove P51 quality, and does not send source to providers. It does not call an LLM, construct prompts, or make remote calls.

See `docs/en/p52b-source-backed-local-verifier-feature-matrix.md` for the generated detailed report.
