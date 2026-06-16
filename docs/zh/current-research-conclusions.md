# OpenLocus 当前研究结论

日期：2026-06-16

范围：R0-R45、real-provider P1-P9、P8/P9 CI scale-up、L1/L2 真实-provider 大仓库 slice 测试、P20-LS/P20-LS-A 低上下文 LLM query-alias 结果，以及 P21-G 跨模型上下文注入研究转向。

状态：研究结论总结，不是 promotion request，不是默认策略升级申请。

## P57 泛化门控 v0

P57 是一个确定性的、无线上 LLM/无 provider 的聚合级泛化就绪门控，运行于 P51B 之后。它只消费现有聚合报告 JSON（P46/P47/P48/P49/P50/P52/P52A/P52B/P52C、可选 P51、必须 P51B），校验上游安全标志、完整性与可用性。P57 不读取源文件、候选池、提示词、响应或 provider 配置，也不在公开产物中发布路径、标识符、区间、摘要或密钥。对于单 slice/self-test 运行，P57 按设计报告 `insufficient_matrix`；它不是质量证据，不是 promotion/默认门控，也不是线上就绪证据。详见 [P57 报告](p57-generalization-gate.md)。

## P58 Source-Backed Verifier Calibration v0

P58 是一个确定性的、无线上 LLM/无 provider 的聚合级校准报告，运行于 P57 之后。它只消费 P48、P52C、P51B、P57（可选 P52B/P52A/P49）的聚合 JSON 报告，把上游的可用性与分布转成粗粒度的规划/行动提示桶。P58 不是 verifier、不是 admission、不是 Evidence、不是默认/promotion、不是线上就绪证据。它不读取源文件、候选池、任务、提示词、响应、repo lock 或 provider 配置，只输出聚合计数、比例与校准桶。详见 [P58 报告](p58-source-backed-verifier-calibration.md)。

## P59 Contrastive Pack Coverage & Counterfactual Study v0

P59 是一个确定性的、无线上 LLM/无 provider、仅聚合的预支出前置诊断，运行于 P58 之后。它从同样的 P25 临时记录重建 P49 对比候选包，并测量冻结后的包是否在触发任何 LLM 支出前就包含后续 LLM 角色所需的必要对比信息。P59 不是质量评估器、不是 admission、不是 Evidence、不是默认/promotion、不是线上就绪证据。包的构造是 gold-free 的，仅使用候选元数据；私有 labels 只在包冻结后、在显式标记的 `score_phase_gold_coverage` 块中加载。它不读取源文件、不构造提示词、不调用 provider。详见 [P59 报告](p59-contrastive-pack-coverage-counterfactual.md)。

## P60 RMC Policy v2 v0

P60 是一个确定性的、无线上 LLM/无 provider、仅聚合的诊断策略对比层，将 P47/P48 的 `request_more_context`（RMC）几何/覆盖层推进为一个可比较的策略矩阵。对同一批冻结的候选/任务输入，每个策略只选择下一个诊断动作；P60 报告聚合路由计数、SCORE-phase 黄金召回/错误代价诊断，以及标注为估算的成本/延迟估算。RMC 不是证据、不是准入、不是默认策略；P60 不声明胜者、不推荐默认策略。详见 [P60 报告](p60-rmc-policy-v2.md)。

## P61 预支出门控 v0

P61 是一个确定性的、无线上 LLM/无 provider、仅聚合的预支出门控，运行于 P60 之后。它只消费现有聚合报告（P57、P58、P59、P60、P51-B 必须；P52C 可选），并输出一个前置条件就绪决策，判断未来 P51-C 线上 LLM 微运行是否值得考虑。P61 不调用 provider、不构造提示词、不读取源文件/临时记录、不认可 Evidence、不修改默认值、不晋升、不授权 provider 支出。它只报告前置条件；开启线上运行仍需单独的 workflow_dispatch 或人工决策。对于单 slice/self-test 运行，P61 按设计报告 `insufficient_inputs` 或 `self_test_only`。它不是质量证据、不是 promotion/默认门控，也不是线上就绪授权。详见 [P61 报告](p61-pre-spend-gate.md)。

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

