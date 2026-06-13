# Real-provider CI 大仓库 slice 测试结论（L1/L2）

日期：2026-06-13

状态：研究测试报告，不是 promotion evidence，不改变默认策略。

## 0. 测试目的

前一轮 P8/P9 只跑到很小的 public CI smoke：约 5 tasks / 80 records / 60 files。用户指出当前阶段需要“大型测试”。本轮目标是把真实 embedding 从 smoke 扩大到受控 large-repo slices，检验：

1. 真实 provider 在更大 CI workload 下是否稳定。
2. dense-only 文件召回是否随规模稳定。
3. SpanF0.5 是否改善到可用水平。
4. primary_false_positive_rate 是否仍可控。
5. QuIVer BQ readiness 和 anchor prototype 在大仓库 slice 上是否仍有正信号。

重要边界：这仍然是 **large-repo slice**，不是 full-repo exhaustive benchmark。每次 run 都有 task、record、file cap。

## 1. 安全与隐私边界

- Workflow: `real-provider-benchmark.yml`
- Trigger: `workflow_dispatch`
- Environment: GitHub `production`
- Remote: explicit `enable_remote_models=true`
- Provider view: `path_plus_symbol` only
- Model: `BAAI/bge-m3`
- Provider URL/key: 未写入 artifact / docs / git
- Raw source: 不发送、不上传
- Private labels: 不上传
- EvidenceCore semantics: 未改变
- Promotion: disabled

本轮会把 public repo 的 path/symbol metadata 与 public query text 发给 embedding provider，但不会发送 raw code、provider URL/key、private labels 或 evidence excerpts。

## 2. Harness 修复

大型测试前发现两个可靠性问题并修复：

1. **R32 远程 embedding 串行请求且吞掉 provider 错误原因**
   - 修复：增加批量请求、重试、脱敏 reason code。
   - 提交：`4ea9025 improve real provider embedding batching`

2. **P2 artifact 只记录 record embedding calls，不记录 query embedding calls**
   - 修复：query embedding 也批量化，并在 report 中记录 total `remote_calls` / `remote_requests` / `remote_texts`。
   - 提交：`6c3cdef report real embedding request counts`
   - 后续 L2 提升 cap：`f554ddd raise real provider large test caps`

## 3. L1：受控 large-repo slice

### 3.1 L1 canary

Repo: `py_django`

Caps: 5 tasks / 80 records / 120 files

Run: `27463000074`

| Metric | Value |
|---|---:|
| provider_status | ok |
| FileRecall@1 | 0.800 |
| FileRecall@3 | 1.000 |
| SpanF0.5 | 0.0179 |
| primary_false_positive_rate | 0.000 |
| citation_validity | 1.000 |

结论：provider 与安全边界可用，但 span quality 很低。

### 3.2 L1 medium caps

Caps: 10 tasks / 100 records / 250 files

| Repo | Run | FileRecall@1 | FileRecall@3 | FileRecall@5 | SpanF0.5 | PFP | Citation |
|---|---:|---:|---:|---:|---:|---:|---:|
| `py_django` | 27463045465 | 0.700 | 0.900 | 0.900 | 0.0089 | 0.000 | 1.000 |
| `rust_deno` | 27463045848 | 0.800 | 0.900 | 0.900 | 0.1042 | 0.000 | 1.000 |
| `ts_nextjs` | 27463104375 | 0.100 | 0.100 | 0.100 | 0.0056 | 0.000 | 1.000 |
| `go_kubernetes` | 27463104726 | 1.000 | 1.000 | 1.000 | 0.0394 | 0.000 | 1.000 |

结论：L1 medium caps 下 file recall 分化明显。Kubernetes/Rust Deno/Django 有文件级信号，Next.js 很弱；SpanF0.5 仍整体低。

### 3.3 L1 max caps

Caps: 20 tasks / 200 records / 500 files

| Repo | Run | FileRecall@1 | FileRecall@3 | FileRecall@5 | SpanF0.5 | PFP | Citation |
|---|---:|---:|---:|---:|---:|---:|---:|
| `py_django` | 27463176417 | 0.750 | 0.900 | 0.950 | 0.0089 | 0.000 | 1.000 |
| `rust_deno` | 27463176822 | 0.000 | 0.000 | 0.000 | 0.0000 | 0.000 | 1.000 |
| `ts_nextjs` | 27463236632 | 0.050 | 0.050 | 0.050 | 0.0050 | 0.000 | 1.000 |
| `go_kubernetes` | 27463236989 | 0.650 | 0.700 | 0.750 | 0.0316 | 0.000 | 1.000 |

结论：L1 max caps 后，Deno 的 file recall 从 medium caps 的 0.8 变成 0，说明 dense-only 对 slice/cap 非常敏感。Django/Kubernetes 仍有文件召回，但 span quality 低；Next.js 仍弱。

## 4. L1 P3：QuIVer BQ readiness 子集

Caps: 20 tasks / 200 records / 500 files

| Repo | Run | BQ_overlap@10 | BQ_overlap@50 | BQ_overlap@100 | BQ_vs_f32_MRR | sign_entropy_mean | quiver_fit |
|---|---:|---:|---:|---:|---:|---:|---|
| `py_django` | 27463309315 | 0.605 | 0.679 | 0.791 | 0.790 | 0.623 | promising |
| `go_kubernetes` | 27463309742 | 0.645 | 0.646 | 0.749 | 0.808 | 0.626 | mixed |

