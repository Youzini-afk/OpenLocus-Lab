# OpenLocus 当前研究结论

日期：2026-06-13

范围：R0-R45、real-provider P1-P9、P8/P9 CI scale-up、L1/L2 真实-provider 大仓库 slice 测试、P20-LS/P20-LS-A 低上下文 LLM query-alias 结果，以及 P21-G 跨模型上下文注入研究转向。

状态：研究结论总结，不是 promotion request，不是默认策略升级申请。

---

## 0. 核心研究判断

OpenLocus 当前最重要的研究结论不是“语义检索已经解决”，而是：项目已经形成了一个可以在不破坏证据契约的前提下研究语义检索、QuIVer、LLM-derived views、graph、admission guard 的 evidence-gated 实验体系。

当前研究姿态要转为质量/效率优先，只保留必要安全边界，而不是继续让模型缺上下文。在 public corpus 或明确 opt-in 的远程 runs 中，可以给模型更丰富的代码上下文：raw snippets、path/symbol/signature metadata、neighbor windows、top-k local candidates 和 retrieval scores，只要排除 secrets、ignored files、provider keys、private labels/gold answers。

这个体系的核心不变量是：

```text
candidate != fact
candidate/supporting channels -> current source read -> content_sha/range validation -> EvidenceCore
```

在这个体系下，真实向量模型已经显示出**候选/文件级召回信号**，但 L1/L2 大型 slice 测试也显示：dense-only/global dense 在更大规模下不稳定，SpanF0.5 很低，primary_false_positive 风险高。P20-LS-A 也显示：低上下文/query-only LLM aliases 不够。RRF 仍是最强 recall base，symbol/regex 仍是 precision anchor，`query_noise_plus_rrf_agree_min` 仍是当前最值得继续研究的 guard candidate。Dense/QuIVer/LLM-derived/graph 暂时仍只能是 candidate/supporting/diagnostic 层，但 P21-G 应该测试跨模型 context injection，而不是继续只给 metadata-only 模型输入，也不是做单模型 token sweep。

---

## 1. 证据强度分层

| 证据层级 | 支持什么 | 不支持什么 |
|---|---|---|
| **强：EvidenceCore、materialization gates、citation validation、CI privacy gates** | 事实权威链路成立：当前文件校验、内容哈希、严格 line range、citation validity、RUN/SCORE 分离、secrets/private-label 排除。 | 不证明任何检索策略应成为默认，也不应在 public/opt-in runs 中强制低上下文模型输入。 |
| **强失败面证据：R29 on R26 auto-stress 1100 tasks** | RRF、symbol、guard、dense_mock、graph 的失败模式已经在较宽 stress bucket 中暴露。 | R26 labels 是 weak/mined/deterministic，不是人工 promotion evidence。 |
| **中等：real-provider P8/P9 CI scale-up** | 真实向量在有界 public repo slice 上出现了初步、可复验的文件级召回信号；QuIVer BQ 诊断值得继续。 | 样本仍小，span quality 与 default safety 未证明。 |
| **中等偏强负证据：L1/L2 large-repo slice** | dense-only/global dense 在更大 slice 上不稳定，L2 四个 repo 的 PFP 都为 `1.0`，SpanF0.5 极低。 | 仍不是 full-repo exhaustive benchmark；不证明 rich raw-code embedding views 无效。 |
| **方向性：P1-P7 self-tests 与 bounded runs** | provider、LLM status、local harness、anchor-seeded 假设在机制上可跑。 | tiny/self-test 结果可能被更大 public corpus 推翻。 |
| **非质量证据：dense_mock、LLM-generated stress、unavailable QuIVer/TDB** | 适合失败面发现与管线验证。 | 不能作为 semantic quality 或 promotion evidence。 |

---

## 2. 主要研究结论

### 2.1 RRF 仍是召回底座

RRF 在 R26/R29 上仍然是最强 recall channel：FileRecall@1 约 `0.803`，FileRecall@5 约 `0.923`。这说明多路本地 lexical/symbol 信号融合确实能覆盖更多任务。

但 RRF 的核心风险也很明确：primary false-positive 高，R29 中约 `0.453`。也就是说，RRF 适合做 recall base，但不能裸奔成为 primary admission。它需要 guard、anchor 或 admission model。

### 2.2 Symbol 和 regex 是精度锚点

