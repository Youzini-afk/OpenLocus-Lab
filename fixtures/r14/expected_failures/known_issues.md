# Known Expected Failures

## Negative Tasks

Tasks with `task_type: "negative"` are expected to return zero or low-quality results.
A method that returns confident hits on negative tasks is producing false positives.

- `r14s-037` (`quantum_entanglement_solver`): No relevant code exists in any indexed repo.
- `r14s-038` (`neural_network_training_loop`): No relevant code exists.
- `r14m-031` (`blockchain_consensus_protocol`): No relevant code exists.
- `r14m-032` (`distributed_database_replication`): No relevant code exists.
- `r14stress-007` (`machine_learning_inference`): No relevant code exists.
- `r14stress-008` (`web_server_http_handler`): No relevant code exists.

## Stress Tasks

Stress tasks have broad/vague queries where multiple files may be relevant.
Exact gold spans are approximate; metrics on stress tasks should be interpreted
cautiously and not used as primary quality indicators.

## Symbol Search Limitations

Symbol search with `--mode regex` uses heuristic patterns. It may miss:
- Re-exports (`pub use`)
- Macro-generated items
- Nested definitions
- Trait implementations

Symbol search with `--mode ast` uses Tree-sitter and may miss:
- Unsupported languages
- Parse errors (falls back to regex)
- Complex symbol patterns

## BM25 Chunking

Line-window chunking (default) may produce evidence spans that overlap with
gold spans but don't precisely match. This is expected and reflects the
fundamental chunking granularity limitation.

AST chunking (experimental) may produce smaller, more precise spans but
can regress FileRecall@5 due to chunk-score dilution (as shown in R9).
