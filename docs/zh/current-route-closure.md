# OpenLocus v2 当前路线关闭

日期：2026-07-04

OpenLocus v2 从已关闭路线的基线出发，而不是再开启 open-ended preflight chain。Phase 1 的范围是公开路线关闭文档、严格 RPM state-action trace schema、validator self-test，以及 aggregate-only schema report。

## 已关闭路线

除非出现具体 failing test、defect report 或 product workflow pain，以下路线停止：

- FRK-N 之后继续做 FRK kernel hardening。
- FRK-I no lift 之后继续 existing-trace selector variants。
- 下游/proxy no-lift 与 failure decomposition 之后复活 FRK-B/C RankPack。
- HAAE-S/HAAE-SF no lift 之后继续 simple scheduler redesign。
- 在 baseline-sufficient easy slice 上继续 LDI-A/LDI-B。
- 不增加 outcome-aligned executable evidence 的 static support-pair repair variants。

## 保留不变量

- EvidenceCore 仍是硬约束：candidate is not fact；被计数 evidence 必须 rematerialize current source，并通过 path/range/content validation。
- 本路线公开 artifact 为 aggregate/schema-only，除非后续另行授权 explicit sanitized-row contract；private state-action traces 保持私有。
- Label/outcome 只能在 action 之后或 offline evaluation 使用；state/action features 不允许 label leakage。
- FastContext 不是 runnable baseline。Hitmux 只有在 locally runnable 且 bounded 时才可作为 product/baseline reference。

## Phase 1 RPM trace schema

Phase 1 新增 `eval/rpm_trace_schema.py` 与公开报告 [`artifacts/rpm_trace_schema/rpm_trace_schema_report.json`](../../artifacts/rpm_trace_schema/rpm_trace_schema_report.json)。该 schema strict 且 fail-closed：required groups 包括 trace identity、task state、state features、action、policy learning support、observation/result、EvidenceCore linkage、outcome/label、privacy/execution、stop/go/source locks/readback。

Validator 会检查 closed enums、required fields、no unknown top-level keys、bucketized public fields、unique trace/step identifiers、monotonic step ordering、label timing/isolation、label-blind state/action features、behavior-policy probability markers、EvidenceCore currentness checks，以及 public aggregate-only leak scanning。

## Stop/go

Phase 1 只允许后续选择并单独实现一个 executable direction：

1. **RPM-D0 trace capture**：schema-conformant private state-action trace capture，并只发布 aggregate-only public report。
2. **FRK product workflow benchmark**：executable product-workflow benchmark，保留 private traces，并只发布 aggregate-only public report。

不授权：RPM training、default/method/scale/winner claims、provider/network/CI/runtime-default claims、FRK-J、FRK-B/C resurrection、LDI-B easy-slice continuation、HAAE-SG/T、broad source scan、candidate generation expansion、把 retrieval/pack rerun 当成 new algorithm work，或 raw publication。