P22/P23 把下一阶段从“继续比较单个通道”推进到 evidence-seeking policy surface。当前冻结了两个本地、无远程调用的决策面：`r20_positive` 用于正例 candidate reach，`r26_guard` 用于 no-gold guard stress。R20 capped positive slice 显示 RRF 仍是 reach base（`Reach@5=0.975`，`SpanReach@5=0.95`），但 symbol 的本地 SpanF0.5 最好（`0.3169`），`symbol_regex_union` 是进入 P25/P30 的 precision/reach 实验基线候选。R26 显示 BM25/RRF 仍会在 no-gold 噪声查询上制造 false primary（`0.2833`），而 symbol/regex/union/guard 会 abstain。因此 P25/P30 必须分开优化：召回保留、false-primary 抑制、EvidenceCore materialization 是三个不同成功层级。

### 2.11 P25 bucket-routed LLM role policy 评估器已就绪

`eval/p25_bucket_policy.py` 是一个确定性、无远程调用的策略评估器。当前提交的报告只是经过净化的 self-test 脚手架（`status=self_test_only`、`not_quality_evidence=true`），不是质量证据。真实 P25 评估现在必须使用 `eval/p21_llm_rich_candidate.py --p25-policy-records-out` 在 SCORE 阶段生成的临时 records；这些 records 留在 runner temp，不上传，P25 只上传聚合指标。`bucket_routed_v0` 只按 allowlisted public `task_bucket`/`task_risk_tags` 路由：`llm_span_narrow` 用于 likely-positive / high-confidence 桶，固定先验的 `llm_filter`/`llm_abstain_filter` 用于 negative / dense-false-positive / ambiguous 桶，exact-symbol + unique-symbol-anchor 任务跳过 LLM，其余回退到 candidate baseline。P21 aggregate summary 和非 ephemeral schema 会被拒绝为 `status=insufficient_task_detail`。这只是 P25/P30 evidence-seeking policy surface 的脚手架，不是 promotion 结论。

第一轮真实 P25 remote smoke 使用这个安全的 P21→P25 ephemeral handoff，完成 6 个成功聚合 runs（`Flash/Kimi/GLM × py_flask/js_express`，每个 run 18 个按 bucket 抽样任务）。`bucket_routed_v0` 显著降低 false spans（`108 -> 28`）和平均 PFP（约 `-0.0926`），但也损失了一些 gold spans（`24 -> 21`）；平均 SpanF0.5 只小幅正向（`+0.0026`），且强依赖 repo/model。因此 P25 适合作为 P30 Admission V3 的 false-primary reducer 组件，而不是 default policy。

### 2.12 P30 Admission Model V3 脚手架已就绪

`eval/p30_admission_model_v3.py` 是一个确定性、无远程调用的 admission model
研究脚手架（schema `p30-admission-v3-report-v1`）。当前提交的报告同样是经过净化的
self-test 脚手架（`status=self_test_only`、`not_quality_evidence=true`），不是质量证据。
真实 P30 评估仍需使用
`eval/p21_llm_rich_candidate.py --p25-policy-records-out` 在 SCORE 阶段生成的临时
`p25-policy-records-ephemeral-v1` records；这些记录留在 runner temp，不上传，P30 只上传聚合指标。

P30 只从 RUN-phase 公开可观测特征进行路由：public `task_bucket`、
`task_risk_tags` 和 `route_features`。`score_group`、`has_gold`、gold spans、
private labels 和 outcome metrics 只在动作确定后用于聚合评分。允许的动作包括
`abstain`、`admit_symbol_regex_union`、`admit_rrf_primary`、
`admit_llm_span_narrow`、`apply_llm_filter`、`supporting_only`、
`weak_candidate_only`。`admission_v3` 评分卡结合可解释单调特征分数（query noise、
exact/unique symbol anchor、symbol/regex/local anchors、RRF backed by anchor、
LLM span-narrow validity/within candidate）与 negative/ambiguous/dense-false-positive
桶的 hard guard。dense 和 graph 信号只允许作为 supporting feature，不能发明 primary evidence。

评估器比较 `candidate_baseline`、`llm_span_narrow`、`llm_filter`、
`llm_abstain_filter`、`bucket_routed_v0`（从 P25 复用）和 `admission_v3`。
报告 task count、SpanF0.5、PFP、added gold/false spans、filter gold kill rate、
abstain rate、action counts、score bands、selective risk proxy、与
candidate baseline 和 `bucket_routed_v0` 的 mean deltas，以及对输入中没有测量 outcome
的动作的 fallback 计数。公开输出会递归扫描禁用键
（raw query/snippet/prompt/response/gold/gold_spans/private labels/provider keys）。
`promotion_ready=false`、`default_should_change=false`、
`evidencecore_semantics_changed=false`、`candidate_not_fact=true`、`external_calls=0`。

