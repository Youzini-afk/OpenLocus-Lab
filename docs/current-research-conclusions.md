# OpenLocus Current Research Conclusions / 当前研究结论

Date / 日期: 2026-06-13
Scope / 范围: R0-R45, real-provider P1-P9, and the first GitHub Actions real-provider scale-up.
Status / 状态: Research summary, not a promotion request. / 这是研究结论总结，不是默认策略升级申请。

---

## 0. Executive Research Thesis / 核心研究判断

**中文**

OpenLocus 当前最重要的研究结论不是“语义检索已经解决”，而是：项目已经形成了一个可以安全研究语义检索、QuIVer、LLM-derived views、graph、admission guard 的 evidence-gated 实验体系。这个体系的核心是不变量：

```text
candidate != fact
candidate/supporting channels -> current source read -> content_sha/range validation -> EvidenceCore
```

在这个体系下，真实向量模型已经显示出清晰的**文件级召回信号**，但还没有证明能够安全提供 primary span evidence。RRF 仍是最强 recall base，symbol/regex 仍是 precision anchor，`query_noise_plus_rrf_agree_min` 仍是当前最值得继续研究的 guard candidate。Dense/QuIVer/LLM-derived/graph 都还不能进入默认 primary 路径。

**English**

The most important current finding is not that semantic retrieval is solved. It is that OpenLocus now has a safe, evidence-gated research system for studying semantic retrieval, QuIVer, LLM-derived views, graph signals, and admission guards without weakening the evidence contract.

The invariant remains:

```text
candidate != fact
candidate/supporting channels -> current source read -> content_sha/range validation -> EvidenceCore
```

Within that system, real embedding models now show clear **file-level recall signal**, but they have not yet proven safe as primary span evidence. RRF remains the recall base, symbol/regex remain precision anchors, and `query_noise_plus_rrf_agree_min` remains the strongest current guard candidate. Dense, QuIVer, LLM-derived views, and graph signals must remain candidate/supporting/diagnostic layers for now.

---

## 1. Evidence Strength / 证据强度分层

| Evidence tier / 证据层级 | What it supports / 支持什么 | What it does not support / 不支持什么 |
|---|---|---|
| **Strong / 强**: EvidenceCore, materialization gates, citation validation, CI privacy gates | Safety architecture is working: current-file validation, `content_sha`, strict line ranges, citation validity, RUN/SCORE separation. / 安全架构成立：当前文件校验、内容哈希、严格行范围、引用有效性、RUN/SCORE 分离。 | Does not prove any retrieval strategy should be default. / 不证明任何检索策略应成为默认。 |
| **Strong for failure discovery / 强失败面证据**: R29 on R26 auto-stress 1100 tasks | RRF/symbol/guard/dense_mock/graph failure patterns are visible across broad stress buckets. / RRF、symbol、guard、dense_mock、graph 的失败模式已经在较宽 stress bucket 中暴露。 | R26 labels are weak/mined/deterministic; not human promotion evidence. / R26 标签不是人工 promotion tier。 |
| **Moderate / 中等**: real-provider P8/P9 CI scale-up | Real embeddings show initial, repeatable file-level recall signal on bounded public repo slices; QuIVer BQ diagnostics are worth continuing. / 真实向量在有界 public repo slice 上出现了初步、可复验的文件级召回信号；QuIVer BQ 诊断值得继续。 | Samples are small; span quality and default safety are not proven. / 样本仍小，span 质量和默认安全性未证明。 |
| **Directional / 方向性**: P1-P7 self-tests and bounded runs | Provider, LLM status, local harness, and initial anchor-seeded hypotheses work mechanically. / provider、LLM 状态、harness、anchor-seeded 假设在机制上可跑。 | Tiny/self-test outcomes can be contradicted by larger public corpus runs. / tiny/self-test 结果可能被更大 public corpus 推翻。 |
| **Not quality evidence / 非质量证据**: dense_mock, LLM-generated stress, unavailable QuIVer/TDB | Useful for safety, failure discovery, and plumbing. / 适合安全验证、失败面发现、管线验证。 | Must not be used as semantic quality or promotion evidence. / 不能作为语义质量或 promotion 证据。 |

---

## 2. Main Research Conclusions / 主要研究结论

### 2.1 RRF is still the recall base / RRF 仍是召回底座

**中文**

RRF 在 R26/R29 上仍然是最强 recall channel：FileRecall@1 约 `0.803`，FileRecall@5 约 `0.923`。这说明多路本地 lexical/symbol 信号融合确实能覆盖更多任务。

