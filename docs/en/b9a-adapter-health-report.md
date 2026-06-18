# B9A Adapter Health Repair Screen

B9A is an adapter-health report, not a quality leaderboard. It checks whether GLM/Qwen model profiles can reliably produce structured bounded candidate decisions under small live screens.

| Adapter | Calls | Schema valid rate | Infra failure rate | Health status | Latency p50 mean ms |
| --- | ---: | ---: | ---: | --- | ---: |
| `glm_5_2_tool_call` | 16 | 0.375 | 0.750 | `not_quality_interpretable_adapter_health` | 1698.0 |
| `glm_5_2_json_schema_strict` | 12 | 0.833 | 0.333 | `not_quality_interpretable_adapter_health` | 1748.0 |
| `qwen3_6_27b_tool_call` | 12 | 0.750 | 0.500 | `not_quality_interpretable_adapter_health` | 5394.0 |
| `qwen3_6_27b_json_schema_strict` | 12 | 1.000 | 0.000 | `quality_interpretable_health_pass` | 4698.5 |

## Interpretation

- Output mode is treated as a model-adapter configuration parameter, not an OpenLocus algorithm variable.
- Qwen3.6-27B `json_schema_strict` passed this small sequential health screen and can be used for cautious low-volume follow-up.
- GLM-5.2 `json_schema_strict` improved over the worst tool-call behavior, but it is still not quality-interpretable in this screen and should not yet be used for policy quality conclusions.
- GLM-5.2 `tool_call` and Qwen `tool_call` remain too noisy for critical-path validation.
