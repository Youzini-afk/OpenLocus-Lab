# 产品栈对比 B3 离线控制平面

日期：2026-07-18

状态：`product_bakeoff_b3_offline_control_plane_complete_server_required_next_for_exact_linux_qualification`

B3 的可执行控制平面已经在不读取私有留出集、不产生治疗输出的前提下实现并完成故障测试。公开聚合报告为 [`product_bakeoff_b3_control_integration.json`](../../artifacts/product_bakeoff_b3_control_integration/product_bakeoff_b3_control_integration.json)。

本阶段补齐了此前 runner/scorer 集成刻意没有实现的部分：精确 Linux runtime qualification、相对四个历史帧的全新留出集准入、私有冻结、聚合 readiness、由 CI 绑定的 launch authorization、断线安全启动、第一条持久化观测的尝试边界 receipt、聚合成功发布和聚合失败关闭发布。

## Runtime qualification

B3 不再依赖任何历史服务器的机器身份。当前 Linux runner 必须独立通过冻结的最低 runner class，使用实际生产 CLI 和严格的 `bakeoff-query` 解析器执行公开合成 tokenizer 矩阵，并且在该矩阵前后保持稳定 profile 字段完全不变。

当前机器的精确 profile 和 CLI 字节只写入私有 receipt。公开报告只包含最低资源级别、聚合门槛、用例类别和零 provider 调用结果。在 authoring、freeze 和正式 RUN admission 前，系统都会重新采集当前 profile：稳定字段必须与 qualification 时完全一致，而可用内存、剩余空间和空闲负载等瞬时值则重新通过最低门槛。

B3 不再继承历史的 300 GiB scratch 下限。新的 scratch 门槛由实际串行峰值计算：最大允许可见仓库的六份逐字节一致实验臂快照、四倍快照/索引余量、4 GiB checkpoint/控制余量、4 GiB 文件系统安全余量，以及 2 GiB 取整/测量余量，最终得到 16 GiB 最低剩余 scratch 门槛。B2.3 的所有非存储 runner 门槛保持不变。候选克隆单独采用 checkpoint 管理，不再被换算成臆测的固定 scratch 预留。

24 GiB cgroup 内存余量要求仍然保留，但 B3 将有效余量计算为“limit 减 current 的原始余量 + 内核明确标记的 `inactive_file` 缓存”，且结果不超过 cgroup limit。这修正了 cgroup v1 把干净、可回收的构建/源码页缓存当成永久占用内存的计量问题。Active file cache、匿名内存、共享内存、脏页和 writeback 均不计入可用余量。

## 全新留出集与 readiness

候选计划必须排除互不重叠的 B2、B2.1、B2.4 和 B2.5 仓库帧，总计 48 个历史仓库 slug 与 identity/commit 对；同时排除所有登记过的真实 preflight 来源和合成 qualification 来源。12 个仓库槽位中的每一个都必须在 authoring 前冻结至少两个互不重复的候选。

Authoring 现在会为每个已完成仓库槽位写入一份持久化 checkpoint。恢复时，只有槽位局部候选计划 digest、所选候选序号、仓库/许可证绑定、精确 Git commit、已跟踪工作树整洁性以及四份任务草稿全部验证通过，才会跳过该槽位。旧克隆也只有在冻结的槽位/序号/仓库位置完全匹配时才可复用，并且仍会重新执行完整准入和源代码扫描；若缓存完整性不合格，必须先重新克隆同一候选，之后才允许考察下一个候选。因此，中断、缓存损坏或后续只替换一个失败候选时，不再丢弃其他已完成工作，也不会改变选择顺序；合格规则、所选 commit、最终 12 仓库帧和全部 48 个任务均不改变。

私有 holdout binding 覆盖所选仓库锁、48 个任务、48 条 oracle、仅源代码 tokenizer compatibility 报告、候选计划、四份历史锁、排除登记表、精确 runtime qualification、CLI 字节、B3 Williams 调度、完整的 360 组 / 1,440 观测计划，以及共用重复性策略。freeze 输出采用排他、持久化写入。

公开 readiness 只暴露固定计数、边际分布、布尔值、公开协议/runtime digest 和自身 digest。它要求治疗输出为零、launch release 不存在、没有评分或排名，也没有公开锦标赛结果。只有该 readiness 文件被提交且对应 CI 成功后，才允许创建私有 launch authorization。

## 尝试边界与断线安全

worker 进入、runner admission 和 launch release 都属于边界前状态，均不消耗正式尝试。

只有在 B3 引擎执行期间，冻结的 B2.1 append 函数才会被临时包装。normal 或 terminal 观测先由历史写入器落盘，随后同步该文件及其目录，最后原子写入私有 attempt receipt。这一刻才是第一条持久化治疗观测，也是唯一的正式尝试边界。

如果进程恰好在“观测文件已经持久化、receipt 尚未写入”的窗口死亡，reconciliation 会检查精确的 normal/terminal 观测目录并重建 receipt，因此绝不会把这种情况误判成零输出启动。反过来，存在 receipt 却没有任何持久化观测会被拒绝。跨越边界后，仍然禁止重启、恢复、选择性重试、填补和重算。

Linux launcher 使用 `nohup`、PID 文件、退出码文件、私有日志、worker-entry / admission 握手，以及单独的 launch release。status 命令只输出 worker 状态、release/边界布尔值、已完成任务组数、逻辑记录数和退出码；不会输出私有路径、身份、查询、指标或排名。

## 成功与失败发布

只有 1,440 条记录完整且全部评分前门槛通过后，系统才延迟导入 scorer，使用共用 B3 canonicalizer，把完整评分写入私有目录，并仅公开六个最终实验臂聚合和冻结的锦标赛决策。质量或资源向量完全相同的实验臂共享 competition rank，不强迫产生唯一赢家。

任何边界后失败都不允许重试。公开失败 artifact 只包含闭合的失败类别、已完成任务组数、已验证逻辑记录数、持久化治疗 artifact 数、冻结的协议边界，以及确认“不包含任何实验臂质量、资源或排名指标”的布尔值。单独的 artifact 计数还能关闭“崩溃留下持久化但不完整观测文件”的极窄情况。worker 或机器硬终止后，也可以只依据持久化的私有观测清单完成关闭，绝不重跑矩阵。

边界前零观测工作状态只会被审计为“可能可恢复”；工具不会自动删除它。若更换 runner，必须重新完成公开 runtime qualification 和 readiness 周期。

## 验证与下一步

跨模块 self-test 和 fault-test 覆盖：源代码闭包、runtime 公开/私有 schema、计算得到的 scratch 预算、取消继承 300 GiB 下限、cgroup v1 inactive-file 解析及保守的可回收内存准入、验证缓存复用且不重新克隆、checkpoint 恢复且不重复 authoring、checkpoint 源/计划漂移拒绝、48 个历史仓库排除、readiness 隐私、成功/失败发布、hook 恢复、只有 release 没有观测、已有观测但缺 receipt 的重建、只有 receipt 没有观测的拒绝，以及边界后禁止重试。Linux launcher 另行通过 13 步握手及重启/PID 复用身份测试。

当前尚未 qualification 精确 Linux runtime，尚无 B3 私有留出集、launch authorization 或正式尝试。只有本控制平面检查点及公开 CI 通过后，才应开启服务器执行精确 Linux qualification；该聚合 qualification 自身提交并通过 CI 之前，仍禁止私有 authoring。
