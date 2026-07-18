# 产品栈对比 B4 精确 Linux 运行时资格验证

日期：2026-07-18

状态：`product_bakeoff_b4_exact_linux_runtime_qualified_private_multi_panel_authoring_allowed_after_publication_ci`

## 结果

当前 Linux runner 使用真实 release CLI 执行了精确 B4 源码检查点及其已通过的控制面 CI。四类公开合成查询全部返回当前证据，BM25 回执均已执行，陈旧或无效跳过均为零，provider/network 调用为零。稳定 runner profile 与精确 CLI 字节只冻结在私有运行时回执中。

本阶段没有读取或产生任何私有候选、仓库、任务、查询、oracle 或处理方案输出。它只证明运行时完整性，不是经验性产品结果，也不授权正式启动。

## 资源准入

runner 通过冻结的最低级别：Linux x64、至少 8 个有效 CPU 配额、至少 32 GiB 的有限内存上限且至少 24 GiB 有效可用、活动交换占用为零、Python 3.10+、Rust/Cargo 1.95.0，以及 checkout 外的非旋转本地 scratch。scratch 门槛是按串行工作集计算的 5,100,273,664 个空闲字节（约 4.75 GiB）；它不是固定付费磁盘预留，也不需要 GPU。

闭合 B4 CLI 现在会在硬上限允许时，把自身进程的打开文件软限制提升到 65,535；若硬上限不足则 fail closed。这样，qualification、authoring、freeze、readiness 与正式执行不再依赖某个 shell 的默认软限制，同时仍保持同一冻结 runner 级别。

## 边界

只有在本聚合公开 artifact 提交并通过 publication CI 后，才新增授权：私下编制并冻结十二个互不重叠 panel。正式尝试仍未获授权；必须先完成私有留出集冻结、发布聚合 readiness 并通过 CI，再创建单独的私有启动授权。

公开 artifact：[`product_bakeoff_b4_runtime_qualification.json`](../../artifacts/product_bakeoff_b4_runtime_qualification/product_bakeoff_b4_runtime_qualification.json)。
