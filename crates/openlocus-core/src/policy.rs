use serde::{Deserialize, Serialize};
use std::path::Path;

// ── Index policy ──────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexPolicy {
    #[serde(default = "default_include")]
    pub include: Vec<String>,
    #[serde(default = "default_exclude")]
    pub exclude: Vec<String>,
    #[serde(default)]
    pub include_gitignored: bool,
    #[serde(default)]
    pub index_generated: bool,
}

impl Default for IndexPolicy {
    fn default() -> Self {
        Self {
            include: default_include(),
            exclude: default_exclude(),
            include_gitignored: false,
            index_generated: false,
        }
    }
}

fn default_include() -> Vec<String> {
    vec!["**/*".into()]
}

fn default_exclude() -> Vec<String> {
    vec![
        ".git/**".into(),
        "target/**".into(),
        "node_modules/**".into(),
        "dist/**".into(),
        ".env*".into(),
        "**/*.pem".into(),
    ]
}

// ── Remote policy ─────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RemotePolicy {
    #[serde(default)]
    pub allow: bool,
    #[serde(default = "default_remote_mode")]
    pub default_mode: String,
    #[serde(default)]
    pub allowed_providers: Vec<String>,
    #[serde(default)]
    pub max_data_level: u8,
    #[serde(default)]
    pub allow_rerank: bool,
    #[serde(default)]
    pub allow_embedding: bool,
    #[serde(default)]
    pub allow_summary: bool,
}

impl Default for RemotePolicy {
    fn default() -> Self {
        Self {
            allow: false,
            default_mode: default_remote_mode(),
            allowed_providers: vec![],
            max_data_level: 0,
            allow_rerank: false,
            allow_embedding: false,
            allow_summary: false,
        }
    }
}

fn default_remote_mode() -> String {
    "local_only".into()
}

// ── Secrets policy ────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SecretsPolicy {
    #[serde(default = "default_true")]
    pub scan_before_remote: bool,
    #[serde(default = "default_true")]
    pub block_on_match: bool,
    #[serde(default = "default_true")]
    pub redact: bool,
}

impl Default for SecretsPolicy {
    fn default() -> Self {
        Self {
            scan_before_remote: true,
            block_on_match: true,
            redact: true,
        }
    }
}

fn default_true() -> bool {
    true
}

// ── Retention policy ──────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetentionPolicy {
    #[serde(default = "default_ttl")]
    pub local_index_ttl_days: u32,
    #[serde(default)]
    pub remote_cache: bool,
    #[serde(default)]
    pub telemetry: bool,
}

impl Default for RetentionPolicy {
    fn default() -> Self {
        Self {
            local_index_ttl_days: default_ttl(),
            remote_cache: false,
            telemetry: false,
        }
    }
}

fn default_ttl() -> u32 {
    90
}

// ── Policy (top-level) ────────────────────────────────────────────────

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct Policy {
    #[serde(default)]
    pub index: IndexPolicy,
    #[serde(default)]
    pub remote: RemotePolicy,
    #[serde(default)]
    pub secrets: SecretsPolicy,
    #[serde(default)]
    pub retention: RetentionPolicy,
}

impl Policy {
    /// Load policy from `.openlocus/policy.toml` under `root`, or return default.
    pub fn load_from_repo(root: &Path) -> Self {
        let policy_path = root.join(".openlocus").join("policy.toml");
        if policy_path.exists() {
            match std::fs::read_to_string(&policy_path) {
                Ok(content) => match toml::from_str(&content) {
                    Ok(policy) => return policy,
                    Err(e) => {
                        eprintln!(
                            "warning: failed to parse {}: {}; using defaults",
                            policy_path.display(),
                            e
                        );
                    }
                },
                Err(e) => {
                    eprintln!(
                        "warning: failed to read {}: {}; using defaults",
                        policy_path.display(),
                        e
                    );
                }
            }
        }
        Self::default()
    }
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn default_policy_is_sane() {
        let p = Policy::default();
        assert!(!p.remote.allow);
        assert_eq!(p.remote.default_mode, "local_only");
        assert!(p.secrets.scan_before_remote);
        assert_eq!(p.retention.local_index_ttl_days, 90);
        assert!(p.index.include.contains(&"**/*".to_string()));
    }

    #[test]
    fn policy_roundtrip_toml() {
        let p = Policy::default();
        let s = toml::to_string(&p).unwrap();
        let back: Policy = toml::from_str(&s).unwrap();
        assert_eq!(back.remote.default_mode, "local_only");
        assert_eq!(back.retention.local_index_ttl_days, 90);
    }

    #[test]
    fn load_from_missing_dir_returns_default() {
        let p = Policy::load_from_repo(Path::new("/tmp/no_such_dir_openlocus_test"));
        assert!(!p.remote.allow);
    }
}
