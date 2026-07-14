//! Reciprocal Rank Fusion (RRF) for combining multi-channel evidence.
//!
//! RRF formula: score_rrf(d) = Σ 1 / (k + rank_i(d))  where k=60.
//!
//! Precision-biased dedup:
//! - Exact same (path, start_line, end_line) → merge why/score/channels.
//! - Overlapping spans on same path → keep the narrower one, discard the wider.
//!   The wider's why and channels are merged into the narrower survivor
//!   (no span widening). Score contributions from the wider are also absorbed.
//! - RRF only changes ranking/score, never widens spans.

use openlocus_core::{Channel, Evidence, EvidenceCore, EvidenceMeta, ScoreParts};
use std::collections::HashMap;

/// RRF constant
const K: u64 = 60;

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
    channel_evidence: Vec<(Vec<Evidence>, Channel, u64)>,
    equal_scores_share_rank: bool,
) -> Vec<Evidence> {
    // Key: (path, start_line, end_line) → accumulated RRF score + metadata
    let mut merged: HashMap<(String, u64, u64), MergedEntry> = HashMap::new();

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

    // Overlap dedup: for same path, if one span fully contains another:
    // - The narrower survives.
    // - The wider's why, channels, and RRF score are merged into the narrower.
    // - The wider is then removed.
    let keys: Vec<_> = merged.keys().cloned().collect();
    for i in 0..keys.len() {
        for j in 0..keys.len() {
            if i == j {
                continue;
            }
            let key_i = &keys[i]; // potentially wider
            let key_j = &keys[j]; // potentially narrower
            if key_i.0 != key_j.0 {
                continue;
            }
            // Check if key_i strictly contains key_j
            if key_i.1 <= key_j.1 && key_i.2 >= key_j.2 && (key_i.1 < key_j.1 || key_i.2 > key_j.2)
            {
                // key_i is wider, key_j is narrower
                // Merge wider's metadata into narrower, then remove wider
                if let Some(wider) = merged.get(key_i).cloned()
                    && let Some(narrower) = merged.get_mut(key_j)
                {
                    narrower.rrf_score += wider.rrf_score;
                    narrower.whys.extend(wider.whys.iter().cloned());
                    for ch in wider.channels {
                        if !narrower.channels.contains(&ch) {
                            narrower.channels.push(ch);
                        }
                    }
                }
                merged.remove(key_i);
            }
        }
    }

    // Build final evidence with RRF scores
    let mut results: Vec<Evidence> = merged
        .into_values()
        .map(|entry| {
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
            .partial_cmp(&a.core.score)
            .unwrap_or(std::cmp::Ordering::Equal)
            .then_with(|| a.core.path.cmp(&b.core.path))
            .then_with(|| a.core.start_line.cmp(&b.core.start_line))
            .then_with(|| a.core.end_line.cmp(&b.core.end_line))
    });

    results
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
    let mut seen = Vec::new();
    for ch in channels {
        if !seen.contains(&ch) {
            seen.push(ch);
        }
    }
    seen
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
