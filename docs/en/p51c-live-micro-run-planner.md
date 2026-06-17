# P51-C0 Live LLM Micro-Run Planner / Explicit Opt-In Gate

- Schema: `p51c-live-micro-run-planner-v0`
- Generated: 2026-06-17T07:28:37.409367+00:00
- Status: `self_test_only`
- Self-test: True
- Planner only: True
- P51-C live calls disabled: True
- Remote calls by P51-C: 0
- LLM calls by P51-C: 0
- Remote requests by P51-C: 0
- Prompt construction by P51-C: False
- Provider spend authorization flag: False
- Live run authorization flag: False

## Purpose

P51-C0 is a planner-only explicit opt-in gate. It validates whether a future P51-C live LLM micro-run may be manually launched. 
It is **not** quality evidence, **not** authorization, **not** Evidence, **not** a promotion/default gate, and **not** a claim that a live run is safe or ready.
No provider calls, prompt construction, source reads, ephemeral record reads, or spend authorization are performed.

## Methodology

- Require `--p51c-live-opt-in` and a matching `--ack-not-evidence` string.
- Read only aggregate upstream reports (`--p61-report`, `--p51b-report`).
- Confirm P61 status is `micro_run_preconditions_met`, provider spend is not authorized, the decision is not authorization, and a separate dispatch is required.
- Confirm P51-B contract readiness, source-backed eligibility, role-output schema validity, and redaction preconditions are satisfied.
- Validate requested budget caps do not exceed the P51-B dry-run contract caps and that exactly one remote call is planned.
- Confirm the output mode is `json_schema_strict` or `tool_call` and the dataset/repo are within allowlists.
- Emit an aggregate planner config that uses `repo_scope='public_ci_smoke_allowlist'` and never exposes raw repo identity, paths, spans, prompts, responses, providers, models, or keys.

## Safety notes

- P51-C0 makes no remote, LLM, or provider calls.
- P51-C0 does not construct prompts, read source files, or access ephemeral records.
- P51-C0 does not publish task IDs, candidate IDs, repo IDs, paths, spans, line ranges, digests, queries, snippets, prompts, responses, providers, models, URLs, or keys.
- P51-C0 output is aggregate-only and explicitly flagged as not quality evidence, not authorization, not Evidence, and not default/promotion/live readiness.

## Input summary

- P61 report present: True
- P61 status: `micro_run_preconditions_met`
- P61 preconditions met: True
- P51-B report present: True
- P51-B status: `ok`
- P51-B live gate ready: True
- P51-B live gate ready reason: `contract_valid_dry_run_only`
- P51-B eligible candidates: 10
- P51-B eligible packs: 5
- P51-B blueprint count: 3
- P51-B source-backed eligibility available: True
- P51-B schema valid rate: 1.0000
- P51-B redaction precondition satisfied: True
- P51-B redaction policy consistent: True
- P51-B runtime redaction still required by P51-C: True

## Gate checks

- Explicit opt-in present: True
- Acknowledgement matches required string: True
- Dataset allowed: True
- Repo in allowlist: True
- Output mode allowed: True
- P61 report present: True
- P61 preconditions met: True
- P51-B report present: True
- P51-B contract ready: True
- P51-B budget caps respected: True
- Provider config safe: True

## Budget check

- Requested max remote calls total: 1 (P51-B cap: 1, must equal 1)
- Requested max request chars: 16000 (P51-B cap: 16000)
- Requested max output chars: 4000 (P51-B cap: 4000)
- Requested max candidates per request: 6 (P51-B cap: 6)
- Requested max total lines per request: 360 (P51-B cap: 360)
- Requested timeout seconds: 60 (P51-B cap: 60)

## Planner config

- p51c_live_opt_in: True
- ack_not_evidence: `I_UNDERSTAND_P51C_NOT_EVIDENCE`
- dataset: `ci_smoke`
- repo_scope: `public_ci_smoke_allowlist`
- llm_output_mode: `json_schema_strict`
- max_remote_calls_total: 1
- max_request_chars: 16000
- max_output_chars: 4000
- max_candidates_per_request: 6
- max_total_lines_per_request: 360
- timeout_seconds: 60
- allowed output modes: ['json_schema_strict', 'tool_call']
- allowed datasets: ['ci_smoke', 'self_test']

## Conclusion

- P51-C0 Live LLM Micro-Run Planner is a planner-only explicit opt-in gate.
- P51-C0 does not call providers, does not construct prompts, does not read source, and does not authorize spend.
- P51-C0 is not quality evidence, not Evidence, not authorization, not default/promotion, and not live readiness.
- A future P51-C live LLM micro-run remains a separate explicit human or workflow_dispatch decision.
- This self-test exercised the planning/gate logic with synthetic aggregate inputs.
- Current planner status: self_test_only.