结论：BQ diagnostics 在大仓库 slice 上仍有非空信号，Django 偏 promising，Kubernetes mixed。但这仍然不是 QuIVer graph/ANN 质量证明；没有 Vamana graph、没有 ANN backend quality claim。

## 5. L1 P4：anchor prototype 子集

Caps: 20 tasks / 200 records / 500 files

| Repo | Run | Best strategy | FileRecall@1 | FileRecall@3 | SpanF0.5 | added_gold_span | added_false_span | hard_negative_hit_rate | Citation |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| `py_django` | 27463384236 | `flat_f32__source_vs_test_split__anchor_regex` | 0.850 | 0.950 | 0.000 | 0 | 40 | 0.350 | 1.000 |
| `go_kubernetes` | 27463384579 | `flat_f32__global_mixed_all__anchor_regex` | 0.650 | 0.700 | 0.074 | 5 | 44 | 0.100 | 1.000 |

结论：Anchor prototype 没有解决 file recall 与 span quality 的权衡。它相对 L1 max P2 提升了 Django 的 FileRecall@1，但 Kubernetes 基本持平；两个 repo 都出现 added_false 远大于 added_gold。因此 default expansion 仍应 blocked。

## 6. L2：更大 large-repo slice

Caps: 60 tasks / 1000 records / 2000 files

每个 run 约 1060 remote embedding texts，通过 batching 降到约 67 HTTP requests。

| Repo | Run | FileRecall@1 | FileRecall@3 | FileRecall@5 | SpanF0.5 | PFP | Citation | remote_texts | remote_requests |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `py_django` | 27463522968 | 0.250 | 0.283 | 0.283 | 0.0042 | 1.000 | 1.000 | 1060 | 67 |
| `go_kubernetes` | 27463605172 | 0.267 | 0.267 | 0.267 | 0.0223 | 1.000 | 1.000 | 1060 | 67 |
| `ts_nextjs` | 27463605587 | 0.017 | 0.017 | 0.017 | 0.0030 | 1.000 | 1.000 | 1060 | 67 |
| `rust_deno` | 27463711523 | 0.000 | 0.000 | 0.000 | 0.0000 | 1.000 | 1.000 | 1060 | 67 |

结论非常明确：当 slice 扩大到 60 tasks / 1000 records / 2000 files 后，dense-only 的 file recall 不稳定且整体下降；SpanF0.5 仍极低；primary_false_positive_rate 在四个 repo 中均为 1.0。dense-only / global dense 不能 primary，也不能 default。

## 7. 关键研究结论更新

1. **现在已经跑过大型真实-provider测试，但它仍是 large-repo slice，不是 full-repo exhaustive benchmark。**
2. **真实 embedding 的文件级召回信号在小/中 slice 上存在，但不稳定。** L2 扩大后，Django/Kubernetes 降到约 0.25，Next.js/Deno 接近 0。
3. **在这些 bge-m3 + `path_plus_symbol` dense-only L2 slice 中，SpanF0.5 没有改善。** L2 最高也只有约 `0.022`。
4. **Dense-only primary 明确不安全。** L2 四个 repo 的 PFP 都是 1.0。
5. **Anchor prototype 仍然不能 default expansion。** L1 P4 中 added_false 明显大于 added_gold。
6. **QuIVer BQ diagnostics 仍值得继续，但只能 diagnostic。** BQ overlap 不空，但没有 graph/ANN quality。
7. **所有有效 run 的 citation gate 与 artifact privacy check 均通过。** citation_validity 为 `1.0`，上传 artifact 未包含 provider secret、raw source、private labels 或 evidence excerpts。

## 8. 对当前研究方向的影响

这轮大型测试把结论从“真实 embedding 有希望，但需要扩大验证”推进到：

```text
真实 embedding 有候选/文件级信号，但在大型 slice 上不稳定；dense-only / global dense 不能 primary/default。
```

更具体地说：

- Dense/QuIVer 必须继续 supporting-only。
- 下一步不应继续追求 global dense top-k。
- 研究重点应该转向：
  - better view construction，不能只靠 `path_plus_symbol`；
  - lexical/symbol seeded retrieval；
  - admission_v2 只把 dense score 作为 supporting feature；
  - source/test/generated/vendor sharding；
  - Span targeting，而不是只看 file recall。

## 9. 下一步建议

1. 在明确 public/opt-in rich-context 模式下跑 L2/P21-G multi-view/context-injection 对照：raw chunks、snippet windows、signature/body windows、path-symbol-raw hybrids、model profiles 和 context packs。继续排除 secrets、ignored files、provider keys、private labels/gold answers。
2. 对 L2 的 false positives 做 failure cluster：是否来自 generated/vendor、test/source confusion、same-name symbol、path-only noise。
3. 增加 lexical anchor seeded 的 P2/P4 版本，不让 dense 在 1000 records 中 global top-k。
4. 将 L2 tasks 固定成 reproducible suite，避免每次 task generation drift。
5. 在 P4 中改用 span-aware rerank/line-localization，否则 file recall 不会转化为 SpanF0.5。

## 10. 当前一句话结论

这轮大仓库 slice 真实-provider 测试没有支持 promotion。它证明 global dense-only retrieval 不够：真实 embedding 在小 slice 上有文件级信号，但在更大的 large-repo slice 上迅速暴露出不稳定、低 SpanF0.5 和高 primary false-positive 风险，因此必须继续作为 supporting/candidate 层，而不能进入默认 primary 路径。下一步质量导向不是继续 metadata-only 的 `path_plus_symbol`，而是使用 richer code context，并同时度量 latency/cost，EvidenceCore 仍作为最终事实权威。
