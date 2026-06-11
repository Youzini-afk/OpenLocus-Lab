//! Persistent Tantivy BM25 index with manifest tracking.
//!
//! Key design constraints:
//! - Tantivy index cannot directly produce authoritative Evidence.
//!   Every hit must be re-verified against the current filesystem.
//! - Stale hits (content_sha mismatch) are skipped, not emitted.
//! - Manifest tracks per-file content_sha so staleness is detectable.
//! - Policy hash is recorded; mismatch signals need for rebuild.

pub mod manifest;
pub mod persistent;

pub use manifest::*;
pub use persistent::*;