P30 不是 promotion candidate。下一步应把它接入真实 P25 ephemeral smoke records，
与 P25 `bucket_routed_v0` 以及 P22/P23 evidence-seeking guard surfaces 进行比较。

第一轮真实 P30 remote smoke 已完成 6 个成功 runs（`Flash/Kimi/GLM × py_flask/js_express`，每个 run 18 个按 bucket 抽样任务）。结果确认当前 `admission_v3` 脚手架过于保守：baseline added gold/false 为 `27/102`，P25 `bucket_routed_v0` 为 `19/39`，P30 `admission_v3` 为 `17/41`。P30 匹配了平均 PFP 降幅（`-0.0833`），但平均 SpanF0.5 delta 比 `bucket_routed_v0` 更差（`-0.0102` vs `+0.0010`）。非零 fallback counts 表明当前 ephemeral handoff 还缺少更丰富本地 admission 动作所需的 measured outcomes/features。下一步应扩展 P21/P22 handoff，加入 measured `symbol_regex_union` / `rrf_primary` outcomes 和安全 route features，再重跑 P30。

P30-H1 已实现这个 handoff repair。它作为 measurement repair 成功，但作为 policy improvement 失败。6 个真实 runs 中 `admission_v3_h1` 的 selected-action fallback 为 0，因此比较已经 quality-comparable；但 P25 `bucket_routed_v0` 仍更强：`20/37` added gold/false，平均 ΔSpanF0.5 为 `+0.0020`；P30-H1 为 `18/87`，平均 ΔSpanF0.5 为 `-0.0350`。新的结论是：missing handoff 掩盖了 scorecard 本身的问题，`admit_symbol_regex_union` 太宽，放进了很多 false spans。下一步 P30-H2 应收紧 local-anchor admission，而不是继续加新通道。

P30-H2 收紧了 local-anchor admission，但这次 quality repair 仍失败。它保持 fallback-free 和 quality-comparable，但结果为 `15/90` added gold/false；H1 是 `18/87`，P25 `bucket_routed_v0` 是 `16/36`。平均 ΔSpanF0.5：H2 `-0.0370`，H1 `-0.0346`，P25 `-0.0052`。新的诊断是：问题不只是 primary admission 太宽；weak/supporting/filter actions 仍然保留了过多 span-level false cost。P30-H3 现在已把 action-specific span-cost accounting 和 false-span budgets 实现为一个仅 SCORE 阶段的诊断性会计层；它不改变 admission 路由，而是从现有 `bucket_routed_v0`、`admission_v3_h1`、`admission_v3_h2` 及 baseline 对比策略推导每个动作的成本，并输出专用报告 `artifacts/p30_admission_v3/p30_h3_span_cost_report.json`（schema `p30-h3-action-span-cost-report-v1`）。

真实 P30-H3 smoke（6 个成功 runs，108 个任务）更精确地解释了 P30 的失败模式。baseline 是 `27/102` added gold/false spans；P25 `bucket_routed_v0` 仍是最强 reference，为 `19/45`；P30-H1 为 `18/88`；P30-H2 为 `15/90`。H3 显示 P30-H1/H2 的 false-span 成本主要来自 primary local-admit actions（`admit_symbol_regex_union`，以及 H2 的 `admit_rrf_primary`），而 `supporting_only` 的主要代价是杀掉 gold、造成 recall loss，并不是新增 false spans。因此 P30-H4 应该给 primary local-admit actions 设定明确 action budgets，而不是继续整体收紧所有 non-primary actions。

### 2.13 P31 Candidate Reach Ceiling Study 脚手架已就绪

`eval/p31_candidate_reach_ceiling.py` 是一个确定性、无远程调用的诊断性脚手架
（schema `p31-candidate-reach-ceiling-report-v1`）。当前提交的 self-test 产物是
经过净化的合成数据（`status=self_test_only`、`not_quality_evidence=true`），不是质量证据。
P31 仅用于 SCORE 阶段：labels 只在 RUN 之后加载，并仅用于聚合指标；它不影响路由或准入决策。

