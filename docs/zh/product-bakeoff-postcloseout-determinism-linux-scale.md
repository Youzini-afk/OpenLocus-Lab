# 产品栈对比关闭后确定性 Linux 规模验证收口

日期：2026-07-17

状态：`product_bakeoff_postcloseout_determinism_linux_scale_complete_no_tournament_authorization`

本阶段完成 B2.5 关闭后确定性修复所要求的生产规模合成 Linux 验证。它不重开 B2.5，不重新分类其失败关闭决定，不对矩阵评分或排名，不复用其启动授权，不改变产品默认，也不授权新的锦标赛。

公开聚合为 [`product_bakeoff_postcloseout_determinism_linux_scale.json`](../../artifacts/product_bakeoff_determinism_linux_scale/product_bakeoff_postcloseout_determinism_linux_scale.json)，digest 为 `detlinux_b82d0262881b5f2623b866e3f9ea504e68cc591b1c23ac43c20349816af7bcfc`。

## 最终审查发现

全面审查在真实 bakeoff 主路径上发现了一个残余问题：核心 RRF 已修复为把宽跨度的票均分给多个互不包含的最小后代，但 bakeoff 输入归一化仍会在 RRF 看到歧义之前先选择其中一个后代。这样即使核心 RRF 本身已经确定，前置步骤仍可能重新制造位置赢家。

修复后的行为明确区分两种情况：

- 只有一个唯一最小后代：把宽单元规范化到该后代；
- 存在多个互不包含的最小后代：保留宽单元，由生产 RRF 将贡献平均分给全部最小后代。

小型回归测试分别覆盖两种情况；Linux 规模脚本还覆盖完整的 bakeoff 归一化到 RRF 路径，而不只是孤立测试 RRF helper。

## Linux 合成规模验证

全部运行均使用 Rust release profile，只使用合成临时输入，不读取 ignored `runs/`，不调用 provider/模型/网络，并绑定到已经通过跨平台 CI 的精确源码检查点。

| 层级 | 合成文件数 | 歧义跨度数 | 全新进程迭代 | 每进程测试入口数 | 结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| 默认生产规模 | 20,000 | 4,096 | 3 | 4 | 通过 |
| 增强规模 | 50,000 | 8,192 | 2 | 4 | 通过 |
| 声明参数上限 | 100,000 | 20,000 | 1 | 4 | 通过 |

每个进程迭代覆盖：

1. 持久 BM25 完整等分边界收集；
2. 临时 BM25 完整等分边界收集；
3. 核心 RRF 歧义重叠与总分守恒；
4. bakeoff 融合前歧义重叠归一化及其后的生产 RRF。

三个层级合计 6 次全新进程迭代、24 个压力测试入口全部通过；最终层直接覆盖压力测试允许的最大文件数和最大跨度数。

## 全面审查范围

审查沿 B2 到 B2.5 冻结锦标赛的精确组件路径进行：持久与临时 BM25；literal、symbol、AST 的有界截断；图构建、扩展、support 排序与上限；bakeoff 组件规范化；融合前重叠处理；RRF 并列、精确单元、包含关系与最终排序；适配器候选顺序及双步 support 投影；未来 scorer-equivalent 可比性投影；终态公开归档验证。

在这一已审查的锦标赛路径中，目前没有已知的依赖顺序的截断点。该结论刻意不扩张为“整个仓库所有无关产品或实验表面都已确定”的主张。

## 解释与剩余边界

此前的研究设计结论继续成立：精确语义重复性 hash 原则上比冻结 scorer 更宽，因此未来 pre-score gate 应使用与未来 scorer 对重复单元规范化完全相同的、oracle-blind、scorer-equivalent 投影。源码当前性、可评分性、血缘、公平性和 provider 隔离仍是独立强制门槛。

B2.5 继续保持权威的 `failed_closed_no_result` 收口；其失败不被重新分类为仅诊断性，也不存在任何 B2.5 分数或排名。

生产规模 Linux 压力验证现已完成。未来若要启动新的锦标赛，仍须单独预注册 gate/scorer 投影，资格化精确的未来运行时，并编写全新 holdout；不得复用 B2.5 treatment 输出或启动授权。
