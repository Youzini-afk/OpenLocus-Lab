# OpenLocus Current Research Conclusions

Date: 2026-06-13

This is the entry point for the current research-conclusion reports. The Chinese
and English versions are split into separate documents for readability and
maintenance. The older stage-by-stage summaries remain unchanged and are linked
below.

当前研究结论总报告已拆分为中文与英文两份，方便后续阅读和维护。原有阶段摘要与历史长报告继续保留，并在下方链接。

## Main reports

- [中文研究结论](current-research-conclusions.zh.md)
- [English research conclusions](current-research-conclusions.en.md)

## Supporting stage reports

- [Stage-by-stage research summary](research-summary.md)
- [R0-R29 historical research report](final-research-report.md)
- [R29 R26 stress matrix](r29-r26-stress-matrix.md)
- [R45 promotion candidate report](r45-promotion-candidate-report.md)
- [Real-provider P7 summary](real-provider-p7-summary.md)
- [Real-provider CI scale-up P8/P9](real-provider-ci-scale-p8-p9.md)
- [Real-provider CI large-repo slice results zh](real-provider-ci-large-scale.zh.md)
- [Real-provider CI large-repo slice results en](real-provider-ci-large-scale.en.md)
- [P20-LS low-context LLM alias scale-up](p20-llm-large-scale.md)
- [P21-G cross-model context-injection plan](p21-g-cross-model-context-injection.md)
- [P22/P23 evidence-seeking policy surface](p22-p23-policy-surface.md)
- [P25 bucket-routed LLM role policy](p25-bucket-routed-policy.md)
- [P30 Admission Model V3](p30-admission-model-v3.md)

## Current one-line conclusion

OpenLocus has established a quality-and-evidence-gated research direction:
local lexical/symbol/RRF retrieval is the backbone, while models are useful only
when they receive enough code facts to be grounded. L1/L2 blocked global
dense-only, and P20-LS-A blocked low-context/query-only LLM aliases. P22/P23 now
reframes the next phase as evidence-seeking retrieval policy research: preserve
RRF reach, use symbol/regex anchors and guard surfaces to suppress false primary,
route dense/LLM roles by bucket, and keep EvidenceCore as the final fact authority.

OpenLocus 目前已经建立了一条质量与证据双重约束的研究路线：本地
lexical/symbol/RRF 是事实检索主干，模型只有在拿到足够代码事实后才可能有效。
L1/L2 阻断了 global dense-only，P20-LS-A 阻断了低上下文/query-only LLM aliases。
P22/P23 已把下一阶段转成 evidence-seeking retrieval policy research：保留 RRF reach，
用 symbol/regex anchors 与 guard surfaces 压 false primary，按 bucket 路由 dense/LLM roles，
并继续让 EvidenceCore 作为最终事实权威。
