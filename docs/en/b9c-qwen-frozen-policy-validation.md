# B9C Qwen Frozen-Policy Validation

Date: 2026-06-18

B9C validates the B6C frozen balanced-policy candidate under the Qwen secondary
adapter identified by B9B. It reuses the B6D cross-adapter frozen-validation
runner with `model_adapter=qwen3_6_27b_json_schema_strict`.

B9C does not search, retune, or change the frozen policy. Output mode is treated
as the Qwen adapter configuration, not as an OpenLocus algorithm variable.

## Run

```text
run: 27744695226
model: [mk]Qwen3.6-27B
adapter/output mode: json_schema_strict
stage: b6d_cross_adapter_frozen_validation
dataset: ci_smoke
max_tasks: 6
task_sample_mode: round_robin_public_buckets
```

The workflow completed successfully and passed artifact privacy gates.

## Adapter health and comparability

```text
status: ok
quality_interpretable: true
direction_consistency: consistent_with_kimi
schema_valid_rate: 1.0
infra_failure_rate: 0.0
included_repo_count: 4
comparable_task_count: 24
policy_search_performed: false
freshness_contract_valid: true
```

## Frozen-policy results

| Policy family | Added gold | Added false | False/gold | Mean SpanF0.5 | Mean PFP | Estimated LLM actions | Net span value 2x |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| P25 bucket-routed baseline | 6 | 5 | 0.833 | 0.0932 | 0.0417 | 24 | -4 |
| Balanced frozen policy | 6 | 4 | 0.667 | 0.0932 | 0.0000 | 12 | -2 |
| Conservative frozen policy | 4 | 1 | 0.250 | 0.0741 | 0.0000 | 4 | 2 |

The balanced frozen policy preserved P25's added gold and mean SpanF0.5 while
reducing false spans, removing observed PFP, and halving estimated LLM actions.
This is directionally consistent with the Kimi B6C/B6E/B6F results.

## Interpretation

B9C upgrades Qwen from "quality-interpretable adapter candidate" to a secondary
adapter that supports the frozen balanced-policy direction on a small smoke
matrix. It still does not make the policy a default:

```text
not promotion
not Evidence admission
not model leaderboard
not output-mode leaderboard
still low-n smoke
```

The important algorithmic signal is not that Qwen is better than Kimi; it is that
the frozen policy's qualitative direction survives a second, health-stable model
adapter.
