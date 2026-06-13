//! Embedding provider trait and implementations.

use crate::model::{ProviderLocality, ProviderMetadata};
use crate::openai::OpenAiEmbeddingProvider;
use anyhow::Result;

/// Trait for embedding providers.
pub trait EmbeddingProvider: Send + Sync {
    /// Return static metadata about this provider.
    fn metadata(&self) -> &ProviderMetadata;

    /// Embed a single input text, returning a vector.
    fn embed(&self, text: &str, text_sha: &str) -> Result<Vec<f32>>;
}

/// Disabled provider: always returns unavailable.
pub struct DisabledEmbeddingProvider {
    metadata: ProviderMetadata,
}

impl DisabledEmbeddingProvider {
    pub fn new() -> Self {
        Self {
            metadata: ProviderMetadata {
                provider_id: "disabled".into(),
                model_id: "disabled-v0".into(),
                dimensions: 0,
                locality: ProviderLocality::Disabled,
                max_data_level: 0,
                outbound_possible: false,
            },
        }
    }
}

impl Default for DisabledEmbeddingProvider {
    fn default() -> Self {
        Self::new()
    }
}

impl EmbeddingProvider for DisabledEmbeddingProvider {
    fn metadata(&self) -> &ProviderMetadata {
        &self.metadata
    }

    fn embed(&self, _text: &str, _text_sha: &str) -> Result<Vec<f32>> {
        anyhow::bail!("provider disabled: no embedding available")
    }
}

/// Create a provider by name.
/// Supported providers: "mock", "disabled", and OpenAI-compatible remote
/// aliases (requires explicit env config).
pub fn create_provider(name: &str) -> Result<Box<dyn EmbeddingProvider>> {
    match name {
        "mock" => Ok(Box::new(crate::mock::MockEmbeddingProvider::new())),
        "disabled" => Ok(Box::new(DisabledEmbeddingProvider::new())),
        "openai" | "openai-compatible" | "openai_compatible" => {
            Ok(Box::new(OpenAiEmbeddingProvider::from_env()?))
        }
        other => anyhow::bail!(
            "unknown provider '{}'; supported providers: mock, disabled, openai-compatible",
            other
        ),
    }
}

/// Returns true when the OpenAI-compatible remote provider appears to be
/// configured and explicitly allowed via environment variables.
pub fn is_remote_provider_configured() -> bool {
    std::env::var("OPENLOCUS_ALLOW_REMOTE").unwrap_or_default() == "1"
        && std::env::var_os("OPENLOCUS_EMBEDDING_BASE_URL").is_some()
        && std::env::var_os("OPENLOCUS_EMBEDDING_API_KEY").is_some()
        && std::env::var_os("OPENLOCUS_EMBEDDING_MODEL").is_some()
        && std::env::var_os("OPENLOCUS_EMBEDDING_DIMENSIONS").is_some()
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn disabled_provider_returns_error() {
        let p = DisabledEmbeddingProvider::new();
        assert_eq!(p.metadata().provider_id, "disabled");
        assert!(!p.metadata().locality.is_available());
        let result = p.embed("test", "sha");
        assert!(result.is_err());
    }

    #[test]
    fn create_provider_mock() {
        let p = create_provider("mock").unwrap();
        assert_eq!(p.metadata().provider_id, "mock");
    }

    #[test]
    fn create_provider_disabled() {
        let p = create_provider("disabled").unwrap();
        assert_eq!(p.metadata().provider_id, "disabled");
    }

    #[test]
    fn create_provider_unknown() {
        let result = create_provider("unknown_provider");
        assert!(result.is_err());
        let err = result.err().unwrap().to_string();
        assert!(err.contains("supported providers"));
    }

    #[test]
    fn create_provider_openai_requires_allow_remote() {
        // Without OPENLOCUS_ALLOW_REMOTE=1, creating the openai provider fails
        // during configuration parsing.
        let result = create_provider("openai");
        assert!(result.is_err());
        let err = result.err().unwrap().to_string();
        assert!(err.contains("OPENLOCUS_ALLOW_REMOTE"));
    }
}
