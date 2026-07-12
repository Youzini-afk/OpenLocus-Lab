# 面向决策的产品实验 —— 第一阶段审计（已执行，无 provider）

> **仅第一阶段。资格 / 余量审计 —— 不是痛点证明，不是产品效果证明，不是下游 Agent 评估。** 未执行任何 provider 或 agent 运行。

## 运行内容

单次无 provider 执行
`eval/decision_experiment_phase1_audit.py --audit`，并预先通过自测
（`--self-test`）。全部为本地 CPU；`new_provider_calls = 0`，
`new_provider_or_agent_runs = false`。

- 冻结源码截止点：`056877ff638d59118e05e046bd30d816e70ba2fb`（公开输出中唯一允许的 SHA）。
- 确定性枚举截止点前所有可达非合并提交，按从新到旧再按 SHA 排序。

## 结果

| 字段 | 值 |
|------|-----|
| 枚举的非合并提交 | 865 |
| 过滤考虑的提交 | 865 |
| 过滤后合格候选 | 2 |
| 可复现性检查尝试 | 0（未到达——低于最小队列） |
| 余量门 | 未运行（合格不足） |
| **总体门状态** | **STOP** |
| 原因 | fewer_than_min_5_eligible_candidates_after_filter |

## 候选过滤原因分桶（仅聚合）

| 原因分桶 | 计数 |
|----------|------|
| excluded_docs_only | 766 |
| excluded_no_prod_source | 80 |
| excluded_not_defect_fix | 15 |
| excluded_msg_test | 1 |
| excluded_no_dev_test_found | 1 |
| eligible_developer_test_resolved | 2 |

未使用硬编码的有利候选列表。过滤完全基于规则；每项排除均有固定原因分桶。从未为凑足分母而放宽规则。原因分桶计数之和等于考虑的提交数（865）。

## Rust 内联测试处理

审计使用确定性括号平衡解析识别 Rust 源文件（`crates/*/src/*.rs`）中的 `#[cfg(test)] mod tests { ... }` 内联测试模块，正确处理字符串字面量、字符字面量、原始字符串、行注释与嵌套块注释。格式错误或歧义区域以失败即关闭方式拒绝（保守地视为生产代码）。

**属性误报安全：** 扫描器具备语言感知能力 —— 出现在行注释、块注释、常规字符串字面量、原始字符串字面量或字符字面量内部的 `#[cfg(test)]` 文本**不被**视为真实的测试模块属性。仅接受在代码位置找到的属性。

**生命周期/标签安全：** Rust 词法分析器区分生命周期（`'a`、`'static`）与标签（`'label:`）和字符字面量。仅跳过语法完整的字符字面量（含合法转义字符）；生命周期/标签保留为代码 token，不破坏括号跟踪。这确保测试区域在模块之后的固定生产代码（使用 `&'static str`、字节字面量或原始字符串）之前结束。

**字节安全覆盖层：** 内联测试模块处理读写原始 `bytes`（Windows 上无换行符转换）。区域检测在 UTF-8 解码字符串上进行，但在切片前将字符偏移映射回原始字节中的字节偏移。**真实强制不变量**（不仅是自测）在 `apply_overlay` 中通过**显式基础模式**（绝不从内容推断）执行：`mode="parent"`（缺陷父提交 + 覆盖层 / 空补丁——覆盖前验证 `parent_full_hash`；覆盖后验证 `parent_prod_hash` + `fixed_test_hash`），`mode="fixed"`（修复提交 + 同一开发者测试——覆盖前验证 `fixed_full_hash`；覆盖后验证 `fixed_prod_hash` + `fixed_test_hash`；可为空操作；绝不要求父哈希），以及 `mode="parent_dev_patch"`（父提交 + 仅生产开发者补丁 + 覆盖层——覆盖前验证 `fixed_prod_hash` 证明仅冻结的开发者生产补丁改变了生产；覆盖后验证 `fixed_prod_hash` 不变 + `fixed_test_hash` 证明覆盖层仅贡献测试字节）。任何不匹配均抛出并以失败即关闭方式拒绝。绝不追加/替换固定生产字节。遇到无效 UTF-8 或歧义偏移映射时以失败即关闭方式拒绝。未知模式被拒绝。

**歧义失败即关闭：** 若源文件（父提交或修复提交中任一）有多个内联 `#[cfg(test)] mod ...` 区域，则父/固定区域对应关系无法唯一确定。覆盖层以失败即关闭方式拒绝（无合格覆盖），而非静默使用区域 0。

