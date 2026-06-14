# Real Provider P3 Research Log

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

# Real Provider P3 Research Log

## Scope

P3 ran QuIVer BQ readiness diagnostics with real embeddings from the local SiliconFlow configuration.

- Provider protocol: `openai-compatible`
- View: `path_plus_symbol` only
- Records: `4`
- Queries: `3`
- Remote calls: `7`
- QuIVer graph: not implemented
- Mode: BQ diagnostics only

## Results

- provider_status: `ok`
- BQ_overlap@10/50/100: `1.0 / 1.0 / 1.0`
- BQ_vs_f32_MRR: `0.6667`
- sign_entropy_mean: `0.3719`
- effective_dimension_proxy: `1445.95`
- query_corpus_centroid_angle: `0.2480`
- quiver_fit: `mixed`
- recommendation: `continue_diagnostics_then_proto`

## Interpretation

The tiny self-test suggests the real embedding distribution is not obviously incompatible with BQ diagnostics, but the sample is too small for a quality claim. The result supports continuing into diagnostic-only BQ top-k + f32 rerank, but not implementing/promoting a global QuIVer backend.

## Safety

- No provider URL/key committed.
- `.env.local` remains gitignored.
- No QuIVer graph quality number was emitted.
- `promotion_ready=false` and `default_should_change=false`.

## Next Step

P4 should run R34-R36 diagnostic-only BQ top-k and anchor-seeded variants with this same remote-safe view, then compare added_gold vs added_false and semantic trap behavior.