Symbol 在 R29 中保持了 precision-anchor 角色：SpanF0.5 约 `0.291`，primary_false_positive_rate 约 `0.080`。它的问题不是太吵，而是 abstain 高、覆盖不足。因此，symbol extraction repair 是非常有价值的 recall-safe 改进方向。

Regex 也仍然是基础 anchor，但需要 normalization。用户 query 不应该默认当 raw regex；需要区分 literal search、explicit regex search、identifier search、path search。R39/R40 的结果支持 `regex_hybrid_normalized` 继续扩大验证。

### 2.3 当前最强 guard candidate 仍是 `query_noise_plus_rrf_agree_min`

R29 中 `query_noise_plus_rrf_agree_min` 基本保留了 RRF recall，同时把 RRF 的 primary false-positive 从约 `0.453` 降到约 `0.106`，guard_recall_kill_rate 约 `0.003`。这是目前最清楚的 guard 正信号。

但是它仍然不能 promotion：R23 guard sweep 出现大量 bucket regression，R26/R29 本身也不是人工 high-confidence promotion tier。因此它是“继续深入验证的 guard candidate”，不是默认策略。

### 2.4 真实向量有文件级召回信号，但还不是 span evidence

P8/P9 的 CI scale-up 显示：真实 embedding 在有界 public corpus slice 上出现了初步、可复验的文件级召回信号。比如 bounded Flask slice 上 P2 的 FileRecall@1=`0.800`、FileRecall@3=`1.000`；多语言 bge-m3 smoke 中 Go/Python 表现强，Rust 中等，JS Express 更弱。

但后续 L1/L2 大型 slice 测试削弱了这个乐观信号：当扩大到 60 tasks / 1000 records / 2000 files 后，Django/Kubernetes 的 FileRecall@1 降到约 `0.25`，Next.js/Deno 接近 `0`，四个 repo 的 primary_false_positive_rate 都是 `1.0`，SpanF0.5 最高也只有约 `0.022`。这说明 dense 当前更像“候选支持通道”，而不是可直接作为 EvidenceCore primary span 的证据通道。

### 2.5 第一批结果没有证明“大模型更好”

P9a 在同一个 Flask slice 上比较了 `BAAI/bge-m3`、`Qwen/Qwen3-Embedding-0.6B`、`Qwen/Qwen3-Embedding-4B`、`Qwen/Qwen3-Embedding-8B`。这个小样本中，8B 没有明显优于小模型；bge-m3 和 Qwen 0.6B/4B 都达到 FileRecall@1=`1.000`，8B 为 `0.800`。

这不能说明小模型一定更好，但足以提醒我们：后续不应默认假设最大 embedding 模型最好，而应在相同任务、corpus、cap 下继续 bakeoff，并同时记录 latency/cost。

### 2.6 Anchor-seeded dense/QuIVer 有希望，但尚不安全

早期 tiny/self-test 中，anchor-seeded dense/QuIVer 看起来很乐观：P4 best strategy 曾出现 added_gold=`2`、added_false=`0`。但 P8a 在真实 public Flask slice 上出现了反向信号：FileRecall@1=`1.000`，但 added_gold=`3`、added_false=`15`。

L1 P4 进一步强化了 blocked 结论：`py_django` best anchor strategy added_gold=`0`、added_false=`40`；`go_kubernetes` added_gold=`5`、added_false=`44`。

这正是 research harness 的价值：小样本乐观信号被更真实的 corpus 约束住了。当前结论不是“anchor-seeded 不行”，而是：anchor-seeded 方向仍值得继续，但必须继续 supporting-only，并重点优化 span targeting 与 false-span suppression。

### 2.7 QuIVer 仍是诊断阶段，但 BQ 信号不再是空的

P3 在真实 embedding 上做了 BQ readiness 诊断。Flask slice 上 BQ_overlap@10=`0.680`、BQ_overlap@50=`0.728`、BQ_vs_f32_MRR=`1.000`，quiver_fit 标记为 `promising`。这说明 BQ/QuIVer 方向值得继续，而不是直接放弃。

L1 P3 在更大 slice 上仍有非空 BQ 诊断信号：Django 标记为 `promising`，Kubernetes 为 `mixed`。这仍只是 BQ diagnostic，不是 QuIVer graph/ANN quality。

但 QuIVer graph/Vamana 后端尚未实现，当前没有 ANN graph quality claim。QuIVer 仍然只能是 diagnostic/prototype-only。

