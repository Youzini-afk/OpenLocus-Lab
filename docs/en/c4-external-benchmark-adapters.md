# C4 External Benchmark Adapters — Schema + Row-Mapping Readiness v1

Date: 2026-06-20 (C4.1 schema readiness; C4.2 ContextBench verified subset
row-mapping smoke; C4.3 SWE-Explore row-mapping / line-budget aggregate
smoke; C4.4 CORE-Bench source readiness / no-go; C4.5 RepoQA
source/schema-contract readiness with adapter deferred)

C4.1 is the **external benchmark adapter / schema readiness** phase and
C4.2 is the **ContextBench verified subset row-mapping smoke** phase.
Neither is an external benchmark performance evaluation, a benchmark
result, a downstream agent value proof, or a promotion or default change.
C4.1 produces one evaluator (`eval/c4_external_benchmark_adapters.py`) and
one canonical aggregate-only public artifact
(`artifacts/c4_external_benchmark_adapters/c4_external_benchmark_adapter_report.json`)
that records adapter/schema readiness only. C4.2 adds a bounded real
row-mapping smoke for the ContextBench verified subset and emits a separate
aggregate-only artifact
(`artifacts/c4_external_benchmark_adapters/c4_contextbench_verified_row_mapping_report.json`).
Row-level benchmark contents were not persisted in either phase.

> **Important claim boundary.** C4.1 emits `claim_level =
> adapter_schema_readiness_only`. It does NOT claim performance, promotion,
> default change, external benchmark result, downstream agent value, OOD
> temporal support, or QuIVer systems support. All no-claim flags are false:
> `promotion_ready=false`, `default_should_change=false`,
> `evidencecore_semantics_changed=false`,
> `runtime_clean_general_algorithm_claimed=false`,
> `downstream_agent_value_proven=false`, `ood_temporal_supported=false`,
> `quiver_systems_supported=false`. Synthetic self-test rows confer NO empirical
> support.

## Objective

Provide a real (non-skeleton) adapter/schema readiness layer for two external
benchmarks so future benchmark-driven evaluation can be wired in without
weakening the public-artifact contract:

- **ContextBench** — HuggingFace dataset `Contextbench/ContextBench`.
- **SWE-Explore** — HuggingFace dataset `SWE-Explore-Bench/SWE-Explore-Bench`.

The evaluator implements: (1) built-in known source/schema metadata for each
benchmark, (2) synthetic in-memory row adapters that separate
`public_task` (aggregate-safe metadata) from `private_label` (row-level
payload that is never serialized), (3) line range normalization for
synthetic self-test / private in-memory validation, (4) a strict fail-closed
forbidden-output scanner for all public JSON outputs, (5) a bounded HF
datasets-server schema smoke via stdlib `urllib` only (no new dependencies),
and (6) a deterministic spec hash that excludes timestamps, network output,
raw rows, and local paths.

## Implementation

### Evaluator

`eval/c4_external_benchmark_adapters.py` exposes an argparse CLI:

- `--self-test` — no-network synthetic self-test (9 assertion groups).
- `--benchmark {contextbench,swe_explore,all}` — default `all`.
- `--schema-smoke` — bounded HF datasets-server schema smoke; requires an
  explicit `--out` so the canonical aggregate report is never overwritten.
- `--limit` — max `(config, split)` pairs to probe with `/first-rows`;
  default 3, hard cap 10.
- `--out` — default
  `artifacts/c4_external_benchmark_adapters/c4_external_benchmark_adapter_report.json`.

Running without `--self-test` and without `--schema-smoke` generates the
canonical aggregate report from built-in known source/schema metadata plus
synthetic self-test status, with no network calls.

### Canonical artifact

`artifacts/c4_external_benchmark_adapters/c4_external_benchmark_adapter_report.json`
(schema `c4_external_benchmark_adapters.v1`) is the canonical aggregate-only
public artifact. It records `schema_version`, `generated_by`, `claim_level`,
all no-claim flags false, `aggregate_only_public_artifact=true`,
`not_evidence=true`, `candidate_not_fact=true`, a deterministic `spec_hash`,
`benchmarks.contextbench` and `benchmarks.swe_explore` blocks, `safety_invariants`
(all false), `framing`, and `forbidden_scan.status == pass`. JSON writing uses
`mkdir parents` + `json.dumps(..., indent=2, sort_keys=True) + "\n"`.

