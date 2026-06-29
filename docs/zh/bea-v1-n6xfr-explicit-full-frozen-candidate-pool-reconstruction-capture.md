# BEA-v1-N6X-FR Explicit Full-Frozen Candidate-Pool Reconstruction Capture

日期：2026-06-28

BEA-v1-N6X-FR 是 N6XR 之后第一个显式 broader full-frozen reconstruction boundary。默认仅做 preflight。它验证 committed public artifacts 与 future full-frozen candidate-pool reconstruction capture 所需的 local prerequisite buckets，但不运行 network access、repository clones、OpenLocus binary、P4L/N1/N2/N3 reruns、retrieval、selector/reranker execution、counterfactuals、candidate-pool generation 或 materialization。

## 结果

```text
status: no_go_n6xfr_local_prerequisites_unavailable
self-test: 18 / 18
forbidden scan: pass
openlocus binary available: false
FD1 private decomposition available: false
P4L private source available: false
local prerequisites available: false
execution attempted: false
```

## 检查内容

N6X-FR 加载 public N4、N5、N6、N6F、N6G、N6XR、P4L 与 N2 artifacts，并验证 expected statuses。随后它在不读取 private file contents、也不公开 private paths/names 的前提下检查 prerequisite buckets：

- OpenLocus release binary availability；
- explicit FD1 private decomposition availability；
- P4L private source availability；
- 是否显式请求 canary 或 full-40 execution；
- private output boundary 是否保持 ignored 且 scanner-safe。

默认本地运行缺少 prerequisites，因此在 canary reconstruction 之前停止。

## Execution flags

CLI 接受未来 checkpoint flags：`--execute-canary`、`--execute-full-40`、`--openlocus`、`--fd1-private-decomposition-jsonl` 与 `--private-output-root`。在本 checkpoint 中，这些都是 safe no-op/preflight inputs：如果 prerequisites 不可用，不会尝试 network、clone、binary execution 或 replay。

## 决策

N6X-FR 不表示 method failure；它表示在 explicit full-frozen boundary 下，本地 capture prerequisites 不可用。下一阶段为 `none_until_full_frozen_reconstruction_prerequisites_are_available`。N6X-FR 不授权 N7、canary execution、full-40 capture、retrieval、full rerun、network/git clone、private reads、P5、BEA-v1-A、selector/reranker execution、counterfactuals、runtime/default changes、method-winner 声明或 downstream-value 声明。

## Artifact

- Script: `eval/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture.py`
- Report: `artifacts/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture/bea_v1_n6xfr_explicit_full_frozen_candidate_pool_reconstruction_capture_report.json`
