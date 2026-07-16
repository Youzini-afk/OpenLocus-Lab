//! Reciprocal Rank Fusion (RRF) for combining multi-channel evidence.
//!
//! RRF formula: score_rrf(d) = Σ 1 / (k + rank_i(d))  where k=60.
//!
//! Precision-biased dedup:
//! - Exact same (path, start_line, end_line) → merge why/score/channels.
//! - Strictly containing spans on the same path → keep minimal descendants and
//!   discard wider ancestors (no span widening). An unambiguous ancestor vote
//!   is absorbed by the sole narrow survivor; an ambiguous ancestor vote is
//!   split evenly across all minimal descendants so total score is conserved
//!   without a positional tie bias. Why/channels follow the same descendants.
//! - RRF only changes ranking/score, never widens spans.

use openlocus_core::{Channel, Evidence, EvidenceCore, EvidenceMeta, ScoreParts};
use std::cmp::Ordering;
use std::collections::BTreeMap;

/// RRF constant
const K: u64 = 60;

type EvidenceKey = (String, u64, u64);

/// Combine evidence from multiple channels using RRF.
///
/// Input: multiple `Vec<Evidence>` from different channels (regex, bm25, symbol).
/// Output: deduplicated, RRF-scored, sorted evidence.
pub fn rrf_combine(channel_evidence: Vec<(Vec<Evidence>, Channel)>) -> Vec<Evidence> {
    let weighted = channel_evidence
        .into_iter()
        .map(|(evidence, channel)| (evidence, channel, 1))
        .collect();
    rrf_combine_impl(weighted, false)
}

/// Combine evidence using RRF while allowing exact native-score ties to
/// share a competition rank (`1, 1, 3`). Input lists must already be sorted
/// by native score descending with a deterministic secondary order.
///
/// This leaves [`rrf_combine`] unchanged for existing callers while exposing
/// an explicit production variant for workflows that must preserve genuine
/// equal-quality candidates as equal-ranked.
pub fn rrf_combine_with_rank_ties(
    channel_evidence: Vec<(Vec<Evidence>, Channel)>,
) -> Vec<Evidence> {
    let weighted = channel_evidence
        .into_iter()
        .map(|(evidence, channel)| (evidence, channel, 1))
        .collect();
    rrf_combine_impl(weighted, true)
}

/// Combine evidence using competition-rank ties and explicit positive
/// integer channel weights. A weight of `2` contributes two RRF votes at
/// the same rank. Existing unweighted entry points remain unchanged.
pub fn rrf_combine_with_rank_ties_and_channel_weights(
    channel_evidence: Vec<(Vec<Evidence>, Channel, u64)>,
) -> Vec<Evidence> {
    rrf_combine_impl(channel_evidence, true)
}

fn rrf_combine_impl(
    mut channel_evidence: Vec<(Vec<Evidence>, Channel, u64)>,
    equal_scores_share_rank: bool,
) -> Vec<Evidence> {
    channel_evidence.sort_by(compare_channel_inputs);
    // Key: (path, start_line, end_line) → accumulated RRF score + metadata
    let mut merged: BTreeMap<EvidenceKey, MergedEntry> = BTreeMap::new();

    for (evidences, _channel, channel_weight) in &channel_evidence {
        let mut competition_rank = 1usize;
        let mut previous_native_score: Option<f64> = None;
        for (position, evidence) in evidences.iter().enumerate() {
            if !equal_scores_share_rank
                || previous_native_score.is_none_or(|score| score != evidence.core.score)
            {
                competition_rank = position + 1;
            }
            let key = (
                evidence.core.path.clone(),
                evidence.core.start_line,
                evidence.core.end_line,
            );

            let rrf_contribution = *channel_weight as f64 / (K as f64 + competition_rank as f64);

            let entry = merged.entry(key).or_insert_with(|| MergedEntry {
                core: evidence.core.clone(),
                meta: evidence.meta.clone(),
                rrf_score: 0.0,
                channels: Vec::new(),
                whys: Vec::new(),
            });

            entry.rrf_score += rrf_contribution;
            entry.channels.push(_channel.clone());
            entry.whys.extend(evidence.core.why.iter().cloned());
            previous_native_score = Some(evidence.core.score);
        }
    }

    collapse_overlaps(&mut merged);

    // Build final evidence with RRF scores
    let mut results: Vec<Evidence> = merged
        .into_values()
        .map(|mut entry| {
            entry.normalize_metadata();
            let mut evidence = Evidence::new(
                entry.core.path,
                entry.core.start_line,
                entry.core.end_line,
                entry.core.content_sha,
                entry.rrf_score,
                entry.whys,
                dedup_channels(entry.channels),
            );
            if let Some(meta) = entry.meta {
                let mut m = meta;
                m.score_parts = Some(ScoreParts {
                    reranker: Some(entry.rrf_score),
                    ..m.score_parts.unwrap_or_default()
                });
                evidence = evidence.with_meta(m);
            }
            evidence
        })
        .collect();

    // Sort by RRF score descending, then path asc, start_line asc, end_line asc for determinism
    results.sort_by(|a, b| {
        b.core
            .score
            .total_cmp(&a.core.score)
            .then_with(|| a.core.path.cmp(&b.core.path))
            .then_with(|| a.core.start_line.cmp(&b.core.start_line))
            .then_with(|| a.core.end_line.cmp(&b.core.end_line))
    });

    results
}