### Benchmark specs (built-in known schema metadata)

**ContextBench** (`Contextbench/ContextBench`):

- Configs/splits known: `default/train` 1136, `contextbench_verified/train` 500.
- Schema-only field names (observations about schema, not row values):
  `instance_id`, `original_inst_id`, `repo`, `repo_url`, `language`,
  `base_commit`, `gold_context`, `patch`, `test_patch`, `problem_statement`,
  `f2p`, `p2p`, `source`.
- Private field categories detected: `repo`, `repo_url`, `base_commit`,
  `gold_context`, `patch`, `test_patch`, `problem_statement`, `f2p`, `p2p`.
- License status: `unknown_dataset_license`. Row-level redistribution
  disabled even though the code repo is Apache-2.0 (the HF dataset card/API
  does not declare a dataset-level license).

**SWE-Explore** (`SWE-Explore-Bench/SWE-Explore-Bench`):

- Config/split known: `default/train` 848.
- Schema-only field names: `instance_id`, `repo_path`, `repo_dir`,
  `ground_truth`, `read_step_info`, `meta`, `dataset`.
- Private field categories detected: `repo_path`, `repo_dir`, `ground_truth`,
  `ground_truth.patch`, `ground_truth.test_patch`,
  `ground_truth.modified_files`, `ground_truth.core_files`,
  `ground_truth.line_ranges`, `read_step_info`, `read_step_info.file_maps`,
  `read_step_info.line_ranges`.
- License status: `cc-by-nc-nd-4.0`. Row-level redistribution AND derived-label
  publication disabled even though the code repo is MIT (the HF dataset license
  is `cc-by-nc-nd-4.0`).

### Synthetic in-memory row adapters

`adapt_contextbench_row` and `adapt_swe_explore_row` separate each synthetic
row into a `public_task` object (aggregate-safe metadata: presence booleans,
field counts, categorical bucket only — never raw values) and a
`private_label` object (all row-level payload, retained only in memory for
self-test and private in-memory validation). The public task NEVER carries
row-level repo/commit/patch/test/problem/gold values. Neither is ever
serialized into a public artifact with row-level values; only aggregate
counts/booleans across many rows may flow into the public artifact.

### Line range normalization

`normalize_line_range` accepts list/tuple/dict/`"S-E"`/`"S:E"` forms and
rejects `start > end`, `start < 1`, non-integer values, and bool values. Line
range normalization is synthetic self-test / private in-memory validation
only; for real benchmark rows, any path/span/line range is private/local-only
and is never written to public artifacts, docs, or schema smoke outputs.

### Forbidden-output scanner

`_scan_forbidden` is a strict recursive scanner for public JSON outputs. It
forbids sensitive key names (e.g. `instance_id`, `repo`, `patch`,
`ground_truth`, `content_sha`, `prompt`, `response`, `snippet`,
`gold_spans`, `private_labels`, `api_key`, `base_url`) anywhere as dict keys,
and forbids URL/hex-digest/secret-like/path-like/multiline/long-string
values. Schema-only field-name lists are allowed under explicit containers
(`field_names_schema_only`, `private_field_categories_detected`) because they
are observations about schema, not row-level data. Known-safe provenance
value paths (`spec_hash`, `generated_by`, `dataset_id`, `schema_version`,
`claim_level`) are allowlisted for the hex_digest/path_like value checks only.
The scanner is fail-closed: if a public report would leak, generation and
self-test fail. The artifact records only `forbidden_scan: {status: "pass"}`
plus category/path counts — never leaked values.

### Deterministic spec hash

`compute_spec_hash` returns the SHA-256 of the canonical spec JSON. The spec
excludes timestamps, network output, raw rows, and local paths; it includes
only dataset_id, configs, schema field names, private categories, license
gating, and field type summary. The hash is stable across runs:
`9de6609359aa8de4cfe7ca50b1388ebc51d9ee2f016bb3bc6c34e253da5ef153`.

## Data boundary

Public artifacts and docs remain aggregate/schema-only. The following were
NOT persisted in any public artifact or doc:

- raw benchmark rows and gold labels;
- row-level task instance values, instance IDs, original_inst_id;
- repo URLs, commits, repo paths, repo dirs;
- file paths, spans, line ranges, snippets;
- issue/problem statements, patches/tests, prompts/responses;
- provider payloads, content_sha, raw HF payloads, response bodies.