内联测试区域行在逐行级别从 `<=100` 生产改动行限制与生产文件集合中排除。对**每一个** Rust `prod_src` 文件（不仅限于大文件），均检查父/修复源码与统一 diff，逐行拆分测试区域与生产改动行。仅当至少有一行改动落在唯一检测到的有效测试区域之外时，该文件才计为生产文件。这防止了仅改动内联测试模块的小型（`<=100` 原始行）提交被误分类为生产代码。对于混合源文件，仅评分端覆盖层精确保留父提交生产字节，并仅移植修复后的开发者内联测试模块字节——通过实际磁盘字节的 SHA-256 哈希断言验证。零固定生产字节可泄漏。

此修正了先前的过高计数与原因分桶核算错误。其一，两个触及含大型内联测试模块的生产源文件的修复提交先前被排除为 `excluded_too_many_prod_lines`；启用内联测试检测后通过行数过滤。其二，内联测试区域拆分先前仅在 `raw_total > 100` 时运行，因此仅改动内联测试模块的小型提交可能被误分类为生产代码；现在对每个 Rust `prod_src` 文件均运行拆分。其三，成功解析精确开发者测试覆盖层的延迟候选先前仍留在 `deferred_no_test_in_commit_check_preexisting` 分桶中；现移至 `eligible_developer_test_resolved`，使原因分桶计数之和等于考虑的提交数，且公开报告不再将成功候选描述为延迟。

## 解释

挖掘的内部源（截止点前的 OpenLocus 仓库）绝大多数为文档、协议冻结、生成物与仅评估脚本。少量产品源码缺陷修复中，两个通过过滤并成功解析精确开发者测试覆盖层（`eligible_developer_test_resolved`）——但低于最少 5 的队列要求。未为凑足分母而放宽任何规则。

按冻结契约，资格失败对第一阶段为**终态 STOP**。不重新设计任务、不替换更易候选、不改阈值、不增加臂、不延续包。不作任何痛点、产品或效果声明。R14/R20 检索标签未被当作任务结果；未使用稀疏/无上下文或 BEA 臂；未作时效性因果声明。

## 生产 Fast Context 路径（已对接生产 CLI schema，未被候选执行）

对照/处理 pack 生成步骤复用**相同的现有生产 `openlocus fast-context` CLI 与渲染器**：

- 处理：`regex,bm25,symbol,graph` + RRF + 最终引用/时效性校验，`max_evidence=12`，`budget=2000`；
- 对照：仅 `bm25`，相同构建器/渲染器/查询/上限。

实现已对接**真实生产扁平化证据 schema**：`Evidence` 为 `#[serde(flatten)] pub core: EvidenceCore`，因此每个证据 JSON 对象直接拥有扁平字段（`path`、`start_line`、`end_line`、`content_sha`、`score`、`why`、`channels`）加上可选 `meta`。**无嵌套 `core` 对象**；校验对嵌套伪 schema 以失败即关闭方式拒绝，而非支持虚构的固定件形状。诊断按精确已知键集（`invalid_citations_dropped`、`unknown_channels`、`token_budget_enforced`）校验类型，且 `unknown_channels` 为空。非融合的意外动作通道、顶层与每轮 `disabled_channels`、以及陈旧时效性均被拒绝。证据路径校验为相对、工作区内、磁盘存在。复用 `eval/fast_context_smoke.py` 中精确的 `citations validate` 调用/逻辑针对各臂工作区证据。`<5` 审计在 fast-context 之前返回，因此该步骤在本次运行中**未被真实候选执行**——无已提交聚合记录前不作新的两臂执行声明。候选 pack 生成、复现与余量均未运行。余量路径（暖重复校验、每轮引用再物化、CLI 前后隔离扫描、显式 `isolation_scan_failures` 门控）因 `2 < 5` STOP 在其之前发生，仅保持**合成校验**状态。

**两个独立臂工作区：** 处理与对照臂运行在完全独立的 OS 临时工作区中，均从同一 `parent_sha` 经 `git archive` 物化（无共享 `.openlocus`、索引、追踪或缓存）。处理创建工作区本地 `.openlocus` 后，共享工作区中对照的 `before_cli` 扫描必然失败；且处理状态可能污染对照。两个工作区消除此问题。每臂：首次调用前使用 `before_cli`；每次调用后使用 `after_cli`；第 2..5 次重复前使用 `after_cli`（工作区本地真实 `.openlocus` 可存在）。所有祖先保持无标记。两个工作区在每次调用前后均被扫描，显式计数/失败被聚合。在 `finally` 中清理两个工作区。此路径**仅为合成校验**，因为 `2 < 5` STOP 阻止了真实余量执行——不作真实余量执行声明。