fn compare_channel_inputs(
    left: &(Vec<Evidence>, Channel, u64),
    right: &(Vec<Evidence>, Channel, u64),
) -> Ordering {
    left.1
        .as_str()
        .cmp(right.1.as_str())
        .then_with(|| left.2.cmp(&right.2))
        .then_with(|| compare_evidence_lists(&left.0, &right.0))
}

fn compare_evidence_lists(left: &[Evidence], right: &[Evidence]) -> Ordering {
    for (left_item, right_item) in left.iter().zip(right) {
        let ordering = left_item
            .core
            .path
            .cmp(&right_item.core.path)
            .then_with(|| left_item.core.start_line.cmp(&right_item.core.start_line))
            .then_with(|| left_item.core.end_line.cmp(&right_item.core.end_line))
            .then_with(|| left_item.core.content_sha.cmp(&right_item.core.content_sha))
            .then_with(|| left_item.core.score.total_cmp(&right_item.core.score));
        if !ordering.is_eq() {
            return ordering;
        }
    }
    left.len().cmp(&right.len())
}

#[derive(Clone)]
struct MergedEntry {
    core: EvidenceCore,
    meta: Option<EvidenceMeta>,
    rrf_score: f64,
    channels: Vec<Channel>,
    whys: Vec<String>,
}

fn dedup_channels(channels: Vec<Channel>) -> Vec<Channel> {
    let mut channels = channels;
    channels.sort_by_key(Channel::as_str);
    channels.dedup();
    channels
}

fn strictly_contains(outer: &EvidenceKey, inner: &EvidenceKey) -> bool {
    outer.0 == inner.0
        && outer.1 <= inner.1
        && outer.2 >= inner.2
        && (outer.1 < inner.1 || outer.2 > inner.2)
}

fn minimal_overlap_survivors(keys: &[EvidenceKey], outer: &EvidenceKey) -> Vec<EvidenceKey> {
    let mut survivors: Vec<EvidenceKey> = keys
        .iter()
        .filter(|candidate| strictly_contains(outer, candidate))
        .filter(|candidate| !keys.iter().any(|other| strictly_contains(candidate, other)))
        .cloned()
        .collect();
    survivors.sort_by_key(|candidate| {
        (
            candidate.2.saturating_sub(candidate.1),
            candidate.1,
            candidate.2,
        )
    });
    survivors
}

