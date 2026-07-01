# BEA-v1-HAAE-R2Z Real-File Candidate Material Preflight

日期：2026-07-01

BEA-v1-HAAE-R2Z Real-File Candidate Material Preflight 是 public-only
design/preflight。它只读取 public R2Y/R2X/R2W artifacts/docs，必要时只读取 public
fixture metadata。它不执行 execution、private read/write、candidate generation、source
scan、retrieval、OpenLocus/runtime、CI、network、provider call、clone、scheduler 或
selector。

```text
phase: BEA-v1-HAAE-R2Z Real-File Candidate Material Preflight
status: haae_r2z_real_file_candidate_material_preflight_complete_r2aa_actual_explicit_local_real_file_material_smoke_authorized
self-test: 20/20
source lock: HAAE-R2Y checkpoint b56462a
source status: haae_r2y_content_identifier_next_step_decision_design_complete_r2z_real_file_candidate_material_preflight_authorized
next phase: BEA-v1-HAAE-R2AA Actual Explicit Local Real-File Material Smoke
operator public corpus manifest/allowlist required
no broad workspace scan
no network clone by default
target 20
candidate depth 40
source file cap 500
row cap 20000
wall-clock cap 20 minutes
gold private eval only not policy
public aggregate-only
no execution/private/candidate generation/source scan/CI in R2Z
future private rows may contain real file candidate references but not R2Z
claim boundary: no method/default/scaling
```

R2Z 定义未来 explicit local real-file candidate material smoke 的 exact bounded
recipe。R2Z 本身不发布 real file candidates，只在后续 explicit opt-in boundary 下授权
R2AA smoke phase。


R2Z performs no execution/private write/candidate generation/source scan; R2AA bounded local execution authorized; R2AA broad workspace scan/CI/network/runtime false.
