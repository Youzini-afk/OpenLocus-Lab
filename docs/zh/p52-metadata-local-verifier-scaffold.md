# P52 仅元数据本地验证器脚手架

> 中文译本待补充。本文档目前保留英文原文，以便内容不丢失。

## English source / 英文原文

# P52 Metadata-Only Local Verifier Scaffold

P52 inventories metadata-verifier feature availability and candidate-risk
buckets before any source-read or LLM span-narrow phase. It is a SCORE-phase-only
scaffold, not a verifier pass/fail phase.

P52 does not verify source text, does not read files, does not call an LLM,
does not construct prompts, does not validate EvidenceCore, does not produce
evidence, does not produce a verifier pass/fail score, and does not prove P51/P53
quality. Its metadata gates are candidate-risk diagnostics only.

See `docs/en/p52-metadata-local-verifier-scaffold.md` for the generated detailed
report.