/// Collapse containment once from an immutable key snapshot.
///
/// A wider span can contain several disjoint narrow spans.  The old
/// mutation-while-iterating implementation assigned the wider contribution
/// to whichever child happened to appear first in a randomized `HashMap`
/// key order.  Each non-minimal span now transfers exactly once to the full
/// set of minimal descendants.  An unambiguous chain transfers all of its
/// contribution to the narrowest span; ambiguous siblings split the score
/// evenly so total RRF mass is conserved without inventing a positional
/// winner.  Metadata is copied to every descendant covered by the wider span.
fn collapse_overlaps(merged: &mut BTreeMap<EvidenceKey, MergedEntry>) {
    let keys: Vec<EvidenceKey> = merged.keys().cloned().collect();
    let transfers: Vec<(EvidenceKey, Vec<EvidenceKey>)> = keys
        .iter()
        .filter_map(|source| {
            let recipients = minimal_overlap_survivors(&keys, source);
            (!recipients.is_empty()).then(|| (source.clone(), recipients))
        })
        .collect();

    for (source, recipients) in transfers {
        let wider = merged
            .remove(&source)
            .expect("overlap source must exist in the immutable key snapshot");
        let score_share = wider.rrf_score / recipients.len() as f64;
        for recipient in recipients {
            let narrower = merged
                .get_mut(&recipient)
                .expect("overlap recipient must be a minimal survivor");
            narrower.absorb_share(&wider, score_share);
        }
    }
}

impl MergedEntry {
    fn absorb_share(&mut self, other: &MergedEntry, score_share: f64) {
        self.rrf_score += score_share;
        self.whys.extend(other.whys.iter().cloned());
        self.channels.extend(other.channels.iter().cloned());
    }