P31 测量候选证据本身在没有任何路由或准入决策前覆盖 gold label 的能力。
输入与 P25/P30 相同，是 `p25-policy-records-ephemeral-v1` 临时 records。
当 records 尚未携带候选证据池时，P31 会报告
`candidate_pool_availability=missing_candidate_pool` 和
`reach_metrics_available=false`，然后只计算 outcome-only fallback 指标，而不是伪造 reach 零值。
当候选池存在时，它会报告 K=1/3/5/10/20 的聚合 `GoldFileReach@K`、`GoldSpanReach@K`、
`GoldSpanExactReach@K`、`CandidateAbsentRate@K`、`FileRightSpanWrongRate@K`，
以及与 `candidate_baseline` 对比的 `ModelMissGivenGoldPresent@K`、
动作/策略诊断指标（`FilterKillGoldRate`、`AdmissionFalsePrimaryRate`、
`AdmissionFalseSpanPerNoGoldTask`）、`EvidenceCoreRejectRate`
（无 rejection 字段时为 `not_measured`），以及满足 `funnel_sums_to_positive_tasks=true` 的 K=5 失败漏斗。

P31-H1 扩展了 P21 rich-candidate 临时 handoff：临时 records 现在携带轻量级候选池
（`p31_candidate_pools`）与仅 SCORE 阶段使用的 private gold spans（`p31_score_gold`），
并标记 `p31_h1_candidate_reach_handoff=true` 与
`p31_h1_schema_version="p31-h1-candidate-reach-handoff-v1"`。
池内条目仅保留 `rank`、`path`、`start_line`、`end_line`，以及可选的 `content_sha`、
`score`、`channels`；不含 snippet、原始 query/prompt/response 或 provider 字段。

P31-H2 增加 strategy-level reach matrix，覆盖 `candidate_baseline`、`rrf_primary`、
`symbol_regex_union`、`llm_span_narrow`、`llm_filter`、`llm_abstain_filter`。
当 H1 候选池存在时，它按公共 `repo_id` 与 `task_bucket` 聚合 reach@5，
报告 unique reach share、pairwise file/span overlap 与 Jaccard span、
双向 marginal gain，以及固定策略组合的并集 reach。缺失的策略池会报告
`availability=missing_pool`，而不是伪造零值。

公开产物仅限聚合指标：不含 per-task 行、原始 query/snippet/prompt/response、
candidate paths/spans、gold spans、private labels 或 provider 字段。
安全标志锁定：`promotion_ready=false`、`default_should_change=false`、
`evidencecore_semantics_changed=false`、`candidate_not_fact=true`、
`remote_calls_by_p31=0`、`score_phase_only_metrics=true`、
`aggregate_only_public_artifact=true`。


第一轮真实 P31-H1 reach smoke 已完成 6 个成功 runs（`Flash/Kimi/GLM × py_flask/js_express`，共 108 个任务、48 个 positive tasks）。所有 runs 都检测到 H1 handoff，且 reach metrics 均可用。candidate baseline 在 K=5 时只覆盖 `24/48` 个 positive tasks 的文件和 span（`GoldFileReach@5=0.5000`、`GoldSpanReach@5=0.5000`），而 `FileRightSpanWrongRate@5=0/24`。这说明本轮 smoke 的第一瓶颈是 candidate absence，而不是文件内 span localization。相同 runs 中 P25 `bucket_routed_v0` 的 false-span 成本仍明显低于 P30-H1/H2（P25 added gold/false `20/46`，H1 `18/87`，H2 `15/90`），但 P31 说明：只调 admission 无法找回缺失的一半 positive tasks。

P31-H2 strategy reach matrix 的重跑说明：下一步更应该修 anchor，而不是再加一个 LLM role。K=5 时，`candidate_baseline` 覆盖 `24/48` 个 positive spans，`rrf_primary` 覆盖 `21/48`，而 `symbol_regex_union` 覆盖 `42/48`。`symbol_regex_union` 贡献 `18/48` 个 unique span hits，而 `candidate_baseline + rrf_primary` 和 `candidate_baseline + llm_span_narrow` 都仍停在 `24/48`。因此 `symbol_regex_union` 是高 reach 的 candidate expansion source，但 P30-H3 已经证明它直接 primary admit 不安全。下一步应进入 P33 anchor repair/calibration，以及 P32/P30-H4 在 local-anchor primary admission 前加入 action budget。

