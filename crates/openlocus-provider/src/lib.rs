//! OpenLocus Provider — safe embedding / LLM-derived indexing bakeoff scaffold.
//!
//! Design constraints:
//! - Remote providers are denied by default and require explicit environment
//!   and policy opt-in.
//! - Default build is fully local; EvidenceCore is unchanged.
//! - Dense/mock/derived hints produce candidate StoreHits only;
//!   final Evidence must go through `openlocus_store::materialize_evidence`.
//! - Audit/cache/vector store never store raw snippet text in audit;
//!   vector store stores path/range/source_content_sha/language/vector only.
//! - Real model integrations are candidate/supporting-only research paths; no
//!   default promotion or semantic quality claim is implied.

pub mod audit;
pub mod cache;
pub mod dense_store;
pub mod gate;
pub mod mock;
pub mod model;
pub mod openai;
pub mod provider;
