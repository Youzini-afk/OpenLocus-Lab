# Real Provider P4 Research Log

## Scope

P4 ran the R34-R36 diagnostic/anchor-seeded harness using the real embedding provider and the remote-safe `path_plus_symbol` view.

- Provider: `openai-compatible`
- View: `path_plus_symbol`
- QuIVer mode: `diagnostic_only`
- Graph/Vamana: not implemented
- Dataset: self-test repo only
- Query embedding cache: enabled to avoid repeated remote calls per strategy

## Results

Best net strategies were source/test split plus regex/symbol anchors:

- SpanF0.5: `0.5435`
- FileRecall@1: `0.6667`
- added_gold_span: `2`
- added_false_span: `0`
- semantic_trap_nonempty: `0`
- citation_validity: `1.0`

This supports the research hypothesis that global dense/QuIVer should not be used directly; anchored/source-test-restricted variants are safer.

## Safety

- `quiver_mode=diagnostic_only`
- `quiver_graph_implemented=false`
- `quiver_default_allowed=false`
- `promotion_ready=false`
- `default_should_change=false`
- No provider URL/key committed
- `.env.local` remains ignored

## Next Step

P5 should exercise the real LLM in a derived/stress-only mode, still avoiding source-code prompts and labels. P6 should then replay R39-R42 on the generated stress/small corpus.