第一轮真实 P33 anchor precision smoke 进一步确认：目前没有任何 observed anchor bucket 可以被视为 primary-safe。最强 calibration cell（`a3_r0_s2`：span agreement、low-risk、RRF-span-backed）覆盖 `42/48` 个 positive spans，但 `false_per_gold≈8.69`、`net_span_value_2x=-786`。`symbol_regex_agree_span` 在其 bucket 内覆盖 `9/9` 个 positives，但仍有 `false_per_gold=4.0`；`symbol_regex_disagree` 覆盖 `27/30`，但 `false_per_gold≈13.44`；`regex_only` 更差（`false_per_gold=22.5`）。因此 P33 保留 P31-H2 的结论：anchors 是主要 reach lever；同时强化 P30-H3 的结论：anchor primary admission 必须被 budget 约束。下一步 P33-B 应修复/校准 symbol 和 regex 子类型；P32/P30-H4 不应在没有 held-out budget validation 前 promote 任何 local-anchor bucket。

### 2.14 P33 Reach-Preserving Precision Anchor Repair 脚手架已就绪

`eval/p33_anchor_precision_repair.py` 是一个确定性、无远程调用的诊断性脚手架
（schema `p33-anchor-precision-repair-report-v1`）。它复用 P31 使用的 P21/P31-H1
临时 records：需要 `p31_candidate_pools`、`p31_score_gold`、公共
`task_bucket`/`task_risk_tags` 以及 RUN 阶段可观测的 `route_features`。
labels 与 gold spans 只在 SCORE 阶段用于聚合指标。当候选池或 gold spans 缺失时，
P33 报告 `availability=missing_pool`/`not_measured`，而不是伪造零值。

P33 定义了 anchor taxonomy v1，包括 `exact_unique_symbol_anchor`、
`unique_symbol_anchor`、`symbol_anchor_only`、`regex_anchor_only`、
`symbol_regex_agree_span`/`agree_file`/`disagree`、
`rrf_anchor_agree_span`/`agree_file`/`unbacked`、公共桶
（`positive`/`ambiguous`/`negative`）、风险标签（`hard_distractor`、
`dense_false_positive`）、query-noise 等级，以及有界组合桶如
`symbol_regex_agree_span_low_risk`、`rrf_span_backed`、
`negative_or_ambiguous_with_anchor` 等。每个桶报告 task count、positive/no_gold count、
`GoldFileReach@5`、`GoldSpanReach@5`、`FileRightSpanWrongRate@5`、span cost 聚合
（`added_gold_span`、`added_false_span`、`false_per_gold`、`gold_per_false`、
`net_span_value_1x/2x`）、平均 `SpanF0.5` 与平均 `primary_false_positive_rate`，
以及 diagnostic class
（`primary_candidate_safe_observed`、`supporting_only_observed`、
`needs_budget_guard`、`blocked_high_false_cost`、
`insufficient_denominator`）。

三维校准矩阵的三个维度为：`anchor_strength`
（0=无 anchor，1=仅有 symbol/regex，2=文件级 agreement，3=span 级 agreement，
4=exact_unique_symbol_span_agreement）、`risk_level`
（0=低风险/positive，1=ambiguous，2=negative/高风险）、`rrf_backing_level`
（0=无 RRF backing，1=仅文件级，2=span 级），报告同样的聚合诊断并标记单调性异常。
`p33_to_p32_handoff` 按 diagnostic class 分组 budget candidate buckets，
并显式设置 `frozen_policy=false`。

公开产物仅限聚合指标：不含 per-task 行、task IDs、原始 query/snippet/prompt/response、
route features、candidate paths/spans、gold spans、private labels 或 provider 字段。
安全标志锁定：`promotion_ready=false`、`default_should_change=false`、
`evidencecore_semantics_changed=false`、`candidate_not_fact=true`、
`remote_calls_by_p33=0`、`score_phase_only_metrics=true`、
`aggregate_only_public_artifact=true`。

### 2.15 P33-B Anchor Subtype Calibration 脚手架已就绪