但 RRF 的核心风险也很明确：primary false-positive 高，R29 中约 `0.453`。也就是说，RRF 适合做 recall base，但不能裸奔成为 primary admission。它需要 guard、anchor 或 admission model。

**English**

RRF remains the strongest recall channel on R26/R29: FileRecall@1 is about `0.803`, and FileRecall@5 is about `0.923`. This confirms that fusing local lexical/symbol channels improves coverage.

Its main risk is also clear: high primary false-positive rate, about `0.453` in R29. RRF is a strong recall base, but it should not directly become primary admission without guards, anchors, or an admission model.

### 2.2 Symbol and regex are precision anchors / Symbol 和 regex 是精度锚点

**中文**

Symbol 在 R29 中保持了 precision-anchor 角色：SpanF0.5 约 `0.291`，primary_false_positive_rate 约 `0.080`。它的问题不是太吵，而是 abstain 高、覆盖不足。因此，symbol extraction repair 是非常有价值的 recall-safe 改进方向。

Regex 也仍然是基础 anchor，但需要 normalization。用户 query 不应该默认当 raw regex；需要区分 literal search、explicit regex search、identifier search、path search。R39/R40 的结果支持 `regex_hybrid_normalized` 继续扩大验证。

**English**

Symbol search remains the precision anchor. In R29 it has SpanF0.5 around `0.291` and primary_false_positive_rate around `0.080`. Its weakness is high abstention and incomplete extraction coverage, not excessive noise. This makes symbol extraction repair a promising recall-safe improvement path.

Regex remains a foundational anchor too, but it needs normalization. User queries should not default to raw regex. The system needs separate modes for literal search, explicit regex search, identifier search, and path search. R39/R40 support continuing validation of `regex_hybrid_normalized`.

### 2.3 `query_noise_plus_rrf_agree_min` is the best current guard candidate / 当前最强 guard candidate 仍是 `query_noise_plus_rrf_agree_min`

**中文**

R29 中 `query_noise_plus_rrf_agree_min` 基本保留了 RRF recall，同时把 RRF 的 primary false-positive 从约 `0.453` 降到约 `0.106`，guard_recall_kill_rate 约 `0.003`。这是目前最清楚的 guard 正信号。

但是它仍然不能 promotion：R23 guard sweep 出现大量 bucket regression，R26/R29 本身也不是人工 high-confidence promotion tier。因此它是“继续深入验证的 guard candidate”，不是默认策略。

**English**

In R29, `query_noise_plus_rrf_agree_min` preserved RRF recall while reducing primary false-positive rate from about `0.453` to about `0.106`, with guard_recall_kill_rate around `0.003`. This is the clearest current guard signal.

It still cannot be promoted. R23 showed many bucket regressions, and R26/R29 are not human-reviewed promotion tiers. It is a strong guard candidate for continued study, not a default strategy.

### 2.4 Real embeddings help file recall but not span evidence yet / 真实向量有文件级召回信号，但还不是 span evidence

**中文**

P8/P9 的 CI scale-up 显示：真实 embedding 在有界 public corpus slice 上出现了初步、可复验的文件级召回信号，但稳定性仍需扩大验证。比如 bounded Flask slice 上 P2 的 FileRecall@1=`0.800`、FileRecall@3=`1.000`；多语言 bge-m3 smoke 中 Go/Python 表现强，Rust 中等，JS Express 更弱。

但 SpanF0.5 很低，典型范围约 `0.067` 到 `0.143`。这说明 dense 当前更像“文件/候选支持通道”，而不是可直接作为 EvidenceCore primary span 的证据通道。

**English**

P8/P9 CI scale-up shows initial, repeatable file-level recall signal on bounded public corpus slices, but stability still needs larger validation. For example, the bounded Flask P2 run achieved FileRecall@1=`0.800` and FileRecall@3=`1.000`; in the multilingual bge-m3 smoke, Go/Python were strong, Rust was moderate, and JavaScript Express was weaker.

However, SpanF0.5 remains low, typically around `0.067` to `0.143`. Dense retrieval is currently a file/candidate-support channel, not a primary span-evidence channel.

### 2.5 Bigger embedding models did not dominate in the first slice / 第一批结果没有证明“大模型更好”

**中文**

P9a 在同一个 Flask slice 上比较了 `BAAI/bge-m3`、`Qwen/Qwen3-Embedding-0.6B`、`Qwen/Qwen3-Embedding-4B`、`Qwen/Qwen3-Embedding-8B`。这个小样本中，8B 没有明显优于小模型；bge-m3 和 Qwen 0.6B/4B 都达到 FileRecall@1=`1.000`，8B 为 `0.800`。

