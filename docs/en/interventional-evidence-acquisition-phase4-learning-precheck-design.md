# Interventional Evidence Acquisition Phase 4 Learning Precheck Design

Date: 2026-07-07

Phase: `phase4_action_outcome_learning_precheck_design`

Status: `phase4_action_outcome_learning_precheck_design_only_no_training_no_claim`

This is design only. It does not train a model, authorize training, read private rows, collect data, change CI, change runtime/default behavior, add retrieval families, or make a method claim.

## What Phase 2, Phase 3, and Phase 3B showed

Phase 2 and Phase 3 showed that the small local comparison protocol can run and replicate a bucket-level pattern on hard current-source tasks:

- controls stayed at `count_0`;
- EvidenceCore materialization checks stayed intact;
- public outputs stayed aggregate-only;
- best fixed local/acquisition baseline buckets were nontrivial in the public screens.

Phase 3B closed that as a public replication summary. It did not prove a method winner, lift, signal, product readiness, or default change.

This is enough to design a learning precheck. It is not enough to train, deploy, or promote a model.

## Future learning question

Can pre-action, non-leaky features predict which local evidence-finding action is worth trying on hard tasks?

The question is about a future screen only. It is not a claim that learning will work.

## Allowed future features

Future feature rows may use only information that is present before the action:

- query or task coarse family bucket;
- candidate pool coarse stats, such as bucketed count, top-score bucket, and rank-diversity bucket;
- action label;
- budget bucket and coarse availability flags;
- prior step count or budget bucket if a future multi-step trace exists.

All features should be bucketed or categorical. Public output must remain aggregate-only.

## Forbidden and leaky features

The future precheck must not use features that reveal the answer or expose private data:

- actual success label;
- target path, range, hash, or content;
- post-action read result;
- downstream validation result;
- exact private task ID;
- source snippets;
- gold labels;
- provider payloads, prompts, or responses.

Any leakage rule failure should fail closed.

## Future target labels

Possible target labels, design only:

- `evidence_success`, using the same EvidenceCore definition as Phase 2/3;
- `cost_adjusted_success_bucket`, only if separately designed later.

`stop` and `abstain` remain controls. Candidate-found alone is not evidence.

## Split discipline

A future precheck must avoid task leakage:

- hold out by task family, repo, or file-family where possible;
- no task leakage across train/validation splits;
- no exact paths, ranges, hashes, snippets, private IDs, or private manifests in public output;
- buckets only in public reports.

## Minimum precheck before any training

Before any model training is considered, a future design must first:

- inspect feature coverage aggregate-only;
- check class balance aggregate-only;
- check leakage rules with a fail-closed validator;
- write stop/go thresholds before running.

Passing this precheck would not be model evidence. It would only say whether a tiny learning experiment is safe enough to consider.

## Stop/go outcomes

- `stop_no_learning_claim`: stop; no learning claim.
- `repair_feature_contract_no_claim`: repair feature, label, split, or privacy contract.
- `learning_precheck_ready_no_training`: precheck design is ready, but training is still not authorized.

## Hard forbidden list

This Phase 4 design does not authorize:

- model training now;
- RPM-D2 or model scaling;
- LLM/provider/network actions;
- runtime/default changes;
- new retrieval families;
- winner, lift, or signal claims;
- OpenLocus v3 branding or product promotion.

Any future training step needs a separate explicit decision after feature, label, leakage, and split rules are written.