    fn normalize_metadata(&mut self) {
        self.whys.sort();
        self.whys.dedup();
        self.channels = dedup_channels(std::mem::take(&mut self.channels));
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use openlocus_core::Freshness;

    #[test]
    fn rrf_combines_and_deduplicates() {
        let regex_evidence = vec![
            Evidence::new(
                "a.rs",
                1,
                1,
                "sha",
                1.0,
                vec!["regex match".into()],
                vec![Channel::Regex],
            ),
            Evidence::new(
                "b.rs",
                5,
                5,
                "sha",
                1.0,
                vec!["regex match".into()],
                vec![Channel::Regex],
            ),
        ];

        let bm25_evidence = vec![
            Evidence::new(
                "a.rs",
                1,
                1,
                "sha",
                2.0,
                vec!["bm25 match".into()],
                vec![Channel::Bm25],
            ),
            Evidence::new(
                "c.rs",
                10,
                10,
                "sha",
                1.5,
                vec!["bm25 match".into()],
                vec![Channel::Bm25],
            ),
        ];

        let result = rrf_combine(vec![
            (regex_evidence, Channel::Regex),
            (bm25_evidence, Channel::Bm25),
        ]);

        // a.rs:1-1 appears in both channels → merged, higher RRF score
        assert!(
            result
                .iter()
                .any(|e| e.core.path == "a.rs" && e.core.start_line == 1)
        );
        let a_ev = result.iter().find(|e| e.core.path == "a.rs").unwrap();
        assert!(a_ev.core.channels.contains(&Channel::Regex));
        assert!(a_ev.core.channels.contains(&Channel::Bm25));
        assert!(a_ev.core.score > 0.0);
    }

    #[test]
    fn rrf_rank_ties_use_competition_ranking() {
        let evidence = vec![
            Evidence::new(
                "a.rs",
                1,
                1,
                "sha",
                2.0,
                vec!["a".into()],
                vec![Channel::Bm25],
            ),
            Evidence::new(
                "b.rs",
                1,
                1,
                "sha",
                2.0,
                vec!["b".into()],
                vec![Channel::Bm25],
            ),
            Evidence::new(
                "c.rs",
                1,
                1,
                "sha",
                1.0,
                vec!["c".into()],
                vec![Channel::Bm25],
            ),
        ];

        let result = rrf_combine_with_rank_ties(vec![(evidence, Channel::Bm25)]);
        let a = result.iter().find(|item| item.core.path == "a.rs").unwrap();
        let b = result.iter().find(|item| item.core.path == "b.rs").unwrap();
        let c = result.iter().find(|item| item.core.path == "c.rs").unwrap();
        assert_eq!(a.core.score, b.core.score);
        assert_eq!(a.core.score, 1.0 / 61.0);
        assert_eq!(c.core.score, 1.0 / 63.0);
        assert_eq!(result[0].core.path, "a.rs");
        assert_eq!(result[1].core.path, "b.rs");
    }

    #[test]
    fn weighted_graph_vote_can_promote_a_related_candidate() {
        let definition = |channel| {
            Evidence::new(
                "definition.rs",
                1,
                1,
                "sha-definition",
                2.0,
                vec!["definition".into()],
                vec![channel],
            )
        };
        let dependency = |score, channel| {
            Evidence::new(
                "dependency.rs",
                1,
                1,
                "sha-dependency",
                score,
                vec!["dependency".into()],
                vec![channel],
            )
        };
        let result = rrf_combine_with_rank_ties_and_channel_weights(vec![
            (
                vec![definition(Channel::Bm25), dependency(1.0, Channel::Bm25)],
                Channel::Bm25,
                1,
            ),
            (
                vec![definition(Channel::Regex), dependency(2.0, Channel::Regex)],
                Channel::Regex,
                1,
            ),
            (
                vec![definition(Channel::TreeSitter)],
                Channel::TreeSitter,
                1,
            ),
            (vec![dependency(2.0, Channel::Graph)], Channel::Graph, 2),
        ]);

        assert_eq!(result[0].core.path, "dependency.rs");
        assert!(result[0].core.score > result[1].core.score);
    }

    #[test]
    fn rrf_overlap_dedup_keeps_narrower_and_merges() {
        let wide = vec![Evidence::new(
            "a.rs",
            1,
            20,
            "sha",
            1.0,
            vec!["wide bm25".into()],
            vec![Channel::Bm25],
        )];
        let narrow = vec![Evidence::new(
            "a.rs",
            5,
            7,
            "sha",
            1.0,
            vec!["narrow regex".into()],
            vec![Channel::Regex],
        )];

        let result = rrf_combine(vec![(wide, Channel::Bm25), (narrow, Channel::Regex)]);

        // The wider span should be removed
        assert!(
            !result
                .iter()
                .any(|e| e.core.start_line == 1 && e.core.end_line == 20)
        );
        // The narrower span should survive
        assert!(
            result
                .iter()
                .any(|e| e.core.start_line == 5 && e.core.end_line == 7)
        );
        // The narrower survivor should have absorbed the wider's channels and why
        let narrow_ev = result
            .iter()
            .find(|e| e.core.start_line == 5 && e.core.end_line == 7)
            .unwrap();
        assert!(
            narrow_ev.core.channels.contains(&Channel::Bm25),
            "narrower should inherit wider's Bm25 channel"
        );
        assert!(
            narrow_ev.core.channels.contains(&Channel::Regex),
            "narrower should keep its own Regex channel"
        );
        assert!(
            narrow_ev.core.why.iter().any(|w| w.contains("wide")),
            "narrower should inherit wider's why"
        );
        assert!(
            narrow_ev.core.why.iter().any(|w| w.contains("narrow")),
            "narrower should keep its own why"
        );
    }

    #[test]
    fn rrf_overlap_siblings_split_ambiguous_contribution_evenly() {
        fn evidence(start: u64, end: u64, label: &str, channel: Channel) -> Vec<Evidence> {
            vec![Evidence::new(
                "a.rs",
                start,
                end,
                "sha",
                1.0,
                vec![label.into()],
                vec![channel],
            )]
        }

        let permutations = [
            [0usize, 1, 2],
            [0, 2, 1],
            [1, 0, 2],
            [1, 2, 0],
            [2, 0, 1],
            [2, 1, 0],
        ];
        let mut baseline = None;
        for _ in 0..32 {
            for permutation in permutations {
                let inputs = [
                    (evidence(1, 20, "wide", Channel::Bm25), Channel::Bm25),
                    (evidence(5, 7, "left", Channel::Regex), Channel::Regex),
                    (
                        evidence(10, 12, "right", Channel::TreeSitter),
                        Channel::TreeSitter,
                    ),
                ];
                let result = rrf_combine(
                    permutation
                        .into_iter()
                        .map(|index| inputs[index].clone())
                        .collect(),
                );
                let signature: Vec<_> = result
                    .iter()
                    .map(|item| {
                        (
                            item.core.start_line,
                            item.core.end_line,
                            item.core.score.to_bits(),
                            item.core.channels.clone(),
                            item.core.why.clone(),
                        )
                    })
                    .collect();
                if let Some(expected) = &baseline {
                    assert_eq!(&signature, expected);
                } else {
                    baseline = Some(signature);
                }

                let left = result
                    .iter()
                    .find(|item| item.core.start_line == 5 && item.core.end_line == 7)
                    .unwrap();
                let right = result
                    .iter()
                    .find(|item| item.core.start_line == 10 && item.core.end_line == 12)
                    .unwrap();
                assert_eq!(left.core.score, 1.5 / 61.0);
                assert_eq!(right.core.score, 1.5 / 61.0);
                assert!(
                    (result.iter().map(|item| item.core.score).sum::<f64>() - 3.0 / 61.0).abs()
                        < f64::EPSILON
                );
            }
        }
    }

    #[test]
    fn rrf_overlap_chain_transfers_every_contribution_to_narrowest() {
        let result = rrf_combine(vec![
            (
                vec![Evidence::new(
                    "a.rs",
                    1,
                    30,
                    "sha",
                    1.0,
                    vec!["wide".into()],
                    vec![Channel::Bm25],
                )],
                Channel::Bm25,
            ),
            (
                vec![Evidence::new(
                    "a.rs",
                    5,
                    20,
                    "sha",
                    1.0,
                    vec!["middle".into()],
                    vec![Channel::Regex],
                )],
                Channel::Regex,
            ),
            (
                vec![Evidence::new(
                    "a.rs",
                    8,
                    10,
                    "sha",
                    1.0,
                    vec!["narrow".into()],
                    vec![Channel::TreeSitter],
                )],
                Channel::TreeSitter,
            ),
        ]);

        assert_eq!(result.len(), 1);
        assert_eq!(
            (result[0].core.start_line, result[0].core.end_line),
            (8, 10)
        );
        assert_eq!(result[0].core.score, 3.0 / 61.0);
        assert_eq!(result[0].core.why, vec!["middle", "narrow", "wide"]);
    }

    #[test]
    fn rrf_exact_span_is_stable_across_channel_permutations() {
        let inputs = [
            (
                vec![Evidence::new(
                    "a.rs",
                    3,
                    3,
                    "sha",
                    4.0,
                    vec!["bm25".into()],
                    vec![Channel::Bm25],
                )],
                Channel::Bm25,
            ),
            (
                vec![Evidence::new(
                    "a.rs",
                    3,
                    3,
                    "sha",
                    3.0,
                    vec!["graph".into()],
                    vec![Channel::Graph],
                )],
                Channel::Graph,
            ),
            (
                vec![Evidence::new(
                    "a.rs",
                    3,
                    3,
                    "sha",
                    2.0,
                    vec!["regex".into()],
                    vec![Channel::Regex],
                )],
                Channel::Regex,
            ),
            (
                vec![Evidence::new(
                    "a.rs",
                    3,
                    3,
                    "sha",
                    1.0,
                    vec!["symbol".into()],
                    vec![Channel::TreeSitter],
                )],
                Channel::TreeSitter,
            ),
        ];
        let permutations = [[0usize, 1, 2, 3], [3, 2, 1, 0], [1, 3, 0, 2], [2, 0, 3, 1]];
        let mut baseline = None;
        for permutation in permutations {
            let result = rrf_combine(
                permutation
                    .into_iter()
                    .map(|index| inputs[index].clone())
                    .collect(),
            );
            assert_eq!(result.len(), 1);
            let signature = (
                result[0].core.score.to_bits(),
                result[0].core.channels.clone(),
                result[0].core.why.clone(),
            );
            if let Some(expected) = &baseline {
                assert_eq!(&signature, expected);
            } else {
                baseline = Some(signature);
            }
        }
    }

    #[test]
    #[ignore = "large synthetic determinism stress; run via the Linux stress script"]
    fn rrf_large_ambiguous_overlap_conserves_score_without_positional_bias() {
        let span_count = std::env::var("OPENLOCUS_DETERMINISM_STRESS_RRF_SPANS")
            .ok()
            .and_then(|value| value.parse::<usize>().ok())
            .unwrap_or(4_096);
        assert!((32..=20_000).contains(&span_count));

        let wide = vec![Evidence::new(
            "a.rs",
            1,
            (span_count * 2) as u64,
            "sha",
            1.0,
            vec!["wide".into()],
            vec![Channel::Bm25],
        )];
        let siblings: Vec<Evidence> = (0..span_count)
            .map(|index| {
                let line = (index * 2 + 1) as u64;
                Evidence::new(
                    "a.rs",
                    line,
                    line,
                    "sha",
                    1.0,
                    vec![format!("sibling-{index}")],
                    vec![Channel::Regex],
                )
            })
            .collect();
        let result =
            rrf_combine_with_rank_ties(vec![(wide, Channel::Bm25), (siblings, Channel::Regex)]);
        assert_eq!(result.len(), span_count);
        let expected_each = 1.0 / 61.0 + 1.0 / (61.0 * span_count as f64);
        for (index, item) in result.iter().enumerate() {
            let expected_line = (index * 2 + 1) as u64;
            assert_eq!(
                (item.core.start_line, item.core.end_line),
                (expected_line, expected_line)
            );
            assert!((item.core.score - expected_each).abs() < 1e-12);
        }
        let expected_total = (span_count as f64 + 1.0) / 61.0;
        let actual_total = result.iter().map(|item| item.core.score).sum::<f64>();
        assert!((actual_total - expected_total).abs() < 1e-9);
    }

    #[test]
    fn rrf_same_span_merges_channels() {
        let ev1 = vec![
            Evidence::new(
                "a.rs",
                3,
                3,
                "sha",
                1.0,
                vec!["regex".into()],
                vec![Channel::Regex],
            )
            .with_freshness(Freshness::VerifiedCurrent),
        ];
        let ev2 = vec![
            Evidence::new(
                "a.rs",
                3,
                3,
                "sha",
                2.0,
                vec!["bm25".into()],
                vec![Channel::Bm25],
            )
            .with_freshness(Freshness::VerifiedCurrent),
        ];

        let result = rrf_combine(vec![(ev1, Channel::Regex), (ev2, Channel::Bm25)]);

        assert_eq!(result.len(), 1);
        let ev = &result[0];
        assert!(ev.core.channels.contains(&Channel::Regex));
        assert!(ev.core.channels.contains(&Channel::Bm25));
        assert!(
            ev.core.why.len() >= 2,
            "should merge why from both channels"
        );
    }

    #[test]
    fn rrf_sorted_deterministic_tiebreak() {
        // Two evidence with same score → tiebreak by path, then start_line, then end_line
        let ev1 = vec![Evidence::new(
            "b.rs",
            1,
            1,
            "sha",
            1.0,
            vec!["b".into()],
            vec![Channel::Regex],
        )];
        let ev2 = vec![Evidence::new(
            "a.rs",
            1,
            1,
            "sha",
            1.0,
            vec!["a".into()],
            vec![Channel::Regex],
        )];

        let result = rrf_combine(vec![(ev1, Channel::Regex), (ev2, Channel::Bm25)]);

        // Same RRF score → tiebreak by path ascending → a.rs first
        assert_eq!(result[0].core.path, "a.rs");
        assert_eq!(result[1].core.path, "b.rs");
    }

    #[test]
    fn rrf_preserves_narrow_spans() {
        let inputs = vec![
            (
                vec![
                    Evidence::new(
                        "a.rs",
                        10,
                        10,
                        "sha",
                        1.0,
                        vec!["r".into()],
                        vec![Channel::Regex],
                    ),
                    Evidence::new(
                        "a.rs",
                        50,
                        50,
                        "sha",
                        1.0,
                        vec!["r".into()],
                        vec![Channel::Regex],
                    ),
                ],
                Channel::Regex,
            ),
            (
                vec![Evidence::new(
                    "b.rs",
                    5,
                    5,
                    "sha",
                    1.0,
                    vec!["b".into()],
                    vec![Channel::Bm25],
                )],
                Channel::Bm25,
            ),
        ];

        let result = rrf_combine(inputs);
        // All spans should be narrow (single line)
        for ev in &result {
            assert_eq!(
                ev.core.start_line, ev.core.end_line,
                "spans should stay narrow after RRF"
            );
        }
    }
}