For each benchmark, the public artifact records only: dataset_id, config/split
row counts, schema-only field-name lists, field type summary, private field
categories detected (as dotted schema-only category names, not values),
license gating fields (`row_level_redistribution_allowed`,
`derived_label_publication_allowed`), and the four statuses
(`discovery_status`, `schema_smoke_status`, `adapter_self_test_status`,
`public_release_status`).

## Schema smoke results

The bounded HF datasets-server schema smoke uses stdlib `urllib` only (no new
dependencies), with an explicit bounded timeout, and uses `/splits` as the
source of truth for `/first-rows` attempts. For `/first-rows`, only
features/schema and row count/truncation booleans are parsed; raw rows remain
local only and are never returned or written. On network/HF failure, the
smoke produces status `unavailable` or `partial` with a sanitized reason
category/status code — no raw response body is stored.

Real schema smoke commands were run and passed the forbidden scan:

```text
python3 eval/c4_external_benchmark_adapters.py \
  --benchmark contextbench --schema-smoke --limit 3 \
  --out /tmp/c4_contextbench_schema.json
  => forbidden_scan: pass, new_network_calls: 4
  => first_rows_status: pass, row_level_data_returned: false

python3 eval/c4_external_benchmark_adapters.py \
  --benchmark swe_explore --schema-smoke --limit 3 \
  --out /tmp/c4_swe_explore_schema.json
  => forbidden_scan: pass, new_network_calls: 3
  => first_rows_status: pass, row_level_data_returned: false
```

The `/tmp` smoke outputs follow the same aggregate-only boundary as the
committed artifact. A network schema smoke failure would be acceptable as
long as a sanitized `partial`/`unavailable` output is produced and the
self-test passes; in this run the smoke endpoints were reachable and returned
schema parseable from public HF datasets-server metadata.

## Validation

```text
python3 -m py_compile eval/c4_external_benchmark_adapters.py   => PASS
python3 eval/c4_external_benchmark_adapters.py --self-test     => PASS (15 groups)
python3 eval/c4_external_benchmark_adapters.py \
  --out artifacts/c4_external_benchmark_adapters/\
c4_external_benchmark_adapter_report.json                     => PASS (forbidden_scan: pass)
python3 eval/c4_external_benchmark_adapters.py \
  --benchmark contextbench --schema-smoke --limit 3 \
  --out /tmp/c4_contextbench_schema.json                       => PASS
python3 eval/c4_external_benchmark_adapters.py \
  --benchmark swe_explore --schema-smoke --limit 3 \
  --out /tmp/c4_swe_explore_schema.json                        => PASS
python3 eval/c4_external_benchmark_adapters.py \
  --row-map-smoke --benchmark contextbench \
  --config contextbench_verified --split train --row-limit 10 \
  --out artifacts/c4_external_benchmark_adapters/\
c4_contextbench_verified_row_mapping_report.json              => PASS
  (rows_seen: 10, rows_mapped: 10, rows_failed: 0, status: pass,
   forbidden_scan: pass, private_label_isolation_verified: true)
python3 eval/c4_external_benchmark_adapters.py \
  --row-map-smoke --benchmark swe_explore \
  --config default --split train --row-limit 10 \
  --out artifacts/c4_external_benchmark_adapters/\
c4_swe_explore_row_mapping_report.json                       => PASS
  (rows_seen: 10, rows_mapped: 10, rows_failed: 0, status: pass,
   forbidden_scan: pass, private_label_isolation_verified: true,
   adapter_assertions_passed: true)
```

Self-test groups (15): ContextBench adapter separation, SWE-Explore adapter
separation, line range normalization, forbidden scan rejects injection,
no-claim flags exactly false, spec hash deterministic, aggregate-only report,
forbidden scan blocks leak at generation, schema smoke report shape, row-map
smoke aggregate-only (sentinel-clean), row-map smoke no-rows unavailable,
row-map smoke isolation failure fail-closed, swe row-map smoke aggregate-only
(sentinel-clean), swe row-map line-budget only-counts, swe row-map isolation
failure fail-closed.

## C4.2 ContextBench verified subset row-mapping smoke