这不能说明小模型一定更好，但足以提醒我们：后续不应默认假设最大 embedding 模型最好，而应在相同任务、corpus、cap 下继续 bakeoff，并同时记录 latency/cost。

**English**

P9a compared `BAAI/bge-m3`, `Qwen/Qwen3-Embedding-0.6B`, `Qwen/Qwen3-Embedding-4B`, and `Qwen/Qwen3-Embedding-8B` on the same Flask slice. In this small sample, the largest model did not dominate: bge-m3 and Qwen 0.6B/4B reached FileRecall@1=`1.000`, while 8B reached `0.800`.

This does not prove smaller models are better, but it is enough to avoid assuming the largest model is best without same-task bakeoffs. Future bakeoffs should compare models on the same tasks, corpus, caps, latency, and cost.

### 2.6 Anchor-seeded dense/QuIVer is promising but not safe yet / Anchor-seeded dense/QuIVer 有希望，但尚不安全

**中文**

早期 tiny/self-test 中，anchor-seeded dense/QuIVer 看起来很乐观：P4 best strategy 曾出现 added_gold=`2`、added_false=`0`。但 P8a 在真实 public Flask slice 上出现了反向信号：FileRecall@1=`1.000`，但 added_gold=`3`、added_false=`15`。

这正是研究 harness 的价值：小样本乐观信号被更真实的 corpus 约束住了。当前结论不是“anchor-seeded 不行”，而是：anchor-seeded 方向仍值得继续，但必须继续 supporting-only，并重点优化 span targeting 与 false-span suppression。

**English**

Early tiny/self-tests made anchor-seeded dense/QuIVer look promising: P4 once showed added_gold=`2` and added_false=`0`. But P8a on a real public Flask slice produced the opposite caution signal: FileRecall@1=`1.000`, but added_gold=`3` and added_false=`15`.

This is exactly why the research harness matters: a small optimistic signal was constrained by a more realistic corpus slice. The conclusion is not that anchor-seeding is useless; it is that anchor-seeded dense/QuIVer must remain supporting-only while span targeting and false-span suppression are improved.

### 2.7 QuIVer is still diagnostic, but BQ signals are no longer empty / QuIVer 仍是诊断阶段，但 BQ 信号不再是空的

**中文**

P3 在真实 embedding 上做了 BQ readiness 诊断。Flask slice 上 BQ_overlap@10=`0.680`、BQ_overlap@50=`0.728`、BQ_vs_f32_MRR=`1.000`，quiver_fit 标记为 `promising`。这说明 BQ/QuIVer 方向值得继续，而不是直接放弃。

但 QuIVer graph/Vamana 后端尚未实现，当前没有 ANN graph quality claim。QuIVer 仍然只能是 diagnostic/prototype-only。

**English**

P3 ran BQ readiness diagnostics on real embeddings. On the Flask slice, BQ_overlap@10=`0.680`, BQ_overlap@50=`0.728`, BQ_vs_f32_MRR=`1.000`, and quiver_fit was marked `promising`. This means the BQ/QuIVer direction is worth continuing.

But the QuIVer graph/Vamana backend is not implemented, and no ANN graph quality claim exists yet. QuIVer remains diagnostic/prototype-only.

### 2.8 Graph expansion remains blocked / Graph expansion 继续 blocked

**中文**

R25/R29/P6 都支持同一结论：graph 不适合默认 expansion。R29 中 graph_basic added_gold=`0`、added_false=`437`。Graph 更可能适合 explainer、rerank feature、impact/test selector，而不是默认 recall expansion。

**English**

R25/R29/P6 support the same conclusion: graph is not safe as default expansion. In R29, graph_basic added_gold=`0` and added_false=`437`. Graph is more likely useful as an explainer, rerank feature, impact signal, or test selector than as default recall expansion.

### 2.9 LLM-derived views are useful for stress and hints, not facts / LLM-derived 适合 stress 和 hint，不适合事实层

**中文**

真实 LLM provider 已经跑通，P5 生成了 derived/stress 结果。但这些输出必须保持 `not_evidence=true`：LLM 不能生成 Evidence，不能生成 gold label，不能做 citation verdict，也不能做 promotion verdict。

当前 LLM 最适合的角色是：query aliases、symbol tags、intent views、failure/stress generation。它可以扩大失败面，但不能替代 EvidenceCore。

