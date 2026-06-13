//! OpenAI-compatible embedding provider (bounded R31 real remote scaffold).
//!
//! Configuration is read from environment variables:
//! - `OPENLOCUS_EMBEDDING_BASE_URL`
//! - `OPENLOCUS_EMBEDDING_API_KEY`
//! - `OPENLOCUS_EMBEDDING_MODEL`
//! - `OPENLOCUS_EMBEDDING_DIMENSIONS`
//!
//! Provider creation requires `OPENLOCUS_ALLOW_REMOTE=1`.
//! The implementation never logs the API key or raw embedding inputs.

use crate::model::{ProviderLocality, ProviderMetadata};
use crate::provider::EmbeddingProvider;
use anyhow::{Context, Result, bail};
use serde::{Deserialize, Serialize};

/// Configuration for the OpenAI-compatible embedding provider.
#[derive(Clone)]
pub struct OpenAiEmbeddingConfig {
    pub base_url: String,
    pub api_key: String,
    pub model: String,
    pub dimensions: usize,
}

impl std::fmt::Debug for OpenAiEmbeddingConfig {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("OpenAiEmbeddingConfig")
            .field("base_url", &self.base_url)
            .field("api_key", &"[REDACTED]")
            .field("model", &self.model)
            .field("dimensions", &self.dimensions)
            .finish()
    }
}

impl OpenAiEmbeddingConfig {
    /// Parse configuration from explicit key/value lookups.
    ///
    /// `get_var` should behave like `std::env::var`: return the value for a
    /// given variable name, or `None` if it is unset. This indirection makes
    /// the parsing logic unit-testable without mutating the process
    /// environment.
    pub fn from_env_values<F>(get_var: F) -> Result<Self>
    where
        F: Fn(&str) -> Option<String>,
    {
        if get_var("OPENLOCUS_ALLOW_REMOTE").as_deref() != Some("1") {
            bail!("remote providers disabled: set OPENLOCUS_ALLOW_REMOTE=1 to enable");
        }

        let base_url = get_var("OPENLOCUS_EMBEDDING_BASE_URL")
            .context("OPENLOCUS_EMBEDDING_BASE_URL not set")?;
        let api_key = get_var("OPENLOCUS_EMBEDDING_API_KEY")
            .context("OPENLOCUS_EMBEDDING_API_KEY not set")?;
        let model =
            get_var("OPENLOCUS_EMBEDDING_MODEL").context("OPENLOCUS_EMBEDDING_MODEL not set")?;
        let dimensions = get_var("OPENLOCUS_EMBEDDING_DIMENSIONS")
            .context("OPENLOCUS_EMBEDDING_DIMENSIONS not set")?
            .parse::<usize>()
            .context("OPENLOCUS_EMBEDDING_DIMENSIONS must be a positive integer")?;

        Ok(Self {
            base_url,
            api_key,
            model,
            dimensions,
        })
    }

    /// Load configuration from the real process environment.
    pub fn from_env() -> Result<Self> {
        Self::from_env_values(|key| std::env::var(key).ok())
    }
}

/// OpenAI-compatible embedding provider.
pub struct OpenAiEmbeddingProvider {
    metadata: ProviderMetadata,
    config: OpenAiEmbeddingConfig,
    client: ureq::Agent,
}

impl OpenAiEmbeddingProvider {
    /// Create a provider from an explicit configuration.
    pub fn new(config: OpenAiEmbeddingConfig) -> Self {
        let metadata = ProviderMetadata {
            provider_id: "openai-compatible".into(),
            model_id: config.model.clone(),
            dimensions: config.dimensions,
            locality: ProviderLocality::Remote,
            max_data_level: 1,
            outbound_possible: true,
        };
        Self {
            metadata,
            config,
            client: ureq::Agent::new(),
        }
    }

    /// Create a provider using environment variables.
    pub fn from_env() -> Result<Self> {
        Ok(Self::new(OpenAiEmbeddingConfig::from_env()?))
    }

    fn embeddings_url(&self) -> String {
        let base = self.config.base_url.trim_end_matches('/');
        format!("{}/embeddings", base)
    }

    pub fn provider_error_reason() -> String {
        "embedding provider request failed; see provider configuration and upstream status".into()
    }
}

impl EmbeddingProvider for OpenAiEmbeddingProvider {
    fn metadata(&self) -> &ProviderMetadata {
        &self.metadata
    }

    fn embed(&self, text: &str, text_sha: &str) -> Result<Vec<f32>> {
        // `text_sha` is used for local audit/cache consistency; the actual text
        // must be sent to the remote API, but it is never logged locally.
        let _ = text_sha;

        let request = OpenAiEmbeddingsRequest {
            model: self.config.model.clone(),
            input: text.to_string(),
            dimensions: self.config.dimensions,
            encoding_format: "float".to_string(),
        };

        let url = self.embeddings_url();
        let response: OpenAiEmbeddingsResponse = self
            .client
            .post(&url)
            .set("Authorization", &format!("Bearer {}", self.config.api_key))
            .set("Content-Type", "application/json")
            .set("Accept", "application/json")
            .set(
                "User-Agent",
                "OpenLocus/0.1 (OpenAI-compatible research harness)",
            )
            .send_json(request)
            .map_err(|e| anyhow::anyhow!(e))
            .with_context(Self::provider_error_reason)?
            .into_json()
            .map_err(|e| anyhow::anyhow!(e))
            .context("failed to decode embedding provider response")?;

        let first = response
            .data
            .into_iter()
            .next()
            .context("embeddings response contained no data")?;

        if first.embedding.len() != self.metadata.dimensions {
            bail!(
                "embedding dimension mismatch: expected {}, got {}",
                self.metadata.dimensions,
                first.embedding.len()
            );
        }

        Ok(first.embedding)
    }
}

