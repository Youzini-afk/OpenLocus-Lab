//! OpenLocus Context — Fast Context Level0 rule prototype.
//!
//! 4-turn deterministic loop using existing regex/bm25/symbol/graph channels
//! retrieval, returning citation-valid EvidencePack. No LLM planner, no
//! remote calls. All output Evidence goes through existing
//! search/materialization paths and can be validated by `citations validate`.

pub mod plan;

pub use plan::{
    ActionRecord, FastContextDiagnostics, FastContextPlan, FastContextResult, TurnKind, TurnResult,
    fast_context,
};