**English**

The real LLM provider has run successfully, and P5 generated derived/stress outputs. These outputs must remain `not_evidence=true`: the LLM must not generate Evidence, gold labels, citation verdicts, or promotion verdicts.

The useful role for LLMs is query aliases, symbol tags, intent views, and failure/stress generation. LLMs can expand the failure surface, but they cannot replace EvidenceCore.

---

## 3. Current Hypotheses / 当前研究假设

| Hypothesis / 假设 | Current state / 当前状态 | What would confirm it / 需要什么来确认 |
|---|---|---|
| RRF should remain the recall base. / RRF 应保留为 recall base。 | Strongly supported by R29, but needs guard. / R29 强支持，但必须配 guard。 | Stable recall under guard across human-reviewed and stress tiers. / 在人工与 stress tier 上 guard 后仍稳定召回。 |
| Symbol/regex should be precision anchors. / symbol/regex 应作为 precision anchor。 | Strongly supported. / 强支持。 | Broader symbol repair validation without PFP increase. / 更广 symbol repair 后 false-positive 不升。 |
| Dense should remain supporting-only for now. / dense 目前应保持 supporting-only。 | Current evidence supports this safety boundary; promotion requires larger real-provider validation. / 当前证据支持这个安全边界；promotion 需要更大真实 provider 验证。 | Dense adds gold more than false across larger R26/R38/CI medium slices. / 更大数据上 added_gold > added_false。 |
| Anchor-seeded dense/QuIVer may be safer than global dense. / anchor-seeded dense/QuIVer 可能比 global dense 更安全。 | Plausible but mixed. / 有希望但信号混合。 | P4-like tests on multiple repos show repeatable false-span suppression. / 多 repo 上可复验地抑制 false span。 |
| BQ diagnostics may be compatible with current code-embedding distributions. / BQ 诊断可能适配当前 code embedding 分布。 | Diagnostic signal promising on Flask. / Flask 诊断信号积极。 | Sharded BQ/proto graph beats flat f32 or improves latency without false-span growth. / 分片 BQ/proto graph 在速度/质量上有优势且不增 false。 |
| Smaller embedding models may be enough. / 小 embedding 模型可能足够。 | Initial P9 supports continued bakeoff. / P9 初步支持继续比较。 | Same-task model bakeoff across more repos with latency/cost. / 更多 repo 同任务并记录延迟/成本。 |
| LLM-derived views can expand failures safely. / LLM-derived 可安全扩大失败面。 | Mechanically supported, not quality-proven. / 机制可行，质量未证。 | Derived views add gold or stress coverage without inducing primary hallucinations. / 增加 gold/失败覆盖且不诱导 primary 幻觉。 |

---

## 4. Contradictions and Negative Results / 矛盾信号与负结果

**中文**

这些负结果是目前最有价值的部分之一，因为它们防止研究结论过早乐观：

1. **P4 tiny 乐观信号被 P8a 弱化**：tiny self-test 中 anchor-seeded added_false=`0`，但 public Flask slice 中 added_false=`15`。
2. **Dense file recall 与 span quality 分离**：多个 P8/P9 结果显示 FileRecall 可以很好，但 SpanF0.5 仍低。
3. **RRF recall 与 false-primary 绑定**：RRF 强召回同时携带高 false-primary，说明 admission 比 raw recall 更关键。
4. **Graph expansion 多次 net-negative**：graph_basic 在 R29 中几乎只加 false，不加 gold。
5. **更大 embedding 模型未在首批样本中胜出**：8B 没有压倒 0.6B/4B/bge-m3。
6. **JS Express 表现弱于 Go/Python/Rust**：真实 embedding 质量有语言/框架差异，不能只看平均数。

**English**

These negative results are among the most valuable findings because they prevent premature optimism:

1. **P4 tiny optimism weakened by P8a**: tiny self-test had added_false=`0`; the public Flask slice had added_false=`15`.
2. **Dense file recall and span quality diverge**: P8/P9 show good FileRecall but low SpanF0.5.
3. **RRF recall is coupled with false-primary risk**: raw recall is not enough; admission is critical.
4. **Graph expansion is repeatedly net-negative**: graph_basic mostly adds false spans and almost no gold.
5. **Larger embedding models did not win the first bakeoff**: 8B did not dominate 0.6B/4B/bge-m3.
6. **JS Express underperformed Go/Python/Rust**: embedding quality varies across language/framework buckets.

---