**严格的每臂状态机：** 每个暖重复的每个臂以失败即关闭状态机运行（在 `_run_one_arm` 中）：(1) 前置隔离扫描通过；(2) 运行 `fast-context`；(3) fast-context 后的 `after_cli` 隔离扫描通过；(4) fast-context schema `_valid` 为真；(5) 仅此后对该可信证据运行 `citations validate`；(6) 引用校验后的 `after_cli` 隔离扫描（引用 CLI 是另一次调用）通过；(7) 引用校验为真；(8) 仅此后进入另一臂/下一重复。任何不可信证据（schema 无效或未隔离）绝不到达引用 CLI。处理失败不调用引用/对照；处理引用失败不调用对照；对照失败不运行后续重复。任何失败立即记录显式扫描/失败、固定私有原因分桶，并返回 G_i=0。`run_fast_context`/`validate_citations` 的 `TimeoutExpired`/`OSError`/意外异常不在辅助函数内捕获——它们传播到每候选 `headroom_for_candidate` 边界，由现有失败即关闭 `except` 子句转换为固定原因分桶（`headroom_subprocess_exception`/`headroom_unexpected_exception`）。两个独立父工作区与首次重复 `before_cli` vs 后续 `after_cli` 语义均保留。

**非对象/格式错误 JSON 失败即关闭：** `run_fast_context` 将 `json.loads` 解析为 `Any`；若结果非字典（列表/字符串/数字/null），返回安全内部结果 `_valid=False`、`_invalid_reason='non_object_json'`，仅含 returncode/latency——绝不包含任意原始数据。非零退出与格式错误 JSON 同样返回无效而不抛出。`validate_citations` 安全拒绝非对象 JSON，不向非字典赋值或对非字典使用 `{**out}` 展开。`TimeoutExpired`、`OSError` 及意外子进程/校验异常在每候选余量边界被捕获并转换为固定原因分桶（`headroom_subprocess_exception`/`headroom_unexpected_exception`）；候选失败即关闭，工作区被清理，整个审计绝不中止。异常细节绝不公开。整数检查收紧为拒绝 `bool`（Python 中 `bool` 是 `int` 的子类），适用于行号、token 计数、诊断计数与引用计数，通过 `type(x) is int` 实现。

**Pack/证据一致性：** 计数匹配不足。`pack.evidence` 必须在结构与顺序上等于可信顶层证据。生产 Rust 构造（`plan.rs`）将同一 `final_evidence` Vec 克隆到 `result.evidence` 与 `result.pack.evidence`，因此它们在内容与顺序上始终相同——强制精确相等。`pack.budget_used` 必须等于顶层 `budget_used`，因为生产 Rust 构造中两者均由相同的 `latency_ms`/`tokens_estimated`/`remote_cost_estimated` 值构建。

**字节精确独立测试覆盖层：** `extract_overlay_test` 对独立测试文件（提交新增与预存在）使用 `_git_bytes`（原始字节，无换行符转换），而非 `_git(...).encode()`（后者在 Windows 上可能规范化换行符）。`separate_test_blob_hash`（原始 git blob 字节的 sha256）在 `apply_overlay` 中被强制：写入后实际磁盘字节必须精确哈希到此值，证明 git blob 字节 == 覆盖层字节 == 磁盘字节，即使对于 CRLF/非 ASCII 内容。目标路径在写入前被校验为相对、无 `..` 遍历、解析在工作区内。

## 自测

