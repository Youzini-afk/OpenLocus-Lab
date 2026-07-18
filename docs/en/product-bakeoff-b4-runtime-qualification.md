# Product Bakeoff B4 Exact Linux Runtime Qualification

Date: 2026-07-18

Status: `product_bakeoff_b4_exact_linux_runtime_qualified_private_multi_panel_authoring_allowed_after_publication_ci`

## Outcome

The exact B4 source checkpoint and its green control-plane CI were exercised on the current Linux runner with the actual release CLI. All four public synthetic query categories passed with current evidence, executed BM25 receipts, zero stale or invalid skips, and zero provider/network calls. The stable runner profile and exact CLI bytes are frozen only in the private runtime receipt.

No private candidate, repository, task, query, oracle, or treatment output was read or produced. This is runtime-integrity evidence only, not an empirical product result and not a formal-launch authorization.

## Resource admission

The runner passed the frozen minimum class: Linux x64, at least eight effective CPU quotas, a finite memory limit of at least 32 GiB with at least 24 GiB effectively available, no active swap, Python 3.10+, Rust/Cargo 1.95.0, and non-rotational local scratch outside the checkout. The scratch gate is the calculated serial working set of 5,100,273,664 free bytes (about 4.75 GiB); it is not a fixed paid-disk reservation and no GPU is required.

The closed B4 CLI now raises its own per-process open-file soft limit to 65,535 when the hard limit permits it, and fails closed otherwise. This removes dependence on a shell-specific default while preserving the admitted runner class for qualification, authoring, freeze, readiness, and formal execution.

## Boundary

After this aggregate-only artifact is committed and its publication CI is green, the only newly authorized action is private authoring and freeze of twelve mutually disjoint panels. The formal attempt remains unauthorized until the private holdout is frozen, aggregate readiness is published and CI-green, and a separate private launch authorization is created.

Public artifact: [`product_bakeoff_b4_runtime_qualification.json`](../../artifacts/product_bakeoff_b4_runtime_qualification/product_bakeoff_b4_runtime_qualification.json).