## 5. Current Safe Architecture Boundary / 当前安全边界

**中文**

目前所有研究结论都依赖以下边界继续成立：

- `EvidenceCore` 仍是唯一事实层。
- Dense/QuIVer/graph/LLM-derived 只能产出 candidate/supporting/diagnostic，不直接产出 Evidence。
- Evidence 必须来自当前源文件读取，并通过 `content_sha` 与 line range 校验。
- RUN phase 不读取 private labels；SCORE phase 才读取 labels。
- 真实 provider 只在 `workflow_dispatch + enable_remote_models=true + OPENLOCUS_ALLOW_REMOTE=1` 下运行。
- 报告与 artifacts 不上传 provider URL/key、raw source、private labels、Evidence excerpts。
- unavailable strategy 只能 reason-only，不能输出假质量数字。

**English**

All conclusions depend on preserving these boundaries:

- `EvidenceCore` remains the only authoritative fact layer.
- Dense, QuIVer, graph, and LLM-derived outputs remain candidate/supporting/diagnostic, not Evidence.
- Evidence must come from reading current source files and validating `content_sha` plus line ranges.
- RUN phase must not read private labels; SCORE phase reads labels only after run artifacts exist.
- Real providers run only under `workflow_dispatch + enable_remote_models=true + OPENLOCUS_ALLOW_REMOTE=1`.
- Reports and artifacts must not upload provider URLs/keys, raw source, private labels, or Evidence excerpts.
- Unavailable strategies must be reason-only and must not emit fake quality numbers.

---

## 6. What the Research Has Actually Established / 目前真正建立了什么

**中文**

目前已经比较稳地建立了四件事：

1. **事实层安全约束可执行**：EvidenceCore + materialization + citation validation 不是口号，而是已经贯穿本地检索、store、graph、dense、CI runner 的机制。
2. **本地 lexical/symbol/RRF 仍是主干**：真实模型进场后，并没有取代 RRF/symbol/regex，反而更明确需要它们作为 anchor 与 guard。
3. **真实模型有价值，但角色有限**：embedding 有 file-level signal，LLM 可扩展 stress/derived views，QuIVer BQ 值得继续；但都不能直接进入事实层。
4. **实验体系能发现反例**：P4 → P8a 的变化说明系统可以把 tiny 乐观信号拉回现实，这对长期研究非常重要。

**English**

The research has established four things with reasonable confidence:

1. **The fact-layer safety constraints are executable**: EvidenceCore, materialization, and citation validation are implemented across local retrieval, store, graph, dense, and CI runner paths.
2. **Local lexical/symbol/RRF remain the backbone**: real models did not replace RRF/symbol/regex; they made anchors and guards more important.
3. **Real models are useful but role-limited**: embeddings have file-level signal, LLMs can expand stress/derived views, and QuIVer BQ deserves continuation; none should directly become facts.
4. **The experiment system can find counterexamples**: the P4 → P8a shift shows that the harness can challenge tiny optimistic results with more realistic corpus slices.

---

## 7. Stage Summary Index / 阶段摘要索引

The detailed phase reports are preserved. This section is an index, not a replacement. / 详细阶段报告均保留；本节只是索引，不替代原报告。

### R0-R13: Local evidence kernel and safety scaffolds / 本地事实层与安全脚手架

- R0/R1: local evidence kernel, read/scan/search, trace, citation validation.
- R2: regex/BM25/symbol/RRF local bakeoff.
- R3: StoreHit materialization gate and conservative store.
- R4: DerivedIndexView safety scaffold; derived views are not Evidence.
- R5: deterministic graph scaffold; graph output is not direct Evidence.
- R6: deterministic fast-context orchestration scaffold.
- R7-R10: persistent BM25, AST chunking, quality bakeoff, incremental index.
- R11: TDB Level0 adapter probe; metadata/chunks only, no retrieval quality claim.
- R12: real-repo incremental robustness bench.
- R13: provider/dense safety scaffold with mock embeddings and no remote quality claim.

### R14-R29: Benchmark/failure-surface expansion / benchmark 与失败面扩张

- R14-R16: scaled benchmark foundation, external multi-repo expansion, multi-method bakeoff.
- R17-R19: query router, guard calibration, large/stress guard generalization.
- R20-R23: auto-wide failure-surface dataset, strategy matrix, failure attribution, guard sweep.
- R24-R25: QuIVer/TDB availability probe, dense_mock/graph ablation; graph/dense default expansion blocked.
- R26: auto-stress-1000 static dataset.
- R28: conservative promotion candidate report; no default change.
- R29: R26 strategy matrix; RRF recall strong, symbol precision anchor, query-noise guard promising, graph/dense blocked.

