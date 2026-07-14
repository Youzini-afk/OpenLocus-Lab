# Product Stack Bakeoff — B1 Mechanics Screen Closeout

Date: 2026-07-14

Status: `b1_mechanics_screen_complete_aggregate_only_no_product_winner_claim`

The project owner authorized aggregate-only publication of the synthetic B1 mechanics result. The authorization is recorded in source checkpoint `0b6f2e13b1dbc679eb1f827c28a8abd5403dcd58`; it does not authorize private rows, task/query/path details, receipts, traces, resource samples, or any product winner/default/effectiveness claim.

## Result

The frozen B1 v2.4 screen passed:

- 504 total comparison records: 360 one-shot and 144 two-step;
- 504 accepted, 0 rejected;
- all six internal stacks passed;
- 2,256 of 2,256 parent-owned sentinels passed;
- all 504 records had complete trusted resource samples and same-execution scoreable captures;
- cold/warm semantic equality, three-repetition determinism, and all two-step lineages passed;
- provider/network call count was 0;
- the private canary remained private and was absent from the public aggregate.

The exact closed aggregate is published as [`product_bakeoff_b1_mechanics_screen_aggregate.json`](../../artifacts/product_bakeoff_b1/product_bakeoff_b1_mechanics_screen_aggregate.json).

## What this proves

B1 proves that the six cumulative internal stacks S0–S5 can execute the frozen synthetic mechanics contract end to end on the two synthetic fixtures. This includes production persistent BM25, exact literal lookup, exact-name AST symbol lookup, conditional depth-1 graph lookup, bounded target/support assembly, cold/warm state reuse, exact native-score competition ties (`1, 1, 3`), and graph channel weight 2 while the other channels use weight 1.

B1 does not rank the stacks, select a product default, establish retrieval quality, validate real repositories, compare external algorithms, or establish a production latency/memory envelope. Those are decisions for B2 and later phases.

## Reproducibility lock

- Source checkpoint: `0b6f2e13b1dbc679eb1f827c28a8abd5403dcd58`
- Spec: `product_bakeoff_b1.v2.4`
- Spec digest: `b1spec_6058c3e732d077f5`
- Fixture digest: `b1fix_b012d3da68d75522`
- Source bundle digest: `b1src_fa5b30ca188d08a491206e13acfe3faa9a5070a68be2222ba349392101b136d2`
- Runtime bundle digest: `b1run_01c1fdcfe6d77f3d1f8101f66a90191a1f4a620d43e39a139b686149e0b2a896`
- Independent preflight before the full screen: 168 records, 0 failures

The local execution surface is:

```text
python eval/product_bakeoff_b1_cli.py --self-test
python eval/product_bakeoff_b1_cli.py --fault-test
python eval/product_bakeoff_b1_cli.py --probe --runs-dir <ignored-local-directory>
python eval/product_bakeoff_b1_cli.py --full-screen --runs-dir <ignored-local-directory>
```

All row-level outputs remain under an ignored local directory. Only the validated closed aggregate above is public.

## Next phase

B1 is frozen and closed. The B2 48-task internal tournament protocol is now frozen in [`product-bakeoff-b2-internal-tournament-protocol.md`](./product-bakeoff-b2-internal-tournament-protocol.md). The next implementation step is the private repository/task admission layer and complete local B2 runner; no B2 empirical result exists yet.