`eval/p33b_anchor_subtype_calibration.py` 是一个确定性、无远程调用的诊断性脚手架
（schema `p33b-anchor-subtype-calibration-v1`）。它扩展了 P21 的临时 handoff，
为每个 `symbol_regex_union` 候选增加了私有 subtype 元数据
（`p33b_anchor_subtypes`，schema `p33b-anchor-subtypes-v1`），将其分类为
`symbol_only`、`regex_only`、`symbol_regex_fusion`，并标注 agreement class
（`single_source`、`same_file_only`、`span_overlap`、`disagree`）、
`rank_bin`、`candidate_count_bin`、`span_width_bin` 以及 per-candidate
`rrf_backing`。同时新增 `symbol_primary` 和 `regex_primary` 候选池，供
P31 覆盖研究使用。

P33-B 消费这些临时 records，将私有 subtype 行与 `symbol_regex_union` 候选对齐，
仅在 SCORE 阶段使用 `p31_score_gold` 和 strategy outcomes 计算聚合指标。
它报告有界 subtype bucket 的诊断：task count、positive/no-gold count、
`SubtypeGoldFileReach@5`、`SubtypeGoldSpanReach@5`、
`FileRightSpanWrongRate@5`、`UniqueSubtypeSpanReach@5`、span cost 聚合
（粗粒度 task-level attribution）、`delta_vs_candidate_baseline`，
以及带最小分母门控的 diagnostic class。三维校准矩阵覆盖
`source_strength`（0=regex_only，1=symbol_only，2=symbol_regex_fusion）、
`match_quality`（0=disagree，1=same_file_only，2=span_overlap_unbacked，
3=span_overlap_rrf_backed）和 `risk_level`，报告同样诊断并标记单调性异常。
`p33b_to_p32_handoff` 按 diagnostic class 分组 budget candidate buckets，
并显式设置 `frozen_policy=false`。

公开产物仍仅限聚合指标：不含 per-task 行、task IDs、原始 query/snippet/prompt/response、
candidate paths/spans、gold spans、private labels、route features、subtype 行或
provider 字段。安全标志锁定：`promotion_ready=false`、
`default_should_change=false`、`evidencecore_semantics_changed=false`、
`candidate_not_fact=true`、`remote_calls_by_p33b=0`、
`score_phase_only_metrics=true`、`aggregate_only_public_artifact=true`。

真实 P33-B subtype smoke（6 个成功 runs，108 个 task observations：36 positive、72 no-gold）在更细粒度上确认了 P33 结论：没有任何 observed subtype bucket 可以 primary-safe。`span_overlap` 是最好的粗粒度 agreement class（`GoldSpanReach=1.0`、`false_per_gold≈1.78`），但在 2x false-span penalty 下仍是 net-negative。`symbol_regex_fusion` 在本轮 smoke 中 subtype span reach 也完整，但 added gold/false 仍为 `24/66`（`false_per_gold=2.75`）。`same_file_only` 更弱（`false_per_gold≈2.18`），`disagree` / `single_source` buckets 被 false-span cost 主导。RRF backing 有帮助，但不足以让 anchor 安全（`rrf_yes false_per_gold≈4.67`）。因此 P33-B subtype bucket 应作为 P32/P30-H4 action budget 输入，而不是 primary admission。

### 2.16 P32 / P30-H4 确定性预算覆盖层已就绪

`eval/p30_admission_model_v3.py` 现已实现 `admission_v3_h4`，即 P32/P30-H4 预算覆盖层策略。H4 是确定性、无远程调用、仅诊断用途的 lane。它从 P21 短暂 handoff 读取私有 P33-B 子类型元数据（`p33b_anchor_subtypes`、`p33b_anchor_subtypes_schema`），结合 RUN-phase 公开特征，测试 budgeted demotion。它不改动 Rust/EvidenceCore 语义、默认 pipeline 策略或任何生产 admission 路由。

