# P21-G: Cross-Model Context Injection Research

P21-G is the next research direction after P20-LS-A. It changes the model-retrieval question from a single-model context-length sweep to a cross-model study of **context injection effects**.

The wrong question is:

```text
Which token budget is best: 4k, 8k, 32k, or 64k?
```

The better OpenLocus question is:

```text
Across model families, query buckets, repo types, and candidate-pool quality,
which context atoms consistently add gold evidence without adding false primary,
false spans, latency, or cost?
```

P20-LS-A showed that low-context, query-only LLM aliases fail: they generate plausible but ungrounded identifiers and add far more false spans than gold spans. That does not prove LLMs or embeddings are weak for code retrieval. It proves that starving models of repo context creates a weak experiment.

P21-G therefore studies **Context Intervention Generalization**: what happens when path, symbol, signature, matched lines, body windows, retrieval scores, source/test flags, hard distractors, neighbors, and related tests are injected into the candidate pack?

## Research Posture

P21-G prioritizes quality and efficiency. On public corpora or explicitly opted-in remote runs, richer code context is acceptable and should be measured directly.

The necessary boundaries remain narrow:

- exclude secrets and ignored files;
- do not send provider keys or private labels/gold answers;
- do not let model output become Evidence directly;
- do not use LLMs as promotion judges;
- final Evidence still comes from current-source read plus `content_sha` and line-range validation.

Everything else is a quality/cost/latency trade-off to measure, not something to forbid upfront.

## P21-G0: Freeze + Autopsy

Freeze the reference suites and prior negative evidence before running new model budget:

- L2 large-repo slice suite;
- R29/R26 stress matrix;
- P20-LS-A low-context alias result.

Autopsy buckets:

```text
file_wrong_rate
file_right_span_wrong_rate
candidate_pool_miss_rate
under_context_error_rate
source_test_confusion_rate
docs_source_confusion_rate
frontend_backend_confusion_rate
same_name_symbol_confusion_rate
fabricated_identifier_rate
```

Reason: if failures are mostly `file_wrong`, richer span snippets will not fix the candidate generator. If failures are mostly `file_right_span_wrong`, span-narrow and body-window context are worth testing.

## P21-G1: Context Atom Screening

Context atoms are the primary experimental units:

| Atom | Meaning |
|---|---|
| A0 | path |
| A1 | language / file kind |
| A2 | source/test/doc/generated flag |
| A3 | symbol name |
| A4 | symbol kind |
| A5 | signature |
| A6 | docstring / comment header |
| A7 | matched lines |
| A8 | local lexical tokens |
| A9 | BM25 / RRF / regex / symbol scores |
| A10 | channel provenance |
| A11 | body window around matched lines |
| A12 | full AST node / function body |
| A13 | imports summary |
| A14 | neighbor symbols |
| A15 | caller/callee/import neighbor snippets |
| A16 | related tests |
| A17 | config/route/schema context |
| A18 | hard distractor candidates |
| A19 | abstain/no-answer hints |
| A20 | candidate uncertainty features |

Estimate the treatment effect of an atom or atom group:

```text
Effect(atom) = metric(with atom) - metric(without atom)
```

Report:

```text
MATE(atom) = model-averaged treatment effect
per_model_effect(atom)
effect_variance_across_models(atom)
bucket_specific_effect(atom)
leave_one_model_out_stability(atom)
```

An atom is broadly useful if it has high positive MATE, low model variance, no PFP increase, and acceptable cost.

## P21-G2: Context Pack Ladder

Do not define strategies by fixed token length. Define them by context content, then record actual tokens.

```text
Pack0 bare:
  path + score

Pack1 metadata:
  path + language + file_kind + symbol + signature + score

Pack2 evidence_sketch:
  Pack1 + matched lines + lexical tokens + channel provenance

Pack3 local_code:
  Pack2 + body window / AST node

Pack4 relational:
  Pack3 + imports/neighbor symbols + related tests

Pack5 contrastive:
  Pack4 + hard distractors + source/test/doc flags

Pack6 repo_slice:
  module-level slice + candidate cluster + tests/config/schema context
```

