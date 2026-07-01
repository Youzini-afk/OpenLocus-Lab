# BEA-v1-HAAE-R2L Next-Step Decision / Mechanism Preflight

日期：2026-07-01

BEA-v1-HAAE-R2L Next-Step Decision / Mechanism Preflight 是 R2K 之后的 public-only
decision package。它只读取 committed public artifacts/docs，不读取 private roots、
private material、source repos、raw fixture rows、CI、network、provider、runtime、
scheduler 或 selector systems。

```text
phase: BEA-v1-HAAE-R2L Next-Step Decision / Mechanism Preflight
status: haae_r2l_next_step_decision_mechanism_preflight_complete_r2m_mechanism_decomposition_authorized
self-test: 14/14
source lock: HAAE-R2K checkpoint 99600db
source status: haae_r2k_public_audit_package_complete_r2l_next_step_decision_authorized
context: separation signal but no method/default/scaling claim
decision: mechanism decomposition over existing R2I material
rejected/deferred: not scale/CI or new material generation yet
R2M contract: explicit opt-in private read only
R2M output: aggregate-only mechanism buckets
next phase: BEA-v1-HAAE-R2M Path-Prior Separation Mechanism Decomposition
R2M next only R2N public audit
```

R2L 只授权 R2M 作为 bounded mechanism decomposition step。R2M 必须在 explicit opt-in
下只读取 existing R2I private material root，不写 private rows，不生成 new
material/candidates，不运行 retrieval/runtime/source scan，不使用 CI/network/provider/
scheduler/selector，并且不提出 method winner、default 或 scaling claim。
