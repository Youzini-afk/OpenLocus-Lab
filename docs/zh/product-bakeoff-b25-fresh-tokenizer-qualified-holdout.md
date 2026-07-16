# 产品栈 Bakeoff — B2.5 全新分词器合格盲测

日期：2026-07-16

状态：`product_bakeoff_b25_protocol_ready_runtime_qualification_pending_no_private_holdout_no_tournament_no_result`

B2.5 是一场单独预注册的新锦标赛。它不会重新打开 B2.4，不会给 B2.4 的不完整输出评分，不会复用已经暴露的 B2.4 盲测集，也不会复用旧启动授权。它只继承已经冻结的 B2.1 执行/评分设计，以及解释 B2.4 为何失败、生产 BM25 校验器如何修复的公开聚合工程证据。

可执行公开契约包括：

- [`product_bakeoff_b25_protocol.py`](../../eval/product_bakeoff_b25_protocol.py)
- [`product_bakeoff_b25_query_gate.py`](../../eval/product_bakeoff_b25_query_gate.py)
- [`product_bakeoff_b25_runtime_qualification.py`](../../eval/product_bakeoff_b25_runtime_qualification.py)
- [`product_bakeoff_b25_corpus.py`](../../eval/product_bakeoff_b25_corpus.py)
- [`product_bakeoff_b25_runner.py`](../../eval/product_bakeoff_b25_runner.py)
- [`product_bakeoff_b25_scorer.py`](../../eval/product_bakeoff_b25_scorer.py)
- [`product_bakeoff_b25_readiness.py`](../../eval/product_bakeoff_b25_readiness.py)
- [`product_bakeoff_b25_cli.py`](../../eval/product_bakeoff_b25_cli.py)
- [`product_bakeoff_b25_linux_longrun.sh`](../../scripts/product_bakeoff_b25_linux_longrun.sh)
- [`product-bakeoff-b25-holdout.yml`](../../.github/workflows/product-bakeoff-b25-holdout.yml)
- [`product_bakeoff_b25_protocol_report.json`](../../artifacts/product_bakeoff_b25_protocol/product_bakeoff_b25_protocol_report.json)

## 为什么 B2.5 必须是新锦标赛

B2.4 曾经跨越一次正式尝试边界，但在形成完整的 1,440 条记录矩阵前终止。严格的生产回执解析器正确拒绝了非零的 `invalid_hits_skipped`，所以没有评分、排名、shortlist 或产品默认项决策。这个终态保持不变。

后续工程排查发现，旧的持久化 BM25 行级校验器使用了独立的查询分词逻辑。以下划线 `_` 开头的精确标识符会被出题器接受，也会被 Tantivy 索引，但校验器丢弃了该查询 token，因而把原本仍然有效的命中判为无效。修复后，索引、查询解析和行级校验共同复用索引内容字段实际配置的 tokenizer。公开上游证据是 [B2.4 失败关闭聚合](../../artifacts/product_bakeoff_b24/product_bakeoff_b24_failed_closed_aggregate.json) 与 [关闭后 BM25 修复聚合](../../artifacts/product_bakeoff_b24_repair/product_bakeoff_b24_bm25_tokenizer_repair.json)。

该修复只是工程证据。B2.5 源码包会显式绑定修复后的持久化 BM25 源文件及真实 `bakeoff-query` 回归测试，但新的确认性结果仍必须使用新仓库、新任务、新 oracle、新冻结、新 readiness 检查点和一次新的正式尝试。

## 全新盲测与历史排除

最终私有样本仍包含 12 个仓库快照和 48 个逻辑任务：Rust、Python、TypeScript 与 small、medium、large、xlarge 四档可见源码规模交叉，每个仓库有四种冻结任务角色。

B2.5 排除三个完整历史样本框架：B2、B2.1 和 B2.4。它们的并集必须恰好包含 36 个互不相同的仓库 slug，以及 36 个互不相同的 `(slug, commit)` 身份。所有 B2.5 候选仓库和最终入选仓库都必须位于该并集之外，也必须位于封闭的预检、资格验证、操作练习和合成源排除表之外。每个槽位至少预注册两个候选，且所有槽位之间不能重复候选仓库。

冻结的 B2 离线出题器仍然是唯一出题器。候选切换必须在任何方案输出产生前完成。仓库身份、候选顺序、切换决定、任务文本、查询、路径、范围和 oracle 行全部保持私有。

## 私有出题前先验证修复后的运行时

在修复后的生产二进制通过合成资格验证前，不得编写任何 B2.5 私有盲测。验证必须在符合冻结 B2.3 runner 等级的 Linux 机器上执行。除 `cgroup_memory_limit_bytes` 外，父资格回执中的全部稳定机器字段都必须精确一致；内存额度只有在当前配置仍同时通过冻结的 B2.3 内存总量与可用内存门槛时才允许变化。CPU、存储、操作系统、工具链、swap 与文件句柄额度的漂移仍然严格关闭。OpenLocus 二进制本身则由 B2.5 重新验证，而不是强行要求它与修复前的旧二进制字节一致。

这项狭窄的换机位许可只存在于 B2.5 运行时资格验证之前。资格验证生成的私有 B2.5 回执会冻结当前机器的完整 profile 与二进制；正式锦标赛前的 runner 准入必须与该回执精确一致，之后不允许再次迁移机器。

资格验证不读取任何私有输入。它会构建一个很小的合成索引，并通过严格的生产解析器调用真实的 `bakeoff-query`，覆盖四个冻结类别：