For each pack, record actual input-token p50/p95 after the pack is naturally built. Token ranges are for after-the-fact analysis, not the main experimental axis.

## P21-G3: Role Matrix

Measure model roles separately. Do not call all of this “LLM retrieval.”

| Role | Input | Output | Question |
|---|---|---|---|
| `rerank` | query + top-k candidates + context atoms | ranked candidate IDs | Which atoms stabilize ranking? |
| `filter` | query + candidates | primary/supporting/weak/reject | Which atoms lower false primary? |
| `span_narrow` | query + snippet/function/file | suggested line range | Which atoms improve SpanF0.5? |
| `inventory_alias` | query + real repo inventory + candidate metadata | aliases selected from inventory | Can grounding reduce fabricated identifiers? |
| `abstain` | query + candidates + hard distractors | answerable/ambiguous/no reliable evidence | Can models reduce negative false primary? |

Model outputs remain suggestions/candidates only.

## P21-G4: Cross-Model Generalization

Do not build a leaderboard first. Build model profiles.

Model groups:

```text
small_fast
code
long_context
reasoning_strong
embedding
local
```

Validation:

```text
leave_one_model_out
leave_one_family_out
cross_cost_transfer
```

Output:

```text
stable_atoms
model_specific_atoms
harmful_atoms
model_family_interactions
```

## P21-G5: Adaptive Context Policy

Build a rule-based policy before any black-box router.

Input features:

```text
query_type
identifier_density
RRF score
RRF top1-top2 gap
regex/symbol agreement
candidate_entropy
source/test ambiguity
dense support score
hard_negative risk
model_profile
latency_budget
cost_budget
```

Output:

```text
which pack
which role
which model group
how many candidates
whether to abstain
```

Example rules:

```text
exact_symbol + unique symbol:
  Pack1, no LLM

natural_language_bug + high RRF entropy:
  Pack4 + rerank + span_narrow

hard_distractor risk:
  Pack5 + filter

file_right_span_wrong pattern:
  Pack3/4 + span_narrow

negative_nonexistent risk:
  Pack2 + abstain/filter, no long code body
```

## P21-G6: Long Context Layout Study

Only run layout tests for richer packs such as Pack4-6.

Layouts:

```text
metadata_first
code_first
score_first
diverse_first
high_score_first
hard_distractor_adjacent
query_repeated_per_candidate
candidate_table_then_code
code_then_candidate_table
positive_like_candidate_in_middle
```

Report:

```text
selected_candidate_position
middle_failure_rate
rerank_stability
SpanF0.5
PFP
latency
```

## P21-G7: Embedding Context Study

Embedding long input is not the same as LLM long context. Prefer multi-vector views over one giant vector.

Views:

```text
symbol_vector
signature_vector
body_vector
doc_vector
file_summary_vector
module_summary_vector
test_intent_vector
route_config_vector
```

Fusion:

```text
early_concat
late_fusion_max
late_fusion_weighted
RRF_dense_views
anchor_seeded_dense_views
```

Embedding model comparisons must run on the same tasks, corpus, caps, latency, and cost accounting. Earlier P9a already showed that the largest embedding model did not automatically dominate on the first slice.

## P21-G8: QuIVer / BQ Context Interaction

QuIVer context interaction is about embedding view distributions, not LLM prompt length.

Measure:

```text
BQ_overlap by view
BQ_overlap by model
BQ_overlap by language
BQ_overlap by pack
QuIVer proto by sharded view
QuIVer anchor-seeded by regex/symbol/RRF
```

Do not claim QuIVer ANN quality unless graph/Vamana backend exists.

## P21-G9: Generalization Report

The final report should not say:

```text
best context length = X
```

It should say:

```text
Stable across models:
  signature + matched lines + source/test flag + scores

Model-specific:
  long-context model benefits from relational pack
  small-fast model benefits only from metadata + matched lines

Harmful:
  query-only aliases
  global dense primary
  graph expansion as recall
  hard distractors omitted in ambiguous queries

Recommended adaptive policy:
  exact_symbol -> Pack1 no LLM
  NL bug -> Pack4 rerank+span-narrow
  hard_distractor -> Pack5 filter
  negative -> Pack2 abstain/filter
```

## Multi-Model Run Configuration

Configuration files:

- `eval/p21_model_profiles.json` — model profile registry for LLM and embedding model groups.
- `eval/p21_multimodel_plan.py` — emits reproducible `gh workflow run real-provider-benchmark.yml ...` commands for selected model profiles, repos, and caps.
- `.github/workflows/real-provider-benchmark.yml` — supports `embedding_model` and `llm_model` workflow inputs. `llm_model` overrides the repo variable for a single dispatch.

Default enabled LLM roster:

| Profile | Model | Family | Intended role |
|---|---|---|---|
| `deepseek_v4_flash_small_fast` | `[mk]DeepSeek-V4-Flash` | small/fast long-context | cheap first-pass filter, abstain, inventory alias, latency baseline |
| `kimi_k2_7_code` | `[mk]Kimi-K2.7-Code` | code | primary code rerank/filter/span-narrow model |
| `deepseek_v4_pro_long_context` | `[mk]DeepSeek-V4-Pro` | long-context/text-strong | Pack5/Pack6, hard distractors, long-layout tests |
| `glm_5_1_reasoning_code` | `[mk]GLM-5.1` | reasoning/code-strong | expensive review/ablation model, cross-family validation |

The autonomous policy is smoke first, then medium only for promising profiles:

```text
smoke: 20 tasks × py_flask/js_express/go_gin/rust_ripgrep × all enabled profiles
medium: 60 tasks × same repos × profiles/roles that pass smoke
max_workflow_runs_per_batch: 20
stop if added_false_span >= 3× added_gold_span, PFP increases, schema violation >5%, or repeated provider/rate-limit failures occur
```

Example dry-run plan for the default LLM roster. This creates 16 workflow runs: four LLM profiles across four repos, staying under the default batch cap of 20.

```bash
python3 eval/p21_multimodel_plan.py \
  --mode llm \
  --enable-remote-models \
  --repos py_flask,js_express,go_gin,rust_ripgrep \
  --max-tasks 20 \
  --max-records 80 \
  --max-files-per-repo 120 \
  --print-commands
```

Run embedding model sweeps separately (`--mode embedding`) so each batch also stays under 20 workflow runs. A combined `--mode both` over four repos currently creates 32 runs and will not execute unless explicitly allowed with `--allow-large-batch`.

To add provider-specific LLMs without committing private provider config:

```bash
python3 eval/p21_multimodel_plan.py \
  --mode llm \
  --enable-remote-models \
  --llm-model small_fast=my-small-fast-model \
  --llm-model long_ctx=my-long-context-model \
  --repos py_flask,js_express \
  --print-commands
```

To execute, intentionally set an extra guard:

```bash
P21_G_ALLOW_DISPATCH=1 python3 eval/p21_multimodel_plan.py --mode llm --execute ...
```

The plan script is only dispatch wiring. It establishes the repeatable multi-model run layer needed for P21-G0/G1. Rich-context candidate-pack harnesses should produce separate P21-G artifacts.

## Reporting Requirements

Every P21-G report should include quality, efficiency, and model-generalization fields:

- quality: FileRecall, MRR, SpanF0.5, added_gold/false, PFP, abstain;
- grounding: fabricated identifier rate, inventory hit rate, snippet citation validity;
- efficiency: provider calls, input/output tokens, latency p50/p95, cost estimate;
- model generalization: MATE, per-model effect, effect variance, leave-one-model-out stability;
- role boundary: promotion_ready=false unless a separate promotion process exists.

## Bottom Line

P21-G treats rich context as a core capability, but token count is not the main experimental variable. The right question is whether specific context atoms, packs, roles, layouts, and model profiles improve retrieval enough to justify their latency and cost while EvidenceCore remains the final authority.
