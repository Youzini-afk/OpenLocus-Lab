//! OpenLocus Derived — LLM Indexing Research Candidate Level0 Safety Scaffold.
//!
//! DerivedIndexView is NOT Evidence. It cannot bypass StoreHit/materialize_evidence.
//! If derived search is ever implemented, it must materialize source evidence.
//!
//! Key safety constraints:
//! - No network/real LLM/API key connections.
//! - High-risk kinds (candidate_edge, bug_symptom_hint) disabled by default.
//! - Default data_level <= 1; no full raw code snippets in derived text.
//! - Build only from scan_repo filtered records; no self filesystem walk.
//! - View ID is deterministic on source/model/prompt/policy/kind.

pub mod generator;
pub mod model;
pub mod store;
pub mod validation;