### R30-R45: Real-model readiness and diagnostic expansion / 真实模型准备与诊断扩展

- R30: freeze R29 baseline.
- R31: real embedding provider smoke and safety gates.
- R32: embedding view bakeoff harness.
- R33: QuIVer BQ readiness diagnostics.
- R34-R36: QuIVer/BQ prototype and anchor-seeded dense/quiver experiments.
- R37-R38: LLM-derived views and stress expansion; not Evidence.
- R39-R40: symbol extraction and regex normalization repair tracks.
- R41-R42: graph role research and admission model v2 rules.
- R43-R45: integrated long-run report; no promotion.

### P1-P9: Real-provider and CI scale-up / 真实 provider 与 CI 逐步放大

- P1: real embedding and LLM smoke, provider access validated.
- P2: bounded real embedding view bakeoff.
- P3: real embedding QuIVer BQ readiness.
- P4: real embedding anchor prototype.
- P5: LLM-derived/stress harness with not-evidence boundary.
- P6: repair/admission replay.
- P7: real-provider summary.
- P8/P9: GitHub Actions public corpus scale-up, model bakeoff, and multilingual smoke.

Key detailed reports / 关键详细报告：

- `docs/final-research-report.md` — long R0-R29 historical report.
- `docs/research-summary.md` — stage-by-stage status summary.
- `docs/r29-r26-stress-matrix.md` — R29 matrix and failure clusters.
- `docs/r45-promotion-candidate-report.md` — R30-R45 conclusion checkpoint.
- `docs/real-provider-p7-summary.md` — P1-P6 real-provider summary.
- `docs/real-provider-ci-scale-p8-p9.md` — first CI scale-up results.

---

## 8. Next Research Questions / 下一步研究问题

**中文**

下一步不是 promotion，而是更大、更细、更可复现的验证：

1. 在相同 public task set 上扩大 P8/P9 的 repo/task/record cap，验证 dense file recall 是否稳定。
2. 对 JS/Go/Rust/Python 都跑 P3/P4，不只在 Flask 上看 QuIVer/anchor-seeded 信号。
3. 在同一任务集上继续比较 bge-m3 与 Qwen 0.6B/4B/8B，加入 latency/cost。
4. 把 P5 stress traps 接入 anchored dense/QuIVer 验证，看 added_gold 是否持续大于 added_false。
5. 在 R26/R38 上复验 symbol repair 和 regex normalization，重点看 bucket regression。
6. 把 real dense support score 接入 admission_v2 研究，但只作为 supporting feature。
7. 继续 QuIVer sharding/prototype，直到有 graph/ANN 后端质量证据再谈 QuIVer quality。

**English**

The next step is not promotion. It is larger, more granular, more reproducible validation:

1. Increase P8/P9 repo/task/record caps on the same public task sets to test whether dense file recall is stable.
2. Run P3/P4 across JS/Go/Rust/Python, not only Flask.
3. Continue bge-m3 vs Qwen 0.6B/4B/8B bakeoffs on identical task sets, including latency/cost.
4. Feed P5 stress traps into anchored dense/QuIVer validation and measure whether added_gold consistently exceeds added_false.
5. Re-validate symbol repair and regex normalization on R26/R38, focusing on bucket regressions.
6. Add real dense support scores to admission_v2 research, but only as supporting features.
7. Continue QuIVer sharding/prototype work; do not claim QuIVer quality until graph/ANN backend evidence exists.

---

## 9. Current Bottom Line / 当前一句话总结

**中文**

OpenLocus 目前已经证明了一个安全研究路线：本地 evidence-gated lexical/symbol/RRF 是事实检索主干；真实 embedding、QuIVer、LLM-derived、graph 都有研究价值，但必须作为 supporting/diagnostic/candidate 层存在。下一阶段的关键问题是：在更大 public corpus 与 stress traps 上，anchor-seeded real-model retrieval 能否稳定增加 gold，同时不增加 false-primary 与 false-span。

**English**

OpenLocus has established a safe research direction: local evidence-gated lexical/symbol/RRF retrieval is the backbone, while real embeddings, QuIVer, LLM-derived views, and graph signals are valuable only as supporting/diagnostic/candidate layers for now. The next key question is whether anchor-seeded real-model retrieval can consistently add gold without increasing false-primary or false-span rates on larger public corpora and stress traps.