C4.2 adds a bounded **real row-mapping smoke** for the ContextBench verified
subset (`contextbench_verified/train`). It reads real HF datasets-server
`/first-rows` preview rows via `_http_get_json()` (stdlib `urllib` only), and
for each preview row calls the existing `adapt_contextbench_row(row)` adapter
in function scope. Real rows live ONLY in function scope / memory; they are
adapted and immediately discarded. The public artifact records ONLY
aggregate-only counts, booleans, and fixed failure categories — never raw
rows, sample rows, row values, row-level hashes, paths, spans, line ranges,
snippets, problem statements, patches/tests, prompts/responses, provider
payloads, content_sha, or raw HF payloads.

### CLI

- `--row-map-smoke` (mutually exclusive with `--self-test` and `--schema-smoke`).
- `--row-limit` default 10, hard cap 20.
- `--config` default `contextbench_verified`; only `contextbench_verified` is
  supported for row-map smoke.
- `--split` default `train`.
- `--out` defaults to
  `artifacts/c4_external_benchmark_adapters/c4_contextbench_verified_row_mapping_report.json`
  when not explicitly set (so the C4.1 canonical report is never overwritten).

### Aggregate-only output shape

The row-map smoke artifact (`c4_contextbench_verified_row_mapping.v1`,
`claim_level=adapter_row_mapping_readiness_only`) records:

- `mode: contextbench_verified_row_mapping_smoke`, `benchmark: contextbench`,
  `dataset_id`, `config`, `split`, `row_limit_requested`;
- `rows_seen`, `rows_mapped`, `rows_failed`, `truncated_rows_observed`;
- `field_presence_counts`: schema field names -> count of non-empty rows
  (field names are schema-only observations used as count bucket keys, never
  row values);
- `public_task_presence_counts`: `has_original_inst_id`, `has_f2p`,
  `has_p2p`, `has_repo_locator`, `has_private_label_payload` -> counts of True;
- `private_field_presence_counts`: private category names -> count of
  non-empty rows (category names are schema-only observations, never values);
- `failure_category_counts`: fixed categories only (`missing_required_field`,
  `wrong_type`, `mapping_error`, `private_field_leak`, `public_artifact_leak`,
  `unexpected_exception`, `no_rows_returned`, `endpoint_unavailable`);
- `private_label_isolation_verified`, `adapter_assertions_passed`,
  `raw_rows_persisted: false`, `row_level_values_emitted: false`,
  `row_level_hashes_emitted: false`, `raw_response_stored: false`;
- `status: pass|partial|unavailable|fail_forbidden_leak|fail_schema_contract`;
- all no-claim flags false, `aggregate_only_public_artifact=true`,
  `not_evidence=true`, `candidate_not_fact=true`,
  `forbidden_scan.status=pass`.

The forbidden scanner was extended with a `SCHEMA_KEY_CONTAINER_KEYS`
allowlist so that count-container dicts (`field_presence_counts`,
`public_task_presence_counts`, `private_field_presence_counts`,
`failure_category_counts`) may use schema-only field-name strings as count
bucket keys. The scanner still forbids row-level values, paths, spans,
hashes, URLs, and secrets anywhere in the public output. A fail-closed
forbidden scan runs before each write.

### Real row-map smoke result (2026-06-20)

```text
python3 eval/c4_external_benchmark_adapters.py \
  --row-map-smoke --benchmark contextbench \
  --config contextbench_verified --split train --row-limit 10 \
  --out artifacts/c4_external_benchmark_adapters/\
c4_contextbench_verified_row_mapping_report.json
  => rows_seen: 10, rows_mapped: 10, rows_failed: 0
  => status: pass, forbidden_scan: pass
  => private_label_isolation_verified: true
  => adapter_assertions_passed: true
  => raw_rows_persisted: false, row_level_values_emitted: false,
     row_level_hashes_emitted: false, raw_response_stored: false
```

All 13 schema field names were non-empty in all 10 rows; all 5 public-task
presence booleans were True in all 10 rows; all 12 private-field categories
were non-empty in all 10 rows. No row-level values, hashes, paths, spans,
snippets, problem statements, patches/tests, prompts/responses, provider
payloads, content_sha, or raw HF payloads were persisted.

## C4.3 SWE-Explore row-mapping / line-budget aggregate smoke

C4.3 adds a bounded **real row-mapping / line-budget shape readiness smoke**
for SWE-Explore (`default/train`). It reads real HF datasets-server
`/first-rows` preview rows via `_http_get_json()` (stdlib `urllib` only), and
for each preview row calls the existing `adapt_swe_explore_row(row)` adapter
in function scope. Real rows live ONLY in function scope / memory; they are
adapted and immediately discarded. The public artifact records ONLY
aggregate-only counts, booleans, fixed failure categories, and line-budget
shape readiness counts/booleans — never raw rows, sample rows, row values,
row-level hashes, file paths/basenames, line ranges/spans/regions, patch/
test_patch/code snippets, modified/core file names, meta raw content,
labels/derived labels, provider payloads, content_sha, or raw HF payloads.

