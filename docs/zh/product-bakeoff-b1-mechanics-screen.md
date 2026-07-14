# 产品栈对比 — B1 机械能力筛查收口

日期：2026-07-14

状态：`b1_mechanics_screen_complete_aggregate_only_no_product_winner_claim`

项目所有者已授权公开 B1 合成机械能力结果的聚合摘要。授权记录在源码检查点 `0b6f2e13b1dbc679eb1f827c28a8abd5403dcd58`；该授权不包括私有逐行数据、任务/查询/路径细节、回执、trace、资源样本，也不构成任何产品获胜者、默认方案或有效性主张。

## 结果

冻结的 B1 v2.4 筛查通过：

- 共 504 条对比记录：360 条单步、144 条双步；
- 504 条接受，0 条拒绝；
- 六个内部栈全部通过；
- 父进程拥有的哨兵 2,256/2,256 通过；
- 504 条记录全部具有完整可信资源采样和同次执行可评分捕获；
- 冷/热语义一致、三次重复确定性和全部双步血缘均通过；
- provider/网络调用数为 0；
- 私有 canary 保持私有，未进入公开聚合摘要。

精确的闭合聚合结果发布在 [`product_bakeoff_b1_mechanics_screen_aggregate.json`](../../artifacts/product_bakeoff_b1/product_bakeoff_b1_mechanics_screen_aggregate.json)。

## 这证明了什么

B1 证明六个累积内部栈 S0–S5 能在两个合成 fixture 上端到端执行冻结的合成机械契约。其中包括生产级持久化 BM25、精确字面检索、精确名称 AST 符号检索、条件式深度 1 图检索、有界 target/support 组装、冷/热状态复用、原生分数完全相同时使用竞赛排名（`1, 1, 3`），以及图通道权重为 2、其他通道权重为 1。

B1 不对六个栈排序，不选择产品默认，不证明检索质量，不验证真实仓库，不比较外部算法，也不建立生产延迟/内存边界。这些属于 B2 及后续阶段的决策。

## 可复现锁定信息

- 源码检查点：`0b6f2e13b1dbc679eb1f827c28a8abd5403dcd58`
- 规格：`product_bakeoff_b1.v2.4`
- 规格摘要：`b1spec_6058c3e732d077f5`
- Fixture 摘要：`b1fix_b012d3da68d75522`
- 源码包摘要：`b1src_fa5b30ca188d08a491206e13acfe3faa9a5070a68be2222ba349392101b136d2`
- 运行时包摘要：`b1run_01c1fdcfe6d77f3d1f8101f66a90191a1f4a620d43e39a139b686149e0b2a896`
- 完整筛查前的独立预检：168 条记录，0 失败

本地执行入口为：

```text
python eval/product_bakeoff_b1_cli.py --self-test
python eval/product_bakeoff_b1_cli.py --fault-test
python eval/product_bakeoff_b1_cli.py --probe --runs-dir <ignored-local-directory>
python eval/product_bakeoff_b1_cli.py --full-screen --runs-dir <ignored-local-directory>
```

所有逐行输出继续保留在 Git 忽略的本地目录中；公开内容只有上面的已校验闭合聚合摘要。

## 下一阶段

B1 已冻结并收口。下一项产品决策工作是 B2：预注册的 48 任务内部锦标赛，在不依据决策集做事后调参的前提下，比较正确性、上下文质量、延迟、内存、弃答和支持证据行为。