pub fn sanitize_provider_error(error: &anyhow::Error) -> String {
    let text = error.to_string();
    if text.contains("OPENLOCUS_") || text.contains("remote providers disabled") {
        text
    } else {
        OpenAiEmbeddingProvider::provider_error_reason()
    }
}

#[derive(Debug, Serialize)]
struct OpenAiEmbeddingsRequest {
    model: String,
    input: String,
    dimensions: usize,
    encoding_format: String,
}

#[derive(Debug, Deserialize)]
struct OpenAiEmbeddingsResponse {
    data: Vec<OpenAiEmbedding>,
}

#[derive(Debug, Deserialize)]
struct OpenAiEmbedding {
    embedding: Vec<f32>,
    #[allow(dead_code)]
    index: usize,
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn vars(overrides: &[(&str, &str)]) -> impl Fn(&str) -> Option<String> {
        let map: std::collections::HashMap<String, String> = overrides
            .iter()
            .map(|(k, v)| (k.to_string(), v.to_string()))
            .collect();
        move |key: &str| map.get(key).cloned()
    }

    #[test]
    fn config_blocks_without_allow_remote() {
        let err = OpenAiEmbeddingConfig::from_env_values(vars(&[])).unwrap_err();
        assert!(err.to_string().contains("OPENLOCUS_ALLOW_REMOTE"));
    }

    #[test]
    fn config_requires_all_vars() {
        let err = OpenAiEmbeddingConfig::from_env_values(vars(&[("OPENLOCUS_ALLOW_REMOTE", "1")]))
            .unwrap_err();
        assert!(err.to_string().contains("OPENLOCUS_EMBEDDING_BASE_URL"));
    }

    #[test]
    fn config_requires_valid_dimensions() {
        let err = OpenAiEmbeddingConfig::from_env_values(vars(&[
            ("OPENLOCUS_ALLOW_REMOTE", "1"),
            ("OPENLOCUS_EMBEDDING_BASE_URL", "https://api.example.com/v1"),
            ("OPENLOCUS_EMBEDDING_API_KEY", "sk-test"),
            ("OPENLOCUS_EMBEDDING_MODEL", "text-embedding-3-small"),
            ("OPENLOCUS_EMBEDDING_DIMENSIONS", "not-a-number"),
        ]))
        .unwrap_err();
        assert!(err.to_string().contains("OPENLOCUS_EMBEDDING_DIMENSIONS"));
    }

    #[test]
    fn config_parses_valid_env() {
        let config = OpenAiEmbeddingConfig::from_env_values(vars(&[
            ("OPENLOCUS_ALLOW_REMOTE", "1"),
            ("OPENLOCUS_EMBEDDING_BASE_URL", "https://api.example.com/v1"),
            ("OPENLOCUS_EMBEDDING_API_KEY", "sk-test"),
            ("OPENLOCUS_EMBEDDING_MODEL", "text-embedding-3-small"),
            ("OPENLOCUS_EMBEDDING_DIMENSIONS", "1536"),
        ]))
        .unwrap();

        assert_eq!(config.base_url, "https://api.example.com/v1");
        assert_eq!(config.api_key, "sk-test");
        assert_eq!(config.model, "text-embedding-3-small");
        assert_eq!(config.dimensions, 1536);
    }

    #[test]
    fn provider_metadata_reflects_config() {
        let config = OpenAiEmbeddingConfig {
            base_url: "https://api.example.com/v1".into(),
            api_key: "sk-test".into(),
            model: "text-embedding-3-small".into(),
            dimensions: 1536,
        };
        let provider = OpenAiEmbeddingProvider::new(config);
        let metadata = provider.metadata();
        assert_eq!(metadata.provider_id, "openai-compatible");
        assert_eq!(metadata.model_id, "text-embedding-3-small");
        assert_eq!(metadata.dimensions, 1536);
        assert_eq!(metadata.locality, ProviderLocality::Remote);
        assert!(metadata.outbound_possible);
    }

    #[test]
    fn embeddings_url_trims_trailing_slash() {
        let config = OpenAiEmbeddingConfig {
            base_url: "https://api.example.com/v1/".into(),
            api_key: "sk-test".into(),
            model: "text-embedding-3-small".into(),
            dimensions: 1536,
        };
        let provider = OpenAiEmbeddingProvider::new(config);
        assert_eq!(
            provider.embeddings_url(),
            "https://api.example.com/v1/embeddings"
        );
    }
}