### CLI

- `--row-map-smoke --benchmark swe_explore` (mutually exclusive with
  `--self-test` and `--schema-smoke`; `--benchmark all` is rejected for
  row-map smoke).
- `--row-limit` default 10, hard cap 20.
- `--config` default `default` for `--benchmark swe_explore` (only `default`
  is supported); `--config` default `contextbench_verified` for
  `--benchmark contextbench`.
- `--split` default `train`.
- `--out` defaults to
  `artifacts/c4_external_benchmark_adapters/c4_swe_explore_row_mapping_report.json`
  for SWE-Explore (and to the C4.2 path for ContextBench), so the C4.1
  canonical schema artifact is never overwritten.

### Aggregate-only output shape

The SWE row-map smoke artifact (`c4_swe_explore_row_mapping.v1`,
`claim_level=adapter_row_mapping_readiness_only`) records:

- `mode: swe_explore_row_mapping_line_budget_smoke`,
  `benchmark: swe_explore`, `dataset_id`, `config`, `split`,
  `row_limit_requested`;
- `rows_seen`, `rows_mapped`, `rows_failed`, `truncated_rows_observed`;
- `field_names_schema_only`, `field_presence_counts` for SWE schema field
  names only (field names are schema-only observations used as count bucket
  keys, never row values);
- `public_task_presence_counts`: `has_repo_path`, `has_repo_dir`,
  `has_ground_truth`, `has_read_step_info`, `has_meta` -> counts of True;
- `private_field_presence_counts`: private category names -> count of
  non-empty rows, including nested `ground_truth_patch`,
  `ground_truth_test_patch`, `ground_truth_modified_files`,
  `ground_truth_core_files`, `ground_truth_line_ranges`,
  `read_step_info_file_maps`, `read_step_info_line_ranges` (category names
  are schema-only observations, never values);
- `line_budget_readiness`: aggregate counts/booleans only —
  `line_level_labels_present_count`, `region_like_structures_present_count`,
  `file_level_labels_present_count`, `rows_with_file_maps`,
  `rows_with_modified_files`, `rows_with_core_files`,
  `budget_evaluation_shape_supported`, `line_budget_values_emitted: false`,
  `paths_or_ranges_emitted: false` (never path or range strings);
- fixed `failure_category_counts` including `line_budget_shape_error` plus
  the existing categories (`missing_required_field`, `wrong_type`,
  `mapping_error`, `private_field_leak`, `public_artifact_leak`,
  `unexpected_exception`, `no_rows_returned`, `endpoint_unavailable`);
- `private_label_isolation_verified`, `adapter_assertions_passed`,
  `raw_rows_persisted: false`, `row_level_values_emitted: false`,
  `row_level_hashes_emitted: false`, `raw_response_stored: false`,
  `derived_labels_published: false`;
- license gating: `license_status: cc-by-nc-nd-4.0`,
  `row_level_redistribution_allowed: false`,
  `derived_label_publication_allowed: false`,
  `public_release_status: blocked_by_license`;
- all no-claim flags false, `aggregate_only_public_artifact=true`,
  `not_evidence=true`, `candidate_not_fact=true`,
  `forbidden_scan.status=pass`;
- `status: pass|partial|unavailable|fail_forbidden_leak|fail_schema_contract`.

The forbidden scanner was extended with `line_budget_readiness` in the
`SCHEMA_KEY_CONTAINER_KEYS` allowlist so that its count keys (which are
fixed readiness labels, not field names or paths) are accepted. The scanner
still forbids row-level values, paths, spans, hashes, URLs, and secrets
anywhere in the public output. A fail-closed forbidden scan runs before each
write. Injected `"12-34"` line-range strings and path-like values still fail
the scanner.

### Real row-map smoke result (2026-06-20)