P33-B 已证明任何 subtype 都不 primary-safe：即便是最好的 `span_overlap` bucket，`false_per_gold≈1.78` 且在 2x false-span penalty 下 net-negative；`disagree` 与 `single_source` 危险；`same_file_only` 更弱。因此 H4 仅基于 subtype 证据不会选择 `admit_symbol_regex_union`、`admit_rrf_primary` 或 `admit_llm_span_narrow`，其动作限定为 `apply_llm_filter`、`supporting_only`、`weak_candidate_only` 和 `abstain`。规则保守：negative/dense/ambiguous 任务过滤或弃权；低危公开 bucket 中 `span_overlap` 若带 RRF backing 则归为 `supporting_only`，否则 `weak_candidate_only`；`same_file_only` 仅在明确 positive bucket 中归为 `weak_candidate_only`；`disagree`/`single_source` 除非公开 bucket 强 positive 且 query noise 低，否则过滤。缺失 subtype 元数据时退化到类 `bucket_routed_v0` 的保守回退。

归一化后的内存任务会携带 P31/P33-B 私有 handoff 字段（`p31_candidate_pools`、`p31_score_gold`、`p33b_anchor_subtypes`、`p33b_anchor_subtypes_schema`）供 SCORE-phase 使用，但这些键不会出现在 P30 公开产物中。报告标志锁定为 `h4_budget_overlay=true`、`promotion_ready=false`、`default_should_change=false`；当存在 P33-B 记录时，`h4_available=true` / `p33b_handoff_detected=true`。H4 与 H1/H2 一样报告 `quality_comparable`、`blocked_by_missing_action_outcomes` 和 `selected_action_fallback_rate`；real-provider CI gate 现在要求 H4 存在，并在 `p21_llm_rich` 真实记录上质量可比且 selected-action fallback 为零。

第一轮真实 P30-H4 remote smoke 完成 6 个成功 runs。它 quality-comparable 且 fallback-free，但过度保守：H4 产生 `0` added gold spans 和 `0` added false spans，mean SpanF0.5 为 `0.0000`。相同 runs 中 P25 `bucket_routed_v0` 仍是最佳 reference（added gold/false `27/34`，mean SpanF0.5 `0.0768`）。因此 H4 是 safety lower bound 和有价值的负结果，不是可部署 admission policy。下一轮 H4 应测试 budgeted selective re-admission 或 `request_more_context`，而不是 all-demotion。

### 2.17 P32 / P30-H4B 选择性 primary re-admission 已就绪

`eval/p30_admission_model_v3.py` 现已同时实现 `admission_v3_h4b`，即 P32/P30-H4B 选择性 primary re-admission 诊断策略。H4B 是确定性、无远程调用、仅诊断用途的 lane。它与 H4 使用相同的私有 P33-B subtype handoff 和 RUN-phase 公开特征，但测试一个极窄的严格合取条件，以判断是否允许 primary-admit 动作。

严格门仅在以下全部满足时才选择 `admit_symbol_regex_union`：最优子类型为 `symbol_regex_fusion` + `span_overlap` + `rrf_backing`；`local_anchor` 和 `symbol_regex_agree_span` 为真；`query_noise <= 0.1`；公开 bucket/tag 属于低危 positive 集合；且 `exact_unique_symbol_anchor` 或 `rrf_anchor_agree_span` 至少一个为真。若同时还有 `rrf_backed_by_anchor` 和 `rrf_anchor_agree_span`，H4B 可选择 `admit_rrf_primary`。其余任务一律 hard-guard 或降级，包括 negative/dense/ambiguous/hallucination/high-noise 及最优子类型为 `regex_only`/`same_file_only`/`disagree`/`single_source` 的情况。

公开产物包含 `h4b_available`、`h4b_budget_overlay=true`、`h4b_selective_readmission=true`、`h4b_primary_opportunity_count` 以及 rule 聚合计数（`strict_union_re_admit`、`strict_rrf_re_admit`、`hard_guard`、`missing_handoff`、`demote_span_overlap`、`demote_same_file`、`filter_dangerous_subtype`）。H4B 还报告 `quality_comparable`、`selected_action_fallback_rate`、`false_per_gold`、`net_span_value_2x` 以及来自 P30-H3 会计的 span-cost summary。合成 self-test 中 H4B 质量可比且 fallback-free，并触发少量严格 primary opportunity。真实 H4B smoke 已完成 6 个成功 provider runs：H4B quality-comparable 且 fallback-free，并摆脱 H4A 全刹车失败（added gold/false `0/0 -> 24/41`）。但它仍未超过 P25 `bucket_routed_v0`（P25 added gold/false `25/30`，mean SpanF0.5 `0.0683`；H4B `0.0433`），因此 H4B 是有希望的研究方向，但不是 promotion candidate。下一轮应进一步收紧 strict RRF re-admission，或在 primary admission 前引入 `request_more_context`。

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

