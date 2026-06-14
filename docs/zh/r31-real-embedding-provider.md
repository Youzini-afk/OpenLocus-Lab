# R31 Real Embedding Provider Smoke

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# R31 Real Embedding Provider Smoke

R31 adds an OpenAI-compatible embedding provider scaffold and validates it with a local HTTP server. It does not call the user's real provider, does not read labels, does not change EvidenceCore, and does not promote DenseReal.

## Safety Gates

- remote_denied_by_default: `True`
- openai_compatible_hidden_until_env_enabled: `True`
- openai_compatible_visible_when_env_enabled: `True`
- provider_build_success: `True`
- provider_search_success: `True`
- audit_file_exists: `True`
- vector_store_exists: `True`
- audit_contains_no_raw_query: `True`
- audit_contains_no_raw_code: `True`
- artifacts_contain_no_api_key: `True`
- artifacts_contain_no_base_url: `True`
- evidence_materialized: `True`
- citation_shape_present: `True`
- no_quality_claim: `True`

## Counts

- server_embedding_requests: `2`
- server_bad_paths: `0`
- server_bad_auth: `0`
- build_remote_calls: `1`
- search_remote_calls: `1`
- record_count: `1`
- evidence_count: `1`
- leak_count: `0`

## Decision

- `promotion_ready=false`
- `default_should_change=false`
- DenseReal remains candidate/supporting-only.
- No runtime artifact may contain raw query, raw code, provider URL, or API key.