```text
python3 eval/c4_external_benchmark_adapters.py \
  --row-map-smoke --benchmark swe_explore \
  --config default --split train --row-limit 10 \
  --out artifacts/c4_external_benchmark_adapters/\
c4_swe_explore_row_mapping_report.json
  => rows_seen: 10, rows_mapped: 10, rows_failed: 0
  => status: pass, forbidden_scan: pass
  => private_label_isolation_verified: true
  => adapter_assertions_passed: true
  => raw_rows_persisted: false, row_level_values_emitted: false,
     row_level_hashes_emitted: false, raw_response_stored: false,
     derived_labels_published: false
```

All 7 SWE schema field names were non-empty in all 10 rows; all 5 public-task
presence booleans were True in all 10 rows. The nested private categories
(`ground_truth_patch`, `ground_truth_modified_files`, etc.) were observed as
absent in the real HF `default/train` preview rows — this is an accurate
schema observation, not an error. The artifact therefore records
`budget_evaluation_shape_supported=false`: C4.3 is a row-mapping/privacy
boundary smoke plus a negative line-budget shape observation, not positive
line-budget readiness evidence. No row-level values, hashes, file paths, line
ranges, spans, snippets, patches/tests, meta raw content, labels, provider
payloads, content_sha, or raw HF payloads were persisted.

## C4.4 CORE-Bench source readiness / no-go

