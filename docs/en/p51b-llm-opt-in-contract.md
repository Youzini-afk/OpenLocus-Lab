# P51-B LLM Opt-In Contract / Dry-Run Payload Validator

- Schema: `p51b-llm-opt-in-contract-v1`
- Generated: 2026-06-15T21:21:31.040832+00:00
- Status: `self_test_only`
- Self-test: True
- Remote calls by P51-B: 0
- LLM calls by P51-B: 0
- Remote requests by P51-B: 0
- Prompt construction by P51-B: False
- Dry-run payload validation only: True
- P51-B live calls disabled: True
- Tasks: 5 positive=4 no_gold=1
- Candidate pool availability: `partial`
- Gold span availability: `available`
- P51 report source: `not_provided`
- P52C report source: `not_provided`
- P52B report source: `not_provided`
- P49 report source: `not_provided`
- P50 report source: `not_provided`
- P48 report source: `not_provided`

## Purpose

P51-B defines a future live LLM opt-in contract and validates dry-run payload schemas. It performs no provider calls, constructs no prompts, and stores no raw requests, outputs, snippets, or responses.

## Methodology

- Load `p25-policy-records-ephemeral-v1` records (or deterministic self-test records).
- Normalize candidates with P46/P49 helpers and apply deterministic P51 eligibility filters using public metadata only; gold and outcomes are not used.
- Consume upstream aggregate reports (P51/P52C/P49/P52B/P52A/P52/P50/P48) as enum/status carry-forward only.
- Build request-envelope blueprint metadata from eligible candidates: candidate counts, line/character budgets, and future cap violations; no prompt strings are constructed.
- Validate synthetic role-output schemas in memory with fail-closed rules (`not_evidence=true`, role enum, no unknown fields, bounded candidate refs and line deltas).
- Emit aggregate readiness diagnostics and a contract manifest with future caps only; no provider, model, URL, or key is published.

## Safety notes

- P51-B does not call an LLM or any remote provider.
- P51-B does not construct prompts.
- P51-B does not store raw request envelopes, prompts, outputs, responses, snippets, source text, queries, paths, spans, or digests.
- P51-B does not publish providers, models, base URLs, or API keys.
- P51-B output is not Evidence, not quality evidence, and does not indicate live readiness or default/promotion.
- Role-output schema validation uses synthetic in-memory fixtures only.

## Contract manifest

- Contract schema version: `p51b-llm-opt-in-contract-v1`
- Supported roles: ['span_narrow', 'filter', 'abstain'] (3)
- Supported output modes: ['json_object', 'json_schema_strict', 'tool_call']
- Live-call lane availability: `disabled_p51b`
- Allowed remote mode: `future_remote_opt_in_only`
- Future caps:
  - max_remote_calls_future_cap: 1
  - max_candidates_per_request: 6
  - max_lines_per_candidate: 120
  - max_total_lines_per_request: 360
  - max_request_chars_future_cap: 16000
  - max_output_chars_future_cap: 4000
  - timeout_seconds_future_cap: 60
  - retry_policy_future_cap: {'max_retries': 1, 'retry_on_schema_error': True}
  - schema_repair_retry_future_cap: 1

## Eligibility

- Candidate denominator: 6
- Eligible candidates: 2 (0.3333)
- Eligible packs: 1 (0.2000)
- Eligible span_narrow: 2 (0.3333)
- Eligible filter: 0 (0.0000)
- Eligible abstain: 0 (0.0000)
- Eligibility availability: `partial_metadata_only`
- Source-backed live eligibility available: False
- Ineligible reason counts:
  - no_contrast_pack: 2 (0.3333)
  - metadata_high_risk: 2 (0.3333)

## Request-envelope blueprint

- Blueprint count: 3
- Mean candidates per envelope: 2.0000
- P95 candidates per envelope: 2.0000
- Mean line budget: 20.0000
- P95 line budget: 20.0000
- Mean context-char budget: 800.0000
- P95 context-char budget: 800.0000
- Max budget violation count/rate: 0 / 0.0000
- Redaction required count/rate: 3 / 1.0000
- Secret-scan availability: `aggregate_metadata_only`
- Request-envelope-not-prompt: `True`
- Raw request envelopes stored: `False`

## Role-output schema validation

- Self-test count: 9
- Valid count/rate: 3 / 1.0000
- Invalid reject count/rate: 6 / 1.0000
- Unknown-field rejections: 1
- Missing `not_evidence` rejections: 1
- Line-delta out-of-bounds rejections: 2
- Candidate-ref out-of-bounds rejections: 2

## Future live gate readiness

- p51b_live_gate_ready: True
- p51b_live_gate_ready_reason: `contract_valid_dry_run_only`

## Conclusion

- Self-test-only contract validation processed 5 synthetic tasks; this is not quality evidence.
- P51-B does not call an LLM, does not construct prompts, and does not send requests to any provider.
- Eligibility is deterministic and uses only public metadata and P52C aggregate availability; gold and outcomes are not used.
- Request-envelope blueprints are metadata-only shapes; raw prompts, snippets, outputs, and responses are not stored.
- Role-output schema validation is performed on synthetic in-memory fixtures only.
- This is a contract-readiness dry run, not Evidence, not quality evidence, and not a live run.
