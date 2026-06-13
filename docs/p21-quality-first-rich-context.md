# P21-Q: Quality-First Rich Context Model Retrieval

P21-Q is the next research direction after P20-LS-A. It changes the model-retrieval question from “how much can we do with minimal context?” to “how much quality and speed do we gain when the model receives enough code facts to be useful?”

## Thesis

P20-LS-A showed that low-context, query-only LLM aliases fail: they generate plausible but ungrounded identifiers and add far more false spans than gold spans. That does not prove LLMs or embeddings are weak for code retrieval. It proves that starving models of repo context creates a weak experiment.

P21-Q therefore prioritizes quality and efficiency. On public corpora or explicitly opted-in remote runs, richer code context is acceptable and should be measured directly.

The necessary boundaries remain narrow:

- exclude secrets and ignored files;
- do not send provider keys or private labels/gold answers;
- do not let LLM output become Evidence directly;
- do not use LLMs as promotion judges;
- final Evidence still comes from current-source read plus `content_sha` and line-range validation.

Everything else is a quality/cost trade-off to measure, not something to forbid upfront.

## P21-Q0: Context Policy Update

Make the eval policy explicit:

```text
quality_first_remote_mode = true
allowed_remote_inputs = query + paths + symbols + signatures + candidate snippets + neighbor snippets + local retrieval scores
excluded_remote_inputs = secrets + ignored files + provider keys + private labels/gold answers
evidence_authority = EvidenceCore only
```

Reports should distinguish:

- low-context mode: path/symbol/query only;
- rich-context mode: actual code snippets and candidate metadata;
- raw-source bulk upload: still unnecessary for these experiments unless explicitly justified.

## P21-Q1: Rich Embedding View Bakeoff

The earlier embedding runs leaned heavily on conservative views such as `path_plus_symbol`. P21-Q should benchmark richer views:

| View | Contents | Purpose |
|---|---|---|
| `raw_chunk_256` | path header + 256-token code chunk | Low-cost raw-code semantic baseline |
| `raw_chunk_512` | path header + 512-token code chunk | Better semantic context |
| `raw_chunk_1024` | path header + 1024-token code chunk | Larger context / latency trade-off |
| `signature_plus_body_window` | symbol signature + nearby body lines | Span targeting around definitions |
| `snippet_with_neighbors` | candidate span + before/after lines | Reduce file-right/span-wrong failures |
| `test_source_pair` | test snippet + likely source snippet metadata | Study test/source confusion |
| `path_symbol_raw_hybrid` | path + symbol + raw snippet | Combine lexical anchors and semantics |

Metrics:

- FileRecall@1/5;
- SpanF0.5;
- primary_false_positive_rate;
- added_gold_span vs added_false_span;
- token waste;
- provider calls, latency p50/p95, input tokens, cost estimate.

## P21-Q2: Rich LLM Candidate Support

Do not ask the LLM to guess repository identifiers from a bare query. First run local retrieval, then give the LLM useful candidate context.

Input per task:

```json
{
  "query": "...",
  "repo_id": "...",
  "candidates": [
    {
      "candidate_id": "c17",
      "path": "...",
      "language": "...",
      "symbol": "...",
      "signature": "...",
      "snippet": "actual code excerpt",
      "neighbor_before": "...",
      "neighbor_after": "...",
      "retrieval_sources": ["bm25", "regex", "symbol", "rrf"],
      "scores": {"bm25": 12.3, "rrf": 0.08}
    }
  ]
}
```

Allowed LLM roles:

- rerank local candidates;
- reject likely false positives;
- narrow a candidate to a smaller line range;
- choose aliases from an existing symbol/path inventory;
- decompose ambiguous queries into sub-intents.

Still forbidden:

- direct Evidence;
- gold-label generation;
- citation verdicts;
- promotion verdicts;
- LLM-only primary admission.

## P21-Q3: Prompt and Context Matrix

Run multiple prompts and context budgets instead of treating one prompt as representative.

Prompt families:

1. `rich_context_rerank_v1` — rank candidates, abstain if all are weak.
2. `rich_context_false_positive_filter_v1` — reject docs/tests/generated/source-confusion traps.
3. `rich_context_span_narrow_v1` — return a narrower candidate line window.
4. `grounded_alias_inventory_v1` — select aliases only from provided symbol/path inventories.
5. `query_decompose_v1` — split vague query into concrete search intents.

Context budgets:

```text
top_k_candidates = 10 / 25 / 50
snippet_window = 20 / 60 / 120 lines
max_input_tokens = 4k / 16k / 64k
```

The goal is not only max quality, but quality per unit latency/cost.

## P21-Q4: Evaluation Plan

Start small but realistic:

```text
repos: py_flask, js_express, go_gin, rust_ripgrep
tasks: 20 then 60 per repo
baseline: regex, bm25, symbol, rrf, query_noise_plus_rrf_agree_min
rich embedding: raw_chunk_256/512, path_symbol_raw_hybrid
rich LLM: rerank/filter/span_narrow over top-k RRF candidates
```

Scale only if:

```text
added_gold_span > added_false_span
SpanF0.5 improves
PFP does not increase
latency/cost are explainable
fabricated_identifier_rate drops near zero for inventory-grounded modes
```

Stop or redesign if:

```text
quality improves only at file level but not span level
false spans dominate gold spans
LLM rejects true positives too aggressively
cost/latency is too high for the quality gain
```

## Reporting Requirements

Every P21-Q report should include both quality and efficiency:

- quality: FileRecall, MRR, SpanF0.5, added_gold/false, PFP, abstain;
- grounding: fabricated identifier rate, inventory hit rate, snippet citation validity;
- efficiency: provider calls, input/output tokens, latency p50/p95, cost estimate;
- role boundary: promotion_ready=false unless a separate promotion process exists.

## Bottom Line

P21-Q treats rich context as a core capability, not a leakage failure. The right question is whether richer code facts let models improve retrieval enough to justify their latency and cost while EvidenceCore remains the final authority.