### 2.8 Graph expansion 继续 blocked

R25/R29/P6 都支持同一结论：graph 不适合默认 expansion。R29 中 graph_basic added_gold=`0`、added_false=`437`。Graph 更可能适合 explainer、rerank feature、impact/test selector，而不是默认 recall expansion。

### 2.9 LLM-derived 适合 stress 和 hint，不适合事实层

真实 LLM provider 已经跑通，P5 生成了 derived/stress 结果。但这些输出必须保持 `not_evidence=true`：LLM 不能生成 Evidence，不能生成 gold label，不能做 citation verdict，也不能做 promotion verdict。

当前 LLM 最适合的角色是：query aliases、symbol tags、intent views、candidate rerank/filter/span narrowing、failure/stress generation。它可以扩大失败面，也可以帮助解释 rich candidate context，但不能替代 EvidenceCore。

P20-LS 把这条边界变成了可执行检查：LS0 做安全预检，LS1 生成 `not_evidence=true` query aliases 并只作为 candidate/supporting 检索扩展评测，LS3 默认只写 public stress split。初始离线 slice 已经给出警告信号；随后 P20-LS-A 用真实 LLM provider（`[mk]Kimi-K2.7-Code`）跑了 self-test 与 9 个真实 CI corpus runs。schema/guardrail 表现可以接受，但低上下文/query-only alias 质量完全失败：9 个真实 runs 中 0 个 quality pass，added_gold_span=`289`、added_false_span=`8312`（约 28.8:1 false:gold），平均 fabricated_identifier_rate 约 `0.459`。因此低上下文 LLM query aliases 已经 blocked，不应继续扩大。这不是 rich-context LLM retrieval 的结论；后续 alias/retrieval 研究应使用 source snippets、candidate metadata、symbol/path inventories 和 prompt/context matrices。

### 2.10 P21-G 应研究跨模型上下文注入效应

下一阶段模型研究不应该继续把 metadata-only remote input 当作默认姿态，但也不应把某一个模型的最佳 token budget 当成 OpenLocus 的全局规律。对于 public corpus 和明确 opt-in 的远程 runs，模型应该拿到足够代码事实：raw code snippets、path headers、signatures、symbol bodies、neighboring lines、local retrieval scores、hard distractors、top-k candidate sets。必要边界仍然保留：排除 secrets、ignored files、provider keys、private labels/gold answers；EvidenceCore 仍是最终事实权威；不让 LLM 做 promotion judge。

P21-G 应跨 embedding 与 LLM model profiles、query buckets、repo types、roles 和 layouts 比较 context atoms 与 context packs。主变量不是固定 token cap，而是注入的信息：signatures、matched lines、source/test/doc flags、retrieval scores、body windows、neighbor symbols、related tests、hard distractors、candidate uncertainty 和 inventory grounding。P21-G1E 显示裸 dense context atoms 仍只能 supporting-only：`pack2_evidence_sketch` 是 model-averaged SpanF0.5 最好的策略，`atom_signature` 是 FileRecall@5 最好的策略，但 false spans 远多于 gold spans（`17924` vs `2876`）。P21-G2E 显示 constrained dense 有 modest supporting value：`dense_atom_signature_rrf_file_constrained` 的 SpanF0.5 avg `0.163` vs RRF `0.1508`，PFP avg `0.0`，`11/16` runs 有用。Dense 仍不能 primary。P21-G3L 显示 LLM rich candidate roles 有信号但强烈依赖模型/仓库：`llm_span_narrow` avg ΔSpanF0.5 `+0.0418`，Flash/Kimi 在 `py_flask` 最明显；filter/abstain 降 false 但经常杀 gold；GLM-5.1 schema degradation 阻止继续扩大，需先做 prompt/schema repair。每份报告都必须同时记录质量、效率和跨模型泛化：SpanF0.5、added_gold/false、PFP、provider calls、input/output tokens/chars、p50/p95 latency、cost、model-averaged treatment effect、per-model effect 和 effect variance。

