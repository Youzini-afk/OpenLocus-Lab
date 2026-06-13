# Real Provider CI All-Smoke

GitHub Actions run:

- workflow: `real-provider-benchmark`
- run id: `27460591592`
- stage: `all_smoke`
- environment: `production`
- remote_enabled: `true`
- views: `path_plus_symbol`

## Results

P2 embedding view bakeoff:

- provider_status: `ok`
- remote_calls: `4`
- FileRecall@3: `0.6666666666666666`
- primary_false_positive_rate: `1.0`
- citation_validity: `1.0`

P3 QuIVer readiness:

- provider_status: `ok`
- remote_calls: `7`
- quiver_fit: `mixed`
- BQ_overlap@10: `1.0`

P4 anchor-seeded diagnostic prototype:

- best_strategy: `flat_f32__source_vs_test_split__anchor_regex`
- SpanF0.5: `0.5434782608695652`
- added_gold_span: `2`
- added_false_span: `0`

P5 LLM derived/stress:

- llm_status: `ok`
- remote_calls: `1`
- derived_view_count: `20`
- stress_public_task_count: `24`
- private_labels: `not_uploaded_in_ci`

## Decision

- `promotion_ready=false`
- `default_should_change=false`
- dense-only remains supporting-only
- QuIVer remains diagnostic-only
- LLM remains derived/stress-only
- next step: add public CI corpus mode with repo/file/task caps

## Safety

- provider URL/key were read from GitHub production environment secrets only
- provider URL/key were not committed
- private labels were not uploaded
- artifact privacy validation passed