C4.4 is a **source-readiness no-go** phase for CORE-Bench (arXiv:2606.11864v1 —
"CORE-Bench: A Comprehensive Benchmark for Code Retrieval in the Era of
Agentic Coding"). It is NOT an adapter or schema-readiness module: the actual
HF dataset files/schema are unavailable, so C4.4 only emits a
**source-readiness no-go** report. No adapter support or schema readiness is
claimed.

### Wrong-target disambiguation

The target is the agentic-coding CORE-Bench (HF placeholder
`zhangfw123/CORE-Bench`), NOT the older `siegelz/core-bench` scientific
reproduction benchmark. The artifact records `wrong_target_disambiguated=true`
and `not_siegelz_core_bench=true`.

### Confirmed external findings

- Paper arXiv/HTML confirmed (arXiv:2606.11864v1).
- HF dataset repo `zhangfw123/CORE-Bench` is public, non-gated, MIT-tagged
  (from README frontmatter `license: mit`).
- HF repo currently contains only `.gitattributes` and `README.md`
  (`sibling_count=2`); no actual dataset files are published.
- datasets-server preview/viewer/search/filter/statistics are unavailable;
  `/is-valid` returns false; `/splits` unavailable; `/first-rows` unavailable.
- No official GitHub/project page confirmed.
- Paper aggregate facts (from arXiv Table 1, paper-level not row-level): 3
  levels (code understanding 172,961 queries; issue-to-edit localization
  5,061 queries / 632 repos / 52,712 qrels; broader context retrieval 2,580
  queries / 97 repos / 106,479 qrels); total 180,602 queries; 106,479
  broader-context labels.

### Artifact

`artifacts/c4_external_benchmark_adapters/c4_core_bench_source_readiness_report.json`
(schema `c4_core_bench_source_readiness.v1`,
`claim_level=source_readiness_no_go_only`). The status is
`blocked_dataset_placeholder_empty` (not `pass`/`support`).
`source_confirmation_status=paper_and_placeholder_confirmed_dataset_unavailable`.
`adapter_support_claimed=false`, `schema_readiness_claimed=false`,
`schema_smoke_attempted=true`, `schema_smoke_passed=false`,
`row_map_smoke_attempted=false`, `row_level_redistribution_allowed=false`,
`derived_label_publication_allowed=false`. All no-claim flags false;
`aggregate_only_public_artifact=true`, `not_evidence=true`,
`candidate_not_fact=true`, `forbidden_scan.status=pass`.

### Source probes

The script `eval/c4_core_bench_source_readiness.py` runs bounded network
probes via stdlib `urllib` only (timeout 10s, no new dependencies):
HF dataset API, HF tree API, datasets-server `/is-valid`, `/splits`,
`/first-rows`. No raw response bodies are stored; only aggregate metadata
and status categories are parsed. In `--offline` mode, no network calls are
made and the report is built from confirmed static findings only.

### Follow-up requirements

To unblock CORE-Bench adapter/schema readiness, the following would be
needed: actual dataset files published, schema and splits exposed,
qrels/corpus/query files published, license and redistribution statement,
official GitHub or project page confirmation.

## C4.5 RepoQA source/schema-contract readiness (adapter deferred)

C4.5 is a **source/schema-contract readiness with adapter deferred**
phase for the EvalPlus **RepoQA** benchmark (task: **Searching Needle
Function / SNF**; arXiv:2406.06025; OpenReview
`hK9YSrFuGf`). It is **not** an adapter module, **not** a
schema-readiness module, **not** a public-row-schema readiness module,
and **not** a benchmark-result module. The official schema contract is
known from source/docs/loader, but full adapter/row-map benchmark support
is **deferred** pending a conscious derived-qrels/version/license
decision. No RepoQA entry is added to
`eval/c4_external_benchmark_adapters.py`.

### Wrong-target disambiguation

The canonical target is EvalPlus RepoQA/SNF, NOT `Nutanix/RepoQA-neo4j`,
`microsoft/SCBench:scbench_repoqa`, `CodeRepoQA`, `SWE-QA-Bench`,
`CoReQA`, `RepoExec`, `RepoBench`, or `SWE-QA-Pro`. The artifact records
`wrong_target_disambiguated=true` and a list of excluded targets with
reasons.

### Confirmed external findings

- Paper: arXiv:2406.06025, OpenReview `hK9YSrFuGf`.
- Homepage/leaderboard: `https://evalplus.github.io/repoqa.html`.
- Code repo: `https://github.com/evalplus/repoqa` (Apache-2.0).
- Dataset release repo: `https://github.com/evalplus/repoqa_release`
  (Apache-2.0).
- Current loader default release: tag `2024-06-23`, asset
  `repoqa-2024-06-23.json.gz` (a monolithic `.json.gz`; NOT downloaded
  or decompressed).
- Paper-compatible release: tag `2024-04-20`, asset
  `repoqa-2024-04-20.json.gz`.
- Paper aggregate facts (paper-level, not row-level): 5 languages x 10
  repos x 10 needles = 500 code-search tasks over 50 repositories.
- Version skew: paper describes 5 languages; current loader default
  (`2024-06-23`) adds Go support (6 languages).
- Official schema contract: top-level shape is language -> repo records.
  Repo record fields: `repo`, `commit_sha`, `entrypoint_path`, `topic`,
  `content`, `dependency`, `needles`. Needle fields: `path`, `name`,
  `start_byte`, `end_byte`, `start_line`, `end_line`, `description`.
  SNF task/model-output fields are adapter-derived and row-level/private
  in real data.
- No official HF dataset/Data Viewer/qrels/corpus/query split was
  confirmed. The dataset is a monolithic source-containing JSON.gz.

### Artifact

`artifacts/c4_external_benchmark_adapters/c4_repoqa_source_readiness_report.json`
(schema `c4_repoqa_source_readiness.v1`, `claim_level =
source_schema_contract_readiness_adapter_deferred_only`). The status is
`source_confirmed_schema_contract_ready_adapter_deferred` (not
`pass`/`support`).
`adapter_support_claimed=false`, `schema_readiness_claimed=false`,
`public_row_schema_readiness_claimed=false`,
`schema_contract_readiness_claimed=true`,
`row_map_smoke_attempted=false`, `row_map_smoke_passed=false`,
`benchmark_result_claimed=false`.
`release_asset_downloaded=false`, `release_asset_decompressed=false`,
`release_asset_body_read=false`, `monolithic_json_rows_read=false`,
`row_level_redistribution_allowed=false`,
`derived_label_publication_allowed=false`. All no-claim flags false;
`aggregate_only_public_artifact=true`, `not_evidence=true`,
`candidate_not_fact=true`, `forbidden_scan.status=pass`.

### Source probes

The script `eval/c4_repoqa_source_readiness.py` runs bounded network
probes via stdlib `urllib` only (timeout 10s, no new dependencies):
GitHub code repo API, GitHub release repo API, GitHub release API (tag
`2024-06-23`) for asset metadata (name/size/content_type only; asset body
NOT downloaded or decompressed), and HEAD/GET status probes for arXiv
abs, homepage, and OpenReview URLs. No raw response bodies are stored;
only aggregate metadata and status categories are parsed. In `--offline`
mode, no network calls are made and the report is built from confirmed
static findings only.

### Schema contract field-name categories

Schema contract field names (`repo`, `content`, `needles`, `path`,
`start_line`, `description`, etc.) are recorded ONLY under explicit
schema-contract containers (`repo_record_contract_fields`,
`needle_contract_fields`, `task_record_contract_fields`,
`model_output_contract_fields`,
`adapter_derived_private_field_categories`,
`schema_contract_field_names`). They are observations about the schema
contract, not row-level data. The forbidden scanner allows them here but
rejects them as row-like dict keys/values elsewhere.

### Follow-up requirements

To unblock RepoQA adapter/row-map readiness, the following would be
needed: derived-qrels design decision, version selection decision,
license and redistribution statement, row-map smoke design, adapter
integration decision.

### Validation

```text
python3 -m py_compile eval/c4_repoqa_source_readiness.py   => PASS
python3 eval/c4_repoqa_source_readiness.py --self-test     => PASS (9 groups)
python3 eval/c4_repoqa_source_readiness.py --offline \
  --out /tmp/c4_repoqa_offline.json                         => PASS
  (status: source_confirmed_schema_contract_ready_adapter_deferred,
   source_confirmation_status: offline_static_findings_only,
   forbidden_scan: pass, new_network_calls: 0)
python3 eval/c4_repoqa_source_readiness.py \
  --out artifacts/c4_external_benchmark_adapters/\
c4_repoqa_source_readiness_report.json                     => PASS
  (status: source_confirmed_schema_contract_ready_adapter_deferred,
   source_confirmation_status: sources_confirmed_via_probe,
   forbidden_scan: pass, new_network_calls: 6)
```

Self-test groups (9): wrong-target disambiguation, offline report shape,
schema-contract allowlist vs row-key leak, schema container strict
pass/fail (approved strings pass; unapproved function/path values, dict
row-like objects, and forbidden dict keys inside schema containers all
fail), leak injection rejections (repo/function names, path, commit SHA,
line/byte range, description/question/answer, snippet, raw JSON fragment,
content hash/provider payload), release metadata allowed but content
sample/digest forbidden, source URLs allowed, report aggregate-only,
fail-closed generation.

## Caveats

- C4.1/C4.2/C4.3 is adapter/row-mapping readiness only. It does NOT validate
  row-level semantics, labels, or downstream agent value. The schema smoke
  confirms that public HF datasets-server schema endpoints are reachable and
  parse; the row-map smoke confirms that the adapter boundary holds (public
  task has no private attrs; private label has private values only in
  memory). Neither confirms benchmark quality, label correctness, or fitness
  for any downstream evaluation. No performance claim is made.
- C4.4 is source-readiness no-go only. It does NOT claim adapter support or
  schema readiness. The CORE-Bench HF dataset is currently a placeholder
  (only `.gitattributes` + `README.md`); actual dataset files/schema are
  unavailable. Row-level redistribution and derived-label publication remain
  disabled until actual dataset contents and terms are published.
- C4.5 is source/schema-contract readiness with adapter deferred. It does
  NOT claim adapter support, schema readiness, public row schema readiness,
  row-map smoke pass, or benchmark result. The official schema contract is
  known from source/docs/loader, but the monolithic JSON.gz is NOT downloaded
  or decompressed; no row-level data is read or persisted. Row-level
  redistribution and derived-label publication remain disabled pending a
  conscious derived-qrels/version/license decision.
- ContextBench dataset license is unknown even though the code repo is
  Apache-2.0; row-level redistribution is disabled.
- SWE-Explore HF dataset license is `cc-by-nc-nd-4.0`; row-level
  redistribution AND derived-label publication are disabled.
- Synthetic self-test rows confer NO empirical support.
- `spec_hash` is deterministic and excludes timestamps/network/raw
  rows/local paths; it is NOT a content_sha and is not row-level evidence.
- Row-level hashes are row-level derived data and are never emitted.

## Next steps

- Future external benchmark evaluation (separate from C4.1/C4.2/C4.3/C4.4/C4.5) would
  require an explicit, evidence-gated preregistration that respects each
  benchmark's license gating and the OpenLocus public-artifact contract.
- C4.4 follow-up: await publication of actual CORE-Bench dataset files,
  schema, and splits before any adapter/schema readiness can be considered.
- C4.5 follow-up: RepoQA adapter/row-map readiness is deferred pending a
  conscious derived-qrels/version/license decision. The monolithic JSON.gz
  is NOT downloaded or decompressed; no row-level data is read or persisted.
- No promotion, no default change, no EvidenceCore semantics change, no
  runtime-clean general algorithm claim, no downstream agent value claim, no
  OOD temporal claim, and no QuIVer systems claim follows from C4.1/C4.2/C4.3/C4.4/C4.5.