P21-G3L-R 是 LLM roles 的 structured-output repair 路线。rich-candidate harness 已支持 `prompt_only`、`json_object`、`json_schema_strict`、`tool_call` 四种输出模式，记录 provider-rejection fallback diagnostics，并允许一次不再走 fallback ladder 的 schema repair retry。第一轮 GLM-focused smoke 已跑 4 output modes × 2 repos：`tool_call` 目前是 GLM 最优模式（avg SpanNarrow Δ `+0.0677`，repair success `3/5`），`prompt_only` 应阻断，`json_object` 仍不够，`json_schema_strict` mixed。随后顺序低并发重跑 `tool_call`，去除了 provider HTTP 429 噪声，并把 GLM SpanNarrow avg Δ 提到 `+0.1361`；下一轮 bucketed P21-G3L 应让 GLM 使用 `tool_call`。

P21-G3B 新增 public-safe bucket sampling（`task_bucket` 与 `task_risk_tags`），并确认 global LLM roles 不能跨 mixed buckets 默认启用。在 6-run bucketed smoke 中，LLM roles 能显著降低 PFP，但经常同时杀掉 gold spans。`span_narrow` 仍适合 likely-positive / high-confidence tasks，但不是跨桶默认策略。`filter` 和 `abstain` 只能路由到 negative / dense-false-positive / ambiguous buckets，不能全局默认。

---

## 3. 当前研究假设

| 假设 | 当前状态 | 需要什么来确认 |
|---|---|---|
| RRF 应保留为 recall base。 | R29 强支持，但必须配 guard。 | 在人工与 stress tier 上 guard 后仍稳定召回。 |
| symbol/regex 应作为 precision anchor。 | 强支持。 | 更广 symbol repair 后 false-positive 不升。 |
| dense 目前应保持 supporting-only。 | 当前 L1/L2 证据已经 blocking dense-only/global dense 的 primary/default。 | rich raw-code/snippet views 能稳定 added_gold > added_false，PFP 低，latency/cost 可接受。 |
| anchor-seeded dense/QuIVer 可能比 global dense 更安全。 | 有希望但信号混合。 | 多 repo 上可复验地抑制 false span。 |
| BQ 诊断可能适配当前 code embedding 分布。 | Flask 诊断信号积极。 | 分片 BQ/proto graph 在速度/质量上有优势且不增 false。 |
| 小 embedding 模型可能足够。 | P9 初步支持继续比较。 | 更多 repo 同任务并记录 latency/cost。 |
| LLM-derived 可安全扩大失败面。 | 机制可行，质量未证。 | rich context derived views 增加 gold 或 stress coverage，且不诱导 primary hallucination。 |
| LLM query aliases 能在不污染 primary 的情况下改善 anchor。 | 低上下文 P20-LS-A query aliases 对 `[mk]Kimi-K2.7-Code` 已 blocked：真实 runs 0/9 quality pass，false:gold span≈28.8:1，平均 fabricated identifier rate≈0.459。 | Grounded variant 成功：从 repo inventories 或 top-k candidate context 中选择 aliases，`alias_added_gold > alias_added_false`，PFP 不升，fabricated identifier rate 低。 |
| Context atoms 能跨模型泛化。 | P21-G planned hypothesis。 | Signature/matched-lines/scores/flags/body-window atoms 具有正向 model-averaged treatment effect，模型间方差低，且不增加 PFP。 |
| Rich LLM candidate support 能改善 span targeting。 | P21-G role hypothesis。 | 在 snippet-backed local candidates 上 rerank/filter/span-narrow，SpanF0.5 上升、false spans 下降，latency/cost 可接受。 |

---

## 4. 矛盾信号与负结果

这些负结果是目前最有价值的部分之一，因为它们防止研究结论过早乐观：

1. **P4 tiny 乐观信号被 P8a 弱化**：tiny self-test 中 anchor-seeded added_false=`0`，但 public Flask slice 中 added_false=`15`。
2. **Dense file recall 与 span quality 分离**：多个 P8/P9 结果显示 FileRecall 可以很好，但 SpanF0.5 仍低。
3. **RRF recall 与 false-primary 绑定**：RRF 强召回同时携带高 false-primary，说明 admission 比 raw recall 更关键。
4. **Graph expansion 多次 net-negative**：graph_basic 在 R29 中几乎只加 false，不加 gold。
5. **更大 embedding 模型未在首批样本中胜出**：8B 没有压倒 0.6B/4B/bge-m3。
6. **JS Express 表现弱于 Go/Python/Rust**：真实 embedding 质量有语言/框架差异，不能只看平均数。
7. **P20-LS 低上下文 alias expansion 真实-provider scale-up 失败**：所有 guardrails 通过，但 query-only aliases 在真实 CI runs 上 false spans 远多于 gold spans（8312 vs 289），且 fabricated identifier rate 高；这阻断低上下文 LLM alias scale-up，不阻断 rich-context LLM retrieval。

