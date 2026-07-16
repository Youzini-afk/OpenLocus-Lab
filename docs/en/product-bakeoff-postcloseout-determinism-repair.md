# Product Bakeoff Post-closeout Retrieval Determinism Repair

Date: 2026-07-17

Status: `product_bakeoff_postcloseout_determinism_repair_complete_no_b25_result_change`

This is an engineering and research-design repair after the terminal B2.5 closeout. It does not reopen B2.5, relax its frozen gate, score or rank its completed matrix, create a tournament result, reuse its launch authorization, or change the product default. The authoritative historical result remains [`product_bakeoff_b25_failed_closed_aggregate.json`](../../artifacts/product_bakeoff_b25/product_bakeoff_b25_failed_closed_aggregate.json).

The public repair aggregate is [`product_bakeoff_postcloseout_determinism_repair.json`](../../artifacts/product_bakeoff_determinism_repair/product_bakeoff_postcloseout_determinism_repair.json).

## Engineering findings

The audit found several ways that a capped retrieval result could inherit process-local or caller-provided order:

- Tantivy `TopDocs` breaks equal-score ties with document addresses. Both temporary and persistent BM25 previously collected a fixed oversample and capped before a stable path/range tie order could see the complete boundary tie.
- RRF accumulated exact cells in an unordered map and collapsed containing spans while mutating that map. A wider span covering several incomparable narrow spans could transfer its full vote to whichever child appeared first.
- The graph configuration-edge cap selected from a `HashSet`, so a large eligible set could produce a different bounded subset in another process.
- Capped literal, regex-symbol, AST-symbol, and context graph-seed paths could inherit input order.
- Historical B2/B2.4/B2.5 artifact validators rebound frozen source digests to the current checkout. After a legitimate post-closeout source repair, that behavior misreported expected source evolution as historical artifact drift.

## Engineering repair

BM25 now expands collection until the entire score tie at the oversample boundary is visible, materializes that set, deduplicates exact cells, sorts by native score then stable path/range/content keys, and only then applies the requested cap. The reusable persistent-index handle and the ordinary persistent search path share the same helper. Temporary BM25 applies the same rule independently because the retrieval and index crates do not share a Tantivy utility layer.

RRF now sorts channel inputs, accumulates exact cells in a `BTreeMap`, normalizes metadata, and computes containment transfers from an immutable key snapshot. A single descendant receives the full ancestor vote. Several incomparable minimal descendants split the ancestor vote evenly, conserving total RRF mass without inventing a leftmost or hash-order winner.

Graph records, nodes, edges, configuration candidates, and serialized edge-kind counts now have stable ordering. Literal, regex-symbol, AST-symbol, and context graph-seed caps use explicit path tie-breaks.

The terminal archive validator locks 15 public B2 through B2.5 artifacts by canonical JSON, verifies canonical self-digests where applicable, and checks public cross-phase bindings. It deliberately does not compare historical source bundles with current `HEAD`.

## Comparability-gate review

The historical exact semantic hash is broader than the frozen scorer in principle: candidate-native scores and order, duplicate span segmentation, excerpts, channels, explanations, and status-reason text can differ while every scorer input stays equivalent. Treating every such diagnostic difference as a score-invalidating event is unnecessarily strict.

The future-only policy in [`product_bakeoff_postcloseout_comparability.py`](../../eval/product_bakeoff_postcloseout_comparability.py) uses an oracle-blind scorer-equivalent projection:

- context observations retain the admission envelope, candidate-set emptiness, pack status, evidence-line union, target-line union, and support-set emptiness;
- support observations retain the admission envelope plus relation kind, parent target, support path, and support-line union;
- source currentness, scoreability, same-arm lineage, fairness, and provider isolation remain separate mandatory gates.

The same projection must be frozen in both the future pre-score repeatability gate and the future scorer's repeated-cell canonicalization. Changing only one side would leave a hidden second exact-hash rejection.

This design finding does not establish that the historical B2.5 failure was diagnostic-only. The frozen B2.5 decision is not retrospectively reclassified, and no B2.5 score or rank exists.

## Validation

The public repair digest is `detrepair_b05b51b37631baa5e7d744be511e3368e4e56bab4f37a0a3cfb8748b853cedeb`.

Repair checkpoint `85f284a5248d5b066e11405a2453c85f84fc1e6a` passed CI run `29537075918`:

- 297 relevant Rust tests on Linux and 297 on Windows;
- eight fresh-process iterations of six deterministic boundary regressions;
- `rustfmt` and clippy with warnings denied;
- terminal-archive self-test and fault injection;
- future comparability-policy self-test and fault injection;
- B2.5 closeout validation, public privacy audit, and bilingual-document validation.

## Remaining limit and next action

The repair has cross-platform bounded CI coverage, but production-scale synthetic Linux stress has not yet run. Before any future tournament design is authorized, run large equal-score BM25, repeated fresh-process retrieval, and resource-bound stress on Linux without private input. Then preregister the scorer-equivalent policy, qualify the exact future runtime, and author a fresh holdout. No B2.5 treatment output or launch authorization may be reused.
