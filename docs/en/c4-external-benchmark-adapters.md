# C4 External Benchmark Adapters — Schema + Row-Mapping Readiness v1

Date: 2026-06-20 (C4.1 schema readiness); 2026-06-20 (C4.2 ContextBench
verified subset row-mapping smoke)

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
python3 eval/c4_external_benchmark_adapters.py --self-test     => PASS (12 groups)
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
```

Self-test groups (12): ContextBench adapter separation, SWE-Explore adapter
separation, line range normalization, forbidden scan rejects injection,
no-claim flags exactly false, spec hash deterministic, aggregate-only report,
forbidden scan blocks leak at generation, schema smoke report shape, row-map
smoke aggregate-only (sentinel-clean), row-map smoke no-rows unavailable.

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

## Caveats

- C4.1/C4.2 is adapter/row-mapping readiness only. It does NOT validate
  row-level semantics, labels, or downstream agent value. The schema smoke
  confirms that public HF datasets-server schema endpoints are reachable and
  parse; the row-map smoke confirms that the adapter boundary holds (public
  task has no private attrs; private label has private values only in
  memory). Neither confirms benchmark quality, label correctness, or fitness
  for any downstream evaluation.
- ContextBench dataset license is unknown even though the code repo is
  Apache-2.0; row-level redistribution is disabled.
- SWE-Explore HF dataset license is `cc-by-nc-nd-4.0`; row-level
  redistribution AND derived-label publication are disabled.
- Synthetic self-test rows confer NO empirical support.
- `spec_hash` is deterministic and excludes timestamps/network/raw
  rows/local paths; it is NOT a content_sha and is not row-level evidence.
- Row-level hashes are row-level derived data and are never emitted.

## Next steps

- Future external benchmark evaluation (separate from C4.1/C4.2) would
  require an explicit, evidence-gated preregistration that respects each
  benchmark's license gating and the OpenLocus public-artifact contract.
- No promotion, no default change, no EvidenceCore semantics change, no
  runtime-clean general algorithm claim, no downstream agent value claim, no
  OOD temporal claim, and no QuIVer systems claim follows from C4.1/C4.2.
