# Real Provider P2 Research Log

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# Real Provider P2 Research Log

## Scope

P2 ran a bounded real embedding view bakeoff using the SiliconFlow OpenAI-compatible embedding provider configured only in local `.env.local`.

- Provider protocol: `openai-compatible`
- Model class: Qwen/Qwen3 embedding family via local environment
- Committed provider URL/key: **none**
- View: `path_plus_symbol` only
- Data level: 0 / remote-safe metadata-symbol view
- Dataset: generated self-test repo only
- Role: candidate/supporting-only

## Results

The bounded self-test completed successfully:

- provider_status: `ok`
- records embedded: `4`
- remote_calls: `4`
- citation_validity: `1.0`
- EvidenceCore_rejection_rate: `0.0`
- promotion_ready: `false`
- default_should_change: `false`

Quality signal is intentionally treated as weak/non-promotional:

- FileRecall@1: `0.0`
- FileRecall@3: `0.6667`
- SpanF0.5: `0.1603`
- primary_false_positive_rate: `1.0`
- semantic_trap_hit_rate: `1.0`

This reinforces the admission rule: real dense hits must remain supporting-only unless anchored/guarded.

## R38 Attempt

An attempted R38 run against the current local `fixtures/r26_auto_stress/repos.lock.jsonl` timed out before producing an artifact. Root cause is harness scale mismatch: the R26 lock points at large local sibling repos and the R32 script builds views before applying enough repo/file caps. This is a harness-scaling issue, not a provider-quality result.

## Safety

- `.env.local` stayed gitignored.
- Reports contain no provider URL or API key.
- Only data-level-0 `path_plus_symbol` text was sent remotely.
- No raw code/config/test assertions were sent.
- RUN/SCORE split remains intact in the report.
- No promotion/default change.

## Next Step

P3 should use the same remote-safe `path_plus_symbol` view for QuIVer BQ readiness diagnostics. P4 should test diagnostic-only BQ top-k and anchor-seeded restrictions on the same tiny bounded corpus before any larger CI run.