- 普通标识符；
- 以下划线 `_` 开头的标识符；
- 被标点分开的标识符；
- 单字符标识符。

每个类别都必须返回由当前 EvidenceCore 支撑的 BM25 证据，BM25 回执必须实际执行，`stale_hits_skipped` 和 `invalid_hits_skipped` 必须都为 0，服务商和出站调用也必须为 0。精确合成查询、源码、路径、二进制摘要和机器配置只进入私有回执；公开报告只包含类别、计数、布尔门槛和公开资格摘要。

运行时资格聚合必须先提交并通过公开 CI，之后才能开始私有出题。它的公开检查点和 CI 运行号随后会绑定进私有盲测。

## 纯源码查询兼容性门槛

离线出题器生成新的私有任务与 oracle 清单后，B2.5 会在任何检索 adapter 执行前运行纯源码兼容性门槛。该门槛镜像 Tantivy 0.25 的 `default` analyzer：按 Unicode 字母数字连续段切分，移除 UTF-8 长度大于等于 40 字节的 token，并执行小写归一化。

全部 48 个查询都必须至少产生一个生产 token。对每个可回答任务的每个 oracle 正例范围，至少一个归一化查询 token 必须按照生产行级校验器的子串规则出现在当前冻结源码行中。no-answer 任务也必须产生非空 token，但没有正例范围。

私有兼容性报告不保存查询文本或源码路径。报告在出题阶段创建，在冻结和 readiness 阶段逐字节重算；其文件哈希和私有摘要会绑定进盲测绑定、冻结回执、启动授权与 runner 准入。runner 准入只验证该绑定，不导入 oracle，也不执行方案检索。

## 冻结、readiness 与正式尝试边界

私有冻结会同时绑定：全新的仓库/任务/oracle 清单、三个历史仓库锁、排除表、查询兼容性报告、公开与私有运行时资格回执、当前 OpenLocus 二进制、B2.5 源码包，以及继承的外层 600 秒 / 内层 570 秒超时契约。

公开 readiness 只能发布聚合计数和布尔门槛：12 个仓库、48 个任务、48 条 oracle 记录、排除 36 个历史仓库、重叠为 0、冻结任务边际、运行时资格通过、查询兼容性通过、方案输出为 0。任何私有清单或查询门槛摘要都不得公开。

readiness 提交并通过 CI 后，才允许创建一个绑定该检查点和 CI 运行的私有启动授权。独立 Linux 启动器先写入 worker 进入回执，等待 runner 完整准入，然后才写入私有 launch release。正式尝试边界是“runner 准入后的 release”，不是 PID 文件或启动器确认。

release 之前，如果交接或校验失败且方案输出仍为 0，不消耗正式尝试。release 之后，不允许重启、恢复、选择性重跑、重新计算、补齐缺失单元、修改规则、修改超时、修改任务、修改 oracle 或迁移机器。边界后的失败会让 B2.5 以无结果状态关闭。

## 实验与评分设计

独立实验单位仍是一个逻辑任务（`n=48`）。仓库是嵌套聚类；重复次数与冷/热缓存观测只是技术重复。六个 S0–S5 方案都在同一台准入机器上运行每个任务，并继承随机完整任务区组和仓库 split-plot 生命周期。

完整矩阵预期包含 1,440 条逻辑记录，并继承精确的索引构建次数。不允许中途查看质量、不允许自适应淘汰，也不允许按方案或任务组分片。质量或资源向量完全相同时使用并列竞争排名，评分器不会强制选出唯一第一名。

只有完整矩阵和全部评分前完整性门槛通过后，才允许导入 oracle 与 scorer。之后继承的 B2.1 scorer 才能生成纯聚合的 B2.5 结果。仓库级、任务级、单元级、查询、oracle、源码位置、精确机器配置和私有摘要都不得公开。

## 冻结的公开标识

- B2.5 规范摘要：`b25spec_1603e85ac197760b`
- B2.5 源码包摘要：`b25src_f293d24c0f3aab207af3571ea3d0bd7a3d7992818f879c217ce5042883cd66d4`
- B2.5 盲测框架摘要：`b25frame_23661bee3726c4b52d6381bee3ad7ea857ca396acb77ee91482b0701978d4e17`
- 继承的执行调度摘要：`b21sched_a023b8ccc4b38f62289a40527bec01b2e3eba47ec6b16754108efee90ac27ad3`
- B2.5 协议报告摘要：`b25protocol_cdb3ec1eb55acd1bf5ba1de39a76deccc525b0dbf6f0d7e74d2ee2b2c20e8ba7`

## 当前获准顺序

在公开实现接受审查期间不需要开启服务器。获准顺序是：

1. 提交 B2.5 协议、实现、文档和协议报告，并取得公开 CI 全绿；
2. 开启符合 B2.3 runner 等级的 Linux 服务器，只运行四类合成的修复后运行时资格验证；
3. 提交其纯聚合公开报告，并再次取得 CI 全绿；
4. 编写全新私有盲测，运行并重算纯源码查询门槛，冻结运行时，生成聚合 readiness；
5. 提交 readiness 并取得 CI 全绿；
6. 创建一次私有启动授权，重新准入 runner，并只释放一次完整长跑。

当前检查点正在执行第 1 步。尚不存在 B2.5 运行时资格结果、私有盲测、方案输出、评分、锦标赛结果或执行授权。