全部三十项自测通过（仅合成临时 git 固定件，无网络/provider 调用）：确定性枚举、基于规则的过滤、逐字节测试移植、隔离（无 `.git` 链接、OS 临时目录在 REPO_ROOT 之外、无祖先标记——真实生产拓扑）、稳定失败/通过复现、聚合隐私扫描、失败即关闭的门行为、Rust 内联测试区域检测（含字符串字面量中的括号）、测试行从生产行计数中排除、字节安全覆盖层保留父提交生产+修复测试字节（原始磁盘字节哈希验证，真实 `apply_overlay` 中通过显式基础模式强制执行——不仅是自测）、格式错误的内联模块失败即关闭拒绝、无固定生产字节泄漏断言、多个有效内联测试模块失败即关闭拒绝（歧义）、注释/字符串字面量/原始字符串中的 `#[cfg(test)]` 属性误报被拒绝、小型（`<100` 原始行）仅测试内联模块改动被作为仅测试排除、生命周期/标签边界（生命周期 `'a`/`'static` 与标签 `'label:` 不被误认为字符字面量——测试区域在固定生产之前结束）、祖先标记拒绝（嵌套于含 `.git` 父目录的工作区被拒绝）、强制真实覆盖层哈希拒绝（错误提交工作区通过 `parent_full_hash` 拒绝）、仅父提交余量物化（两臂检索均无固定实现字节）、扁平化 Fast Context 证据 schema 校验（真实 `#[serde(flatten)]` schema——`path`/`start_line`/`end_line`/`content_sha`/`score`/`why`/`channels` 为直接字段加可选 `meta`；嵌套 `core` 对象失败即关闭拒绝；诊断精确键/类型；`unknown_channels` 为空；非融合意外动作通道与顶层/每轮 `disabled_channels` 被拒绝；陈旧时效性被拒绝；证据路径解析在工作区内且文件存在）、非空洞的隔离/引用 GO 条件（GO 要求 `isolation_scans > 0` 且 `isolation_scan_failures == 0`）、仓库外工作区拓扑、**内联覆盖层基础模式往返**（mode=parent/fixed/parent_dev_patch 在真实 Rust 内联仓库上均成功；错误工作区或缺失开发者补丁失败即关闭；未知模式被拒绝——证明每条复现路径确实可复现而非必然失败）、**暖重复聚合**（五次中首次无效后续有效仍失败；一次引用失败仍失败；一次 CLI 后隔离失败递增显式 `isolation_scan_failures` 并阻止 GO——后续有效运行不抹除先前失败），以及 **after-CLI 隔离模式**（工作区本地 `.openlocus` 目录仅在为真实非符号链接目录时允许；文件/符号链接 `.openlocus` 始终拒绝；`.git` 始终拒绝）。、**两臂工作区独立性**（处理与对照在完全独立的 OS 临时工作区中从同一 parent_sha 物化——不同根、均父提交精确、无标记/状态交叉、第 2 次重复仅接受真实本地 .openlocus 目录而拒绝文件/符号链接/祖先标记）、**非对象/格式错误 JSON 失败即关闭**（JSON 数组/字符串/数字/null 返回 _valid=False 且 _invalid_reason='non_object_json' 而不抛出或包含任意原始数据；TimeoutExpired/OSError/意外异常在每候选余量边界被捕获并转换为固定原因分桶；格式错误引用输出失败即关闭；布尔值作为整数在行号、token 计数、诊断计数与引用计数中被拒绝）、**Pack/证据一致性**（pack.evidence 必须在结构与顺序上等于顶层 evidence；pack.budget_used 必须等于顶层 budget_used）、以及**字节精确独立测试覆盖层**（独立测试文件使用 _git_bytes 获取精确 blob 字节含 CRLF/非 ASCII；separate_test_blob_hash 在 apply_overlay 中强制执行；目标路径校验为相对/无 ../工作区内），以及**余量臂状态机排序/短路**（mocked `run_fast_context`/`validate_citations` 配合由工作区标记状态驱动的真实 `_do_isolation_scan` 证明：处理 schema 无效 → 零引用调用且零对照调用；处理 fast-context 后隔离失败 → 零引用/对照且失败被计数；处理引用失败 → 零对照调用；对照 schema 无效 → 无后续重复——恰好一次处理 + 一次对照 fast-context 调用与一次引用调用；且引用 CLI 调用后的 `after_cli` 隔离失败被计数并阻止 GO——不可信证据绝不到达引用 CLI）。

## 校验

- `python -m py_compile eval/decision_experiment_phase1_audit.py` —— 通过。
- 自测（`--self-test`）—— 全部 30 项通过。
- 公开隐私扫描（`public_privacy_scan`）—— 干净（`forbidden_public_key_scan_clean: true`）。唯一类似私有值的字段是故意公开的冻结截止点 SHA，契约允许且扫描器已将其加入白名单。
- 现有公开报告（`phase1_public_report.json`）已对照更新后的报告 schema/不变量与隐私扫描校验。其聚合（`865` 考虑、`2` 合格）与 `generated_at` 未变——这些修复仅影响 STOP 后不可达的执行路径且 Rust 词法分析器未改变，因此无需重新运行完整真实审计。
- `runs/` 私有树确认被 gitignore；公开产物未被 gitignore。

## 下一步

第一阶段 STOP。第二阶段（配对 agent 框架）、实时 GO 阈值与 Defects4J 确认未到达且不得在本冻结契约下运行——这是经验门结果，非用户授权门。未来的第一阶段需要不同的、含足够多小型且带测试的产品缺陷修复的挖掘内部源 —— 而非放宽这些规则。两个合格候选不足以构成队列（最少 5）。
