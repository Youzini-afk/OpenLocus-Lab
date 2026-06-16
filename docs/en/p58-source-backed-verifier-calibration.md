# P58 Source-Backed Verifier Calibration v0

- Schema: `p58-source-backed-verifier-calibration-v0`
- Generated: 2026-06-16T11:04:55.122222+00:00
- Status: `self_test_only`
- Self-test: True
- Remote calls by P58: 0
- LLM calls by P58: 0
- Prompt construction by P58: False
- Source reads attempted by P58: False
- Provider config read by P58: False

## Purpose

P58 Source-Backed Verifier Calibration v0 consumes only public aggregate JSON reports from upstream diagnostics (P48, P52C, P51B, P57, and optionally P52B/P52A/P49) and turns their availability/distributions into coarse, deterministic planning/action-hint buckets. 
It is **not** a verifier, **not** admission, **not** Evidence, **not** default/promotion, and **not** live-readiness evidence. 
No source files, candidate pools, prompts, responses, provider configs, or per-candidate rows are read.

## Methodology

- Read only aggregate upstream report JSON (no `--input`, `--repo-lock`, `--source-root`, no provider/model/prompt arguments).
- Required upstream reports: P48, P52C, P51B, P57.
- Optional upstream reports: P52B, P52A, P49.
- Collapse upstream statuses to an allowlisted safe enum.
- Verify upstream safety flags where present: promotion/default false, `candidate_not_fact=true`, aggregate-only true, remote/LLM/prompt counters zero or bounded-source-reads only for source-read phases.
- Extract only aggregate counts/rates from known paths; missing fields are `null` plus availability enum, never fake zeros.
- Emit coarse hint buckets for request-more-context priority, local-verifier priority, and P51-C eligibility planning.

## Safety notes

- P58 makes no remote, LLM, or provider calls.
- P58 does not construct prompts, read source files, or access candidate pools.
- P58 does not publish task IDs, candidate IDs, repo IDs, datasets, paths, spans, line ranges, digests, queries, snippets, prompts, responses, providers, models, URLs, or keys.
- P58 output is aggregate-only and explicitly flagged as not quality evidence, not a verifier pass/fail, not admission, and not default/promotion/live readiness.

## Input summary

- Required reports: p48, p52c, p51b, p57
- Optional reports: p52b, p52a, p49
- Required present count: 4/4
- Optional present count: 3/3
- Required missing: none
- Invalid JSON upstream reports: 0

### Upstream status by phase

| Phase | Status |
|---|---|
| p48 | `self_test_only` |
| p52c | `self_test_only` |
| p51b | `self_test_only` |
| p57 | `insufficient_matrix` |
| p52b | `self_test_only` |
| p52a | `self_test_only` |
| p49 | `self_test_only` |

## Upstream safety summary

- Checked phase count: 7
- Safety blocker count: 0
- Safety warning count: 0
- P57 `insufficient_matrix` acceptable: True

| Phase | Present | Status | Safety blocker | Warnings |
|---|---|---|---|---|
| p48 | True | `self_test_only` | False | 0 |
| p52c | True | `self_test_only` | False | 0 |
| p51b | True | `self_test_only` | False | 0 |
| p57 | True | `insufficient_matrix` | False | 0 |
| p52b | True | `self_test_only` | False | 0 |
| p52a | True | `self_test_only` | False | 0 |
| p49 | True | `self_test_only` | False | 0 |

## Calibration denominators

- P52C candidate denominator: 100
- P52C score candidate denominator: 95
- P51B candidate denominator: 100
- P51B eligible candidate count: 40
- P48 selected count: 100
- P48 request-more-context count: 20
- Calibration denominator availability: `available`

## Source-backed coverage

- Source-backed coverage bucket: `source_backed_available`
- P52C score availability: `available_source_backed`
- Source-backed score candidate denominator: 60
- Metadata-only candidate denominator: 35
- Score unavailable candidate rate: 0.0500
- Source-backed is not verification: True

## P52C bucket carry-forward

- Score bucket distribution available: True
- Diagnostic score high rate: 0.2000
- Diagnostic score medium rate: 0.5053
- Diagnostic score low rate: 0.2000
- Diagnostic score unavailable rate: 0.1000
- P52C distribution is not pass/fail: True

## Request-more-context calibration

- Hint bucket: `medium`
- Request-more-context rate: 0.2000
- Demoted primary rate: 0.1000
- P52C low/unavailable rate: 0.3000
- Calibration basis: `aggregate_p48_p52c`
- Diagnostic only: True
- Not admission: True

## Local verifier priority calibration

- Hint bucket: `high`
- Source-backed coverage bucket: `source_backed_available`
- Diagnostic score distribution available: True
- Component coverage available: True
- Diagnostic only: True
- Not verifier pass/fail: True
- Not admission: True

## P51-C eligibility calibration

- Hint bucket: `p51c_planning_source_backed`
- Eligibility availability: `available_source_backed`
- Source-backed live eligibility available: True
- Eligible candidate rate: 0.4000
- Request-envelope blueprint count: 10
- Budget violation rate: 0.1000
- Redaction required rate: 0.2000
- Diagnostic only: True
- Not live readiness: True
- Not provider authorization flag set: True

## Blockers

- none

## Warnings

- P57 reports insufficient_matrix; this is acceptable for P58 calibration.

## Conclusion

- P58 Source-Backed Verifier Calibration v0 is a deterministic, aggregate-only planning-hint report.
- P58 does not read source files, candidate pools, prompts, responses, provider configs, or per-candidate rows.
- P58 does not call LLMs, providers, or networks, and does not construct prompts.
- P58 is not quality evidence, not a verifier pass/fail, not Evidence, not admission, and not default/promotion/live readiness.
- This self-test exercised the calibration paths with synthetic upstream aggregate reports.
- Calibration warning(s): 1.
- Current status: self_test_only. Source-backed coverage bucket: source_backed_available; request-more-context hint: medium; local-verifier priority hint: high; P51-C eligibility hint: p51c_planning_source_backed.