---

## 5. 当前质量与边界策略

新的研究优先级是质量与效率。边界应该保护事实层和 secrets，而不是让模型缺少有用的 public-code context。目前所有研究结论都依赖以下必要边界继续成立：

- `EvidenceCore` 仍是唯一事实层。
- Dense/QuIVer/graph/LLM-derived 只能产出 candidate/supporting/diagnostic，不直接产出 Evidence。
- Evidence 必须来自当前源文件读取，并通过 `content_sha` 与 line range 校验。
- RUN phase 不读取 private labels；SCORE phase 才读取 labels。
- 真实 provider 只在 `workflow_dispatch + enable_remote_models=true + OPENLOCUS_ALLOW_REMOTE=1` 下运行。
- 报告与 artifacts 不上传 provider URL/key、private labels 或 gold answers。Raw snippets 可以在明确 public/opt-in rich-context runs 中发送给 provider，但不应作为 artifacts 提交，除非明确说明。
- unavailable strategy 只能 reason-only，不能输出假质量数字。

质量优先的 public/opt-in remote runs 中可以使用：

- 经过 secret/ignore 过滤后的 raw code snippets/chunks；
- path、symbol、signature、doc heading、neighbor-line context；
- top-k local candidate metadata 和 retrieval scores；
- 用于权衡 quality、cost、latency 的 prompt/context matrices。

---

## 6. 目前真正建立了什么

目前已经比较稳地建立了四件事：

1. **事实层安全约束可执行**：EvidenceCore + materialization + citation validation 不是口号，而是已经贯穿本地检索、store、graph、dense、CI runner 的机制。
2. **本地 lexical/symbol/RRF 仍是主干**：真实模型进场后，并没有取代 RRF/symbol/regex，反而更明确需要它们作为 anchor 与 guard。
3. **真实模型有价值，但高度依赖上下文**：embedding 有 file-level signal，LLM 可扩展 stress/derived views，QuIVer BQ 值得继续；它们都不能直接进入事实层，但后续测试应给模型 richer code context。
4. **实验体系能发现反例**：P4 → P8a、P20-LS offline → remote scale-up 的变化说明系统可以把 tiny 乐观或“只是 schema-safe”的结果拉回现实，这对长期研究非常重要。

---

## 7. 阶段摘要索引

详细阶段报告均保留；本节只是索引，不替代原报告。

### R0-R13：本地事实层与安全脚手架

- R0/R1：local evidence kernel、read/scan/search、trace、citation validation。
- R2：regex/BM25/symbol/RRF local bakeoff。
- R3：StoreHit materialization gate 与 conservative store。
- R4：DerivedIndexView safety scaffold；derived views are not Evidence。
- R5：deterministic graph scaffold；graph output is not direct Evidence。
- R6：deterministic fast-context orchestration scaffold。
- R7-R10：persistent BM25、AST chunking、quality bakeoff、incremental index。
- R11：TDB Level0 adapter probe；metadata/chunks only，无 retrieval quality claim。
- R12：real-repo incremental robustness bench。
- R13：provider/dense safety scaffold with mock embeddings and no remote quality claim。

### R14-R29：benchmark 与失败面扩张

- R14-R16：scaled benchmark foundation、external multi-repo expansion、multi-method bakeoff。
- R17-R19：query router、guard calibration、large/stress guard generalization。
- R20-R23：auto-wide failure-surface dataset、strategy matrix、failure attribution、guard sweep。
- R24-R25：QuIVer/TDB availability probe、dense_mock/graph ablation；graph/dense default expansion blocked。
- R26：auto-stress-1000 static dataset。
- R28：conservative promotion candidate report；no default change。
- R29：R26 strategy matrix；RRF recall strong、symbol precision anchor、query-noise guard promising、graph/dense blocked。

### R30-R45：真实模型准备与诊断扩展

- R30：freeze R29 baseline。
- R31：real embedding provider smoke and safety gates。
- R32：embedding view bakeoff harness。
- R33：QuIVer BQ readiness diagnostics。
- R34-R36：QuIVer/BQ prototype and anchor-seeded dense/quiver experiments。
- R37-R38：LLM-derived views and stress expansion；not Evidence。
- R39-R40：symbol extraction and regex normalization repair tracks。
- R41-R42：graph role research and admission model v2 rules。
- R43-R45：integrated long-run report；no promotion。

