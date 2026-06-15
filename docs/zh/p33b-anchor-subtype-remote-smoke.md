# p33b-anchor-subtype-remote-smoke（中文镜像）

中文译本待补充；以下保留英文原文，确保 docs/en 与 docs/zh 文件级 1:1 镜像。

## English source / 英文原文

# P33-B Anchor Subtype Calibration Remote Smoke

- Runs: 6 successful real-provider P21 rich-candidate runs
- Task observations: `108`
- Positive/no-gold observations: `36` / `72`
- promotion_ready: `false`
- default_should_change: `false`

## Main conclusion

P33-B confirms the P33 result at finer granularity: splitting `symbol_regex_union` into symbol-only, regex-only, fusion, agreement, and RRF-backed subtype buckets does not reveal a primary-safe bucket. Some subtypes are lower-risk candidate expansion signals, but all observed useful buckets remain net-negative when false spans are weighted 2x.

## Lowest false-per-gold buckets with gold

| bucket | tasks | span reach | added gold | added false | false/gold | net value 2x |
|---|---:|---:|---:|---:|---:|---:|
| `regex_only__span_overlap__rrf_yes__r0` | 3 | 1.0 | 15 | 15 | 1.000 | -15 |
| `symbol_only__span_overlap__rrf_no__r0` | 3 | 1.0 | 15 | 15 | 1.000 | -15 |
| `regex_only__same_file_only__rrf_yes__r0` | 15 | 0.2 | 27 | 33 | 1.222 | -39 |
| `symbol_only__same_file_only__rrf_no__r0` | 9 | 0.3333333333333333 | 27 | 63 | 2.333 | -99 |
| `symbol_regex_fusion__span_overlap__rrf_yes__r0` | 18 | 1.0 | 24 | 66 | 2.750 | -108 |
| `regex_only__same_file_only__rrf_no__r0` | 6 | 1.0 | 12 | 48 | 4.000 | -84 |
| `regex_only__single_source__rrf_yes__r0` | 12 | 0.75 | 9 | 39 | 4.333 | -69 |
| `regex_only__disagree__rrf_no__r0` | 3 | 0.0 | 3 | 27 | 9.000 | -51 |

## Highest false-span buckets

| bucket | tasks | added gold | added false | false/gold | net value 2x |
|---|---:|---:|---:|---:|---:|
| `regex_only__disagree__rrf_no__r1` | 9 | 0 | 90 | n/a | -180 |
| `regex_only__disagree__rrf_yes__r1` | 9 | 0 | 90 | n/a | -180 |
| `symbol_only__disagree__rrf_no__r1` | 9 | 0 | 90 | n/a | -180 |
| `regex_only__single_source__rrf_yes__r1` | 9 | 0 | 81 | n/a | -162 |
| `symbol_regex_fusion__span_overlap__rrf_yes__r0` | 18 | 24 | 66 | 2.750 | -108 |
| `symbol_only__same_file_only__rrf_no__r0` | 9 | 27 | 63 | 2.333 | -99 |
| `regex_only__single_source__rrf_no__r1` | 6 | 0 | 60 | n/a | -120 |
| `regex_only__same_file_only__rrf_no__r0` | 6 | 12 | 48 | 4.000 | -84 |

## Rollup highlights

| dimension | tasks | added gold | added false | false/gold | net value 2x |
|---|---:|---:|---:|---:|---:|
| `agreement:span_overlap` | 24 | 54 | 96 | 1.778 | -138 |
| `agreement:same_file_only` | 30 | 66 | 144 | 2.182 | -222 |
| `agreement:single_source` | 30 | 9 | 210 | 23.333 | -411 |
| `agreement:disagree` | 39 | 12 | 378 | 31.500 | -744 |
| `source:symbol_regex_fusion` | 18 | 24 | 66 | 2.750 | -108 |
| `source:symbol_only` | 27 | 48 | 222 | 4.625 | -396 |
| `source:regex_only` | 78 | 69 | 540 | 7.826 | -1011 |
| `rrf:rrf_yes` | 72 | 81 | 378 | 4.667 | -675 |
| `rrf:rrf_no` | 51 | 60 | 450 | 7.500 | -840 |

## Interpretation

- `span_overlap` is the best coarse agreement class, but it is still net-negative (`false_per_gold` > 1).
- `same_file_only` is not enough for primary admission.
- `disagree` and `single_source` buckets are dominated by false-span cost.
- RRF backing helps but does not make anchors primary-safe.
- P32/P30-H4 should treat P33-B buckets as budget inputs, not promotion evidence.

## Safety

- The public report is aggregate-only.
- It does not contain task IDs, candidate IDs, paths, spans, gold spans, snippets, prompts, responses, route features, or provider fields.
