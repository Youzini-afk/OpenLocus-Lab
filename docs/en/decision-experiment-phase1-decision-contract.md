# Decision-oriented product experiment — Phase 1 decision contract

> **Status:** Frozen before any new run. This is a one-page decision contract,
> not a lettered protocol package. It replaces the Phase 10/10P package line
> with one causal product decision.
>
> **Stage 1 is an eligibility / headroom audit only. It is NOT a pain proof,
> NOT a product-effect proof, and NOT a downstream-agent evaluation.** No
> provider or agent runs occur in Stage 1.

## 1. Decision question

Does the existing multi-channel OpenLocus Fast Context evidence pack improve
an objective coding-task outcome versus the same-budget BM25-only baseline
enough to justify its cost (with currentness and citation validation held
constant across arms)?

## 2. Frozen source cutoff

- **Source cutoff (public):** `056877ff638d59118e05e046bd30d816e70ba2fb`
- All candidate enumeration is over non-merge commits reachable **before** this
  cutoff. The cutoff is the only SHA permitted in public output.

## 3. Estimand (frozen)

Existing multi-channel OpenLocus source-backed context delivery **versus** the
same pack-builder / rendering path with **BM25 only**.

- Currentness and citation validation are **held constant** across arms.
- **This is not a causal currentness test.** No currentness causal claim is
  permitted.

## 4. Population (frozen)

Real historical coding defects with:

- a **pinned buggy parent** commit,
- **natural pre-fix prose** (unedited commit message, or a prior linked issue
  only if locally available),
- an **exact developer-authored executable regression test**.

Retrieval-label-only corpora (R14 / R15 / R20 / R26) are **diagnostics, not
outcome tasks**. R14/R20 retrieval labels are **not** task outcomes.

## 5. Treatment and control (frozen, provider-free in Stage 1)

Both arms reuse the **same existing production Fast Context path and renderer**.

| Arm | Channels | RRF | Citation / currentness | `max_evidence` | approx token budget |
|-----|----------|-----|------------------------|----------------|---------------------|
| **Treatment** | `regex,bm25,symbol,graph` | yes | final validation held constant | 12 | 2000 |
| **Control** | `bm25` only | (single channel) | same builder/renderer/query/caps | 12 | 2000 |

- If the exact production call cannot be made without changing product code,
  the step **fails / repairs honestly** rather than emulating semantics.
- No sparse / no-context arm. No BEA. No new retrieval family.

## 6. Objective hidden-test outcome (frozen)

- **Hidden oracle policy:** exact pre-existing or developer-added tests may be
  transplanted **unchanged (byte-for-byte)** into scorer-only isolated
  overlays.
- **Forbidden:** new or edited hidden tests, expected values synthesized from
  fixes, and fix-diff context.
- Outcome is binary solve on the transplanted developer test under each arm's
  pack.

## 7. Agent parity (Stage 2 only — not executed in Stage 1)

When and only when Stage 1 passes, Stage 2 builds a real multi-turn paired agent
harness reusing provider gating / privacy patterns — **not** synthetic
task/action machinery. Arms share the same budget, tools, and prompt except the
retrieval variant, with no cross-run memory and randomized arm order.

## 8. Eligibility gate (frozen)

- **Deterministic enumeration:** all non-merge commits reachable before the
  cutoff, ordered **newest-first, then SHA**.
- **Cohort:** first 8 eligible, **minimum 5**. No replacement after packs or
  outcomes are seen.
- Candidate filters: product source + developer-authored tests, one logical
  defect, `<=2` production files and `<=100` production changed lines, natural
  pre-fix prose from an unedited commit message. Exclude docs / protocol /
  generated / eval-only / test-only / refactor / dependency / migration.
- **No hardcoded favorable candidate list.** Any coarse mechanical prefilter is
  rule-based and reports aggregate reason buckets only.

## 9. Reproducibility gate (frozen, per candidate)

A candidate is eligible only if it can be **deterministically and safely**
checked:

- buggy parent + overlay test **fails 3/3** with a stable signature,
- fixed commit + same overlay **passes 3/3**,
- relevant fixed regression **passes 2/2**,
- developer patch **passes**,
- empty patch **fails**,
- each scoring run `<= 10` minutes.

If a candidate cannot be deterministically and safely checked, it is
**excluded with a fixed reason bucket**. **Rules are never weakened to reach a
denominator.**

## 10. Headroom spend gate (frozen) — NOT an outcome

A spend gate, not a product result. Uses private fix-relevant preimage paths
(production files changed by the developer fix plus existing direct
source/config dependency paths from the parent).

- `G_i = 1` only if same-budget **BM25 omits a relevant path** AND the
  multi-channel treatment **adds valid current evidence absent from control**,
  with **materially different rendered packs**.
- Requires at least `max(2, ceil(0.4 * N))` such tasks on `N = first up to 8`
  eligible, **minimum `N = 5`**.
- Additional checks: citation rematerialization, no treatment degeneration,
  five warm retrieval repetitions per task, retrieval `p95 <= 3s`, **one or
  more isolation scans and zero isolation-scan failures**.

## 11. Live GO / STOP thresholds (frozen, Stage 2 — only if Stage 1 passes)

GO only if **all** hold:

- control has `>= 2` unsolved,
- treatment-only wins `>= 2`,
- control-only wins `= 0`,
- absolute solve gain `>= 0.25`,
- `>= 2` wins have pre-run pack differences,
- treatment retrieval `p95 <= 3s`,
- prompt token `<= 1.10x`,
- end-to-end cost `<= 1.20x`,
- zero isolation / citation failures.

**Any GO condition failure is a terminal STOP.** No task redesign, no easier
replacements, no threshold changes, no new BEA version, no extra arms, no
package continuation.

## 12. Positive action (frozen)

Internal GO authorizes **exactly one** unchanged Defects4J confirmation across
`>= 3` projects. Both screens must pass **independently** before one bounded
opt-in integration.

## 13. Claim boundary (frozen)

- Stage 1 makes **no pain, product, or effect claim**.
- Stage 1 is an eligibility / headroom audit, **not** pain proof.
- R14/R20 retrieval labels are **not** task outcomes.
- No sparse/no-context or BEA arm.
- No currentness causal claim.
- Public output is **aggregate counts / buckets / gate status / reason buckets
  only** — no commit SHAs (except the public cutoff), task IDs, issue prose,
  paths, test names, diffs, patches, expected values, private pack text,
  per-task rows, prompts, or provider details. Private rows / manifests / logs
  stay only in the ignored `runs/` tree.