### P1-P9：真实 provider 与 CI 逐步放大

- P1：real embedding and LLM smoke，provider access validated。
- P2：bounded real embedding view bakeoff。
- P3：real embedding QuIVer BQ readiness。
- P4：real embedding anchor prototype。
- P5：LLM-derived/stress harness with not-evidence boundary。
- P6：repair/admission replay。
- P7：real-provider summary。
- P8/P9：GitHub Actions public corpus scale-up、model bakeoff、multilingual smoke。

### P20-P21：LLM scale-up 与跨模型 context injection

- P20-LS/P20-LS-A：低上下文/query-only LLM aliases safety-passed 但 quality-failed；direct low-context alias scale-up blocked。
- P21-G：跨模型 context-injection 阶段，使用 context atoms、context packs、candidate metadata、model profiles、roles、layouts，并记录 latency/cost。P21-G1E 显示 `pack2_evidence_sketch`、`atom_signature` 有 file/span 信号但 naked dense false spans 占主导。P21-G2E 显示 constrained dense 有 modest supporting value（`dense_atom_signature_rrf_file_constrained`），但 dense-only 仍只是 diagnostic/non-primary。P21-G3L 显示 LLM span narrowing 有 promising 但 model/repo-specific 信号；filter/abstain 需要 prompt/bucket routing，GLM 需要 schema repair。

关键详细报告：

- `docs/final-research-report.md` — R0-R29 historical report。
- `docs/research-summary.md` — stage-by-stage status summary。
- `docs/r29-r26-stress-matrix.md` — R29 matrix and failure clusters。
- `docs/r45-promotion-candidate-report.md` — R30-R45 conclusion checkpoint。
- `docs/real-provider-p7-summary.md` — P1-P6 real-provider summary。
- `docs/real-provider-ci-scale-p8-p9.md` — first CI scale-up results。
- `docs/real-provider-ci-large-scale.zh.md` — L1/L2 大型真实-provider测试结论。
- `docs/p20-llm-large-scale.md` — P20-LS-A 低上下文 LLM alias scale-up 结果。
- `docs/p21-g-cross-model-context-injection.md` — P21-G 跨模型 context-injection 计划。

---

## 8. 下一步研究问题

下一步不是 promotion，而是更大、更细、更可复现的验证：

1. 将 L2 task set 固定为可复现 suite，避免 task generation drift。
2. 在 public/opt-in corpus 上跑 P21-G context atom screening：signatures、matched lines、retrieval scores、flags、body windows、neighbors、related tests、hard distractors。
3. 在完成 false-span analysis 后，再把 P3/P4 扩到更多 repo。
4. 在同一任务集上继续比较 bge-m3 与 Qwen 0.6B/4B/8B，加入 latency/cost。
5. 把 P5 stress traps 接入 anchored dense/QuIVer 验证，看 added_gold 是否持续大于 added_false。
6. 在 R26/R38 上复验 symbol repair 和 regex normalization，重点看 bucket regression。
7. 把 real dense support score 接入 admission_v2 研究，但只作为 supporting feature。
8. 继续 QuIVer sharding/prototype，直到有 graph/ANN 后端质量证据再谈 QuIVer quality。
9. 如果重新研究 LLM query aliases，只测试 grounded variants：从 inventories 中选择 aliases，或在看到 top-k local candidate snippets 后生成 aliases。
10. 跑 P21-G rich LLM candidate support：在 snippet-backed local candidates 上 rerank/filter/span-narrow/abstain/inventory_alias，记录 model-averaged/per-model effects，并报告质量、latency、token、cost trade-off。

---

## 9. 当前一句话总结

OpenLocus 目前已经建立了一条质量与证据双重约束的研究路线：本地 lexical/symbol/RRF 是事实检索主干；真实 embedding、QuIVer、LLM-derived、graph 只有在 grounded 与 validated 时才有价值。L1/L2 证明 dense-only/global dense 不能 primary/default；P20-LS-A 证明低上下文/query-only LLM aliases 不能按当前形式扩大。下一阶段的关键问题是：哪些 context atoms、packs、roles、layouts 和 model profiles 能让 real-model retrieval 跨模型稳定增加 gold，同时不以不可接受的 latency/cost 增加 false-primary 与 false-span。
