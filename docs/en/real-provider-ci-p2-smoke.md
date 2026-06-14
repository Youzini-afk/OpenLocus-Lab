# Real Provider CI P2 Smoke

GitHub Actions run:

- workflow: `real-provider-benchmark`
- run id: `27460471971`
- stage: `p2_embedding`
- environment: `production`
- remote_enabled: `true`
- views: `path_plus_symbol`

Result:

- provider_status: `ok`
- remote_calls: `4`
- FileRecall@3: `0.6666666666666666`
- primary_false_positive_rate: `1.0`
- citation_validity: `1.0`
- promotion_ready: `false`
- default_should_change: `false`

Safety:

- provider URL/key were read from GitHub production environment secrets only
- no provider URL/key is committed
- private labels were not uploaded
- artifact privacy validation passed

Interpretation remains unchanged: real dense retrieval is available in CI, but dense-only stays supporting-only because false-primary remains high on the smoke task set.
