# Interventional Evidence Acquisition Phase 8A Fresh-Input Independence Protocol Freeze

日期：2026-07-08

Status: `phase8a_protocol_freeze_no_execution_no_claim`

Public report: [`phase8a_fresh_input_independence_protocol_freeze_report.json`](../../artifacts/phase8a_fresh_input_independence_protocol_freeze/phase8a_fresh_input_independence_protocol_freeze_report.json)

## 范围

Phase 8A 仅为 docs/report-only。它为可能的 Phase 8B 定义 future fresh-input construction 与 independence-audit contract。它不声称 independence 已 achieved、passed、validated 或 repaired。

Phase 8A 未读取 private inputs，未读取 ignored `runs/`，未读取 manifests，未 fetch/clone public repository，未读取 source，未生成 tasks，未填充 candidate registry，未执行 row/outcome scoring，也未执行 runner。它不提出 model、training、provider、LLM、runtime、default、product 或 method claim。

## Frozen future Phase 8B contract

- Phase 8B 必须先做 input construction 与 independence audit，而不是 scoring。
- 任何 private candidate source registry 都只属于 Phase 8B 的 ignored `runs/` 下，不属于 Phase 8A。
- Phase 8B 必须显式排除 Phase 5B、7B、7C 和 7E provenance。
- Comparable repo identity 必须覆盖 normalized URL forms、owner/name、可检测时的 fork/source repository、commit/SHA、clone origin、可用时的 package/module identity、exact paths/ranges/hashes、task IDs，以及 privately detectable 时的 file-family closeness。
- Attempt budget：最多 2 次 independent construction attempts；最多 inspect 16 个 candidate repos；target accepted repos 为 8-12；如果后续单独允许 scoring，future task hard max 仍为 150。
- Replacement 只允许在 outcome scoring 前发生，且原因只能是 clone failure、unavailable SHA、insufficient eligible files，或 failed independence/materialization precheck。看到 evidence outcomes 后绝不允许 replacement。
- Hard stops 包括 nonzero overlap、无法建立 comparable identity、不能在不放宽 freshness 的情况下达到 accepted task count、public report 需要 exact/private details，或 input independence audit passes 前发生任何 scoring。
- Public output 继续保持 aggregate-only：不包含 repo names/URLs/owners、commits/SHAs、paths/ranges/hashes/snippets、task IDs、row IDs、manifest paths、run dirs、per-repo/per-task details 或 singleton buckets。

## Boundary

Phase 8A 禁止另一个 Phase 7E repair loop。唯一 next authorized action 是单独的 Phase 8B input-construction/audit step，并且在 input independence audit passes 前仍不得 scoring。