### P20-P25/P30：LLM 放大、策略路由与可解释 admission

- P20-LS/P20-LS-A：低上下文/query-only LLM aliases safety-passed 但 quality-failed；direct low-context alias scale-up blocked。
- P21-G：跨模型 context-injection 阶段，使用 context atoms、context packs、candidate metadata、model profiles、roles、layouts，并记录 latency/cost。P21-G1E 显示 `pack2_evidence_sketch`、`atom_signature` 有 file/span 信号但 naked dense false spans 占主导。P21-G2E 显示 constrained dense 有 modest supporting value（`dense_atom_signature_rrf_file_constrained`），但 dense-only 仍只是 diagnostic/non-primary。P21-G3L 显示 LLM span narrowing 有 promising 但 model/repo-specific 信号；filter/abstain 需要 prompt/bucket routing，GLM 需要 schema repair。
- P25：bucket-routed LLM role policy 评估器。确定性、无远程、只按公开 `task_bucket`/`task_risk_tags` 路由；能降低 false primary 但也会损失一些 gold span；作为 P30 输入有价值，不是默认策略。
- P30：Admission Model V3 研究脚手架。确定性可解释评分卡加 hard guard，只从 pre-SCORE 公开特征路由，比较多个 baseline 和 `admission_v3`/`admission_v3_h1`/`admission_v3_h2`，输出 score bands/selective risk/deltas、action-specific span-cost accounting（P30-H3），并递归扫描公开输出中的禁用键。P30-H1 修复了 missing outcomes；P30-H2 收紧 local-anchor admission 后仍弱于 P25；P30-H3 现在提供诊断性动作成本会计而不改路由。

关键详细报告：

- `docs/final-research-report.md` — R0-R29 historical report。
- `docs/research-summary.md` — stage-by-stage status summary。
- `docs/r29-r26-stress-matrix.md` — R29 matrix and failure clusters。
- `docs/r45-promotion-candidate-report.md` — R30-R45 conclusion checkpoint。
- `docs/real-provider-p7-summary.md` — P1-P6 real-provider summary。
- `docs/real-provider-ci-scale-p8-p9.md` — first CI scale-up results。
- `docs/zh/real-provider-ci-large-scale.md` — L1/L2 大型真实-provider测试结论。
- `docs/p20-llm-large-scale.md` — P20-LS-A 低上下文 LLM alias scale-up 结果。
- `docs/p21-g-cross-model-context-injection.md` — P21-G 跨模型 context-injection 计划。
- `docs/p25-bucket-routed-policy.md` — P25 bucket-routed LLM role policy。
- `docs/p30-admission-model-v3.md` — P30 Admission Model V3 报告。
- `docs/p30-admission-model-v3-remote-smoke.md` — 第一轮 P30 真实 remote smoke。
- `docs/p30-h1-remote-smoke.md` — P30-H1 enriched handoff 真实 remote smoke。
- `docs/p30-h2-remote-smoke.md` — P30-H2 stricter local-anchor admission 真实 remote smoke。
- `docs/p30-h3-span-cost-accounting.md` — P30-H3 action-specific span-cost accounting（仅诊断、仅 SCORE 阶段、不改路由）。
- `docs/p30-h3-remote-smoke.md` — P30-H3 真实 remote smoke 的 action-cost 诊断。

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
11. P30-H3：为 weak/supporting/filter outcomes 加入 action-specific span-cost accounting 和 false-span budgets，然后再继续 route tuning。

---

## 9. 当前一句话总结

OpenLocus 目前已经建立了一条质量与证据双重约束的研究路线：本地 lexical/symbol/RRF 是事实检索主干；真实 embedding、QuIVer、LLM-derived、graph 只有在 grounded 与 validated 时才有价值。L1/L2 证明 dense-only/global dense 不能 primary/default；P20-LS-A 证明低上下文/query-only LLM aliases 不能按当前形式扩大。下一阶段的关键问题是：哪些 context atoms、packs、roles、layouts 和 model profiles 能让 real-model retrieval 跨模型稳定增加 gold，同时不以不可接受的 latency/cost 增加 false-primary 与 false-span。P30 提供了一个确定性的可解释 admission 脚手架，用于横向比较这些策略面。
