use anyhow::{Context, Result, bail};
use chrono::Utc;
use clap::{Parser, Subcommand};
use openlocus_core::{ContextLitePack, Evidence, JsonOutput, Policy, TraceEvent, append_trace};
use openlocus_repo::read::read_file;
use openlocus_repo::scan::scan_repo;
use openlocus_repo::validate_path;
use openlocus_retrieval::regex_search::{regex_search, text_search};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Parser)]
#[command(
    name = "openlocus",
    version,
    about = "Code fact retrieval kernel for coding agents"
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Read a file or line range, returning Evidence
    Read {
        /// Path spec: e.g. README.md or src/main.rs:10-20
        path_spec: String,
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// Scan repo for file records
    Scan {
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// Search code
    Search {
        #[command(subcommand)]
        search_cmd: SearchCommands,
    },
    /// Validate citations
    Citations {
        #[command(subcommand)]
        citations_cmd: CitationsCommands,
    },
    /// Generate context-lite pack
    ContextLite {
        /// Write context files to .openlocus/context/
        #[arg(long)]
        write_files: bool,
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// Print version
    Version,
}

#[derive(Subcommand)]
pub enum SearchCommands {
    /// Search with a regex pattern
    Regex {
        /// Regex pattern
        pattern: String,
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
    /// Search with plain text query
    Text {
        /// Text query
        query: String,
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
}

#[derive(Subcommand)]
pub enum CitationsCommands {
    /// Validate a JSON file of citations
    Validate {
        /// Path to JSON file containing Evidence array or object with evidence field
        json_file: String,
        /// Output as JSON
        #[arg(long)]
        json: bool,
    },
}

#[derive(Debug, Serialize, Deserialize)]
struct CitationValidationResult {
    valid: Vec<Evidence>,
    invalid: Vec<InvalidCitation>,
    total: usize,
    valid_count: usize,
    invalid_count: usize,
}

#[derive(Debug, Serialize, Deserialize)]
struct InvalidCitation {
    evidence: Evidence,
    reason: String,
}

pub fn run() -> Result<()> {
    let cli = Cli::parse();
    let repo_root = discover_repo_root()?;

    let policy = Policy::load_from_repo(&repo_root);

    match cli.command {
        Commands::Read { path_spec, json } => {
            let evidence = read_file(&repo_root, &path_spec)?;
            trace_event(
                &repo_root,
                "read",
                serde_json::json!({"path_spec": path_spec}),
                serde_json::json!({"path": evidence.core.path}),
            );
            print_output(&evidence, json)
        }
        Commands::Scan { json } => {
            let records = scan_repo(&repo_root, &policy)?;
            trace_event(
                &repo_root,
                "scan",
                serde_json::json!({}),
                serde_json::json!({"file_count": records.len()}),
            );
            print_output(&records, json)
        }
        Commands::Search { search_cmd } => match search_cmd {
            SearchCommands::Regex { pattern, json } => {
                let records = scan_repo(&repo_root, &policy)?;
                let results = regex_search(&repo_root, &records, &pattern, 100)?;
                trace_event(
                    &repo_root,
                    "search_regex",
                    serde_json::json!({"pattern": pattern}),
                    serde_json::json!({"result_count": results.len()}),
                );
                print_output(&results, json)
            }
            SearchCommands::Text { query, json } => {
                let records = scan_repo(&repo_root, &policy)?;
                let results = text_search(&repo_root, &records, &query, 100)?;
                trace_event(
                    &repo_root,
                    "search_text",
                    serde_json::json!({"query": query}),
                    serde_json::json!({"result_count": results.len()}),
                );
                print_output(&results, json)
            }
        },
        Commands::Citations { citations_cmd } => match citations_cmd {
            CitationsCommands::Validate { json_file, json } => {
                let result = validate_citations(&repo_root, &json_file)?;
                trace_event(
                    &repo_root,
                    "citations_validate",
                    serde_json::json!({"file": json_file}),
                    serde_json::json!({
                        "total": result.total,
                        "valid_count": result.valid_count,
                        "invalid_count": result.invalid_count
                    }),
                );
                print_output(&result, json)
            }
        },
        Commands::ContextLite { write_files, json } => {
            let pack = build_context_lite(&repo_root, write_files)?;
            trace_event(
                &repo_root,
                "context_lite",
                serde_json::json!({"write_files": write_files}),
                serde_json::json!({"generated_files": pack.generated_files}),
            );
            print_output(&pack, json)
        }
        Commands::Version => {
            println!("openlocus {}", env!("CARGO_PKG_VERSION"));
            Ok(())
        }
    }
}

/// Discover repo root by walking up from CWD looking for .git directory.
fn discover_repo_root() -> Result<PathBuf> {
    let mut dir = std::env::current_dir()?;
    loop {
        if dir.join(".git").exists() || dir.join(".openlocus").exists() {
            return Ok(dir);
        }
        if !dir.pop() {
            // Fallback: use current directory
            return Ok(std::env::current_dir()?);
        }
    }
}

fn trace_event(root: &Path, event: &str, input: serde_json::Value, output: serde_json::Value) {
    let ev = TraceEvent::new(event).with_input(input).with_output(output);
    if let Err(e) = append_trace(root, &ev) {
        eprintln!("warning: failed to append trace: {}", e);
    }
}

fn print_output<T: Serialize>(val: &T, _json: bool) -> Result<()> {
    println!("{}", JsonOutput::to_json_pretty(val)?);
    Ok(())
}

/// Validate citations from a JSON file.
/// Accepts three input formats:
/// 1. A single Evidence object (not wrapped in array)
/// 2. An array of Evidence
/// 3. An object with an "evidence" field containing an array
fn validate_citations(repo_root: &Path, json_file: &str) -> Result<CitationValidationResult> {
    let content = fs::read_to_string(json_file)?;
    let trimmed = content.trim_start();

    let evidences: Vec<Evidence> = if trimmed.starts_with('[') {
        // Format 2: array of Evidence
        serde_json::from_str(&content)?
    } else if trimmed.starts_with('{') {
        let obj: serde_json::Value = serde_json::from_str(&content)?;
        if let Some(arr) = obj.get("evidence") {
            // Format 3: object with evidence field
            serde_json::from_value(arr.clone())?
        } else {
            // Format 1: single Evidence object (has path/content_sha fields)
            if obj.get("path").is_some() || obj.get("content_sha").is_some() {
                let single: Evidence = serde_json::from_value(obj)?;
                vec![single]
            } else {
                bail!("JSON object must be a single Evidence or have an 'evidence' field");
            }
        }
    } else {
        bail!("JSON must start with '{{' or '['");
    };

    let mut valid = Vec::new();
    let mut invalid = Vec::new();

    for ev in evidences {
        match validate_single_citation(repo_root, &ev) {
            Ok(()) => valid.push(ev),
            Err(reason) => invalid.push(InvalidCitation {
                evidence: ev,
                reason: reason.to_string(),
            }),
        }
    }

    let valid_count = valid.len();
    let invalid_count = invalid.len();
    let total = valid_count + invalid_count;

    Ok(CitationValidationResult {
        valid,
        invalid_count,
        valid_count,
        invalid,
        total,
    })
}

fn validate_single_citation(repo_root: &Path, evidence: &Evidence) -> Result<()> {
    // Validate line range basics
    if evidence.core.start_line == 0 {
        bail!("start_line must be >= 1, got 0");
    }
    if evidence.core.start_line > evidence.core.end_line {
        bail!(
            "start_line ({}) > end_line ({})",
            evidence.core.start_line,
            evidence.core.end_line
        );
    }

    let full_path = validate_path(repo_root, &evidence.core.path)?;

    if !full_path.exists() {
        bail!("path does not exist: {}", evidence.core.path);
    }

    if !full_path.is_file() {
        bail!("not a file: {}", evidence.core.path);
    }

    // Verify content_sha matches current file
    let current_sha = openlocus_repo::read::compute_content_sha(&full_path)?;
    if current_sha != evidence.core.content_sha {
        bail!(
            "content_sha mismatch: expected {}, got {}",
            evidence.core.content_sha,
            current_sha
        );
    }

    // Read file content for line-range and excerpt validation
    let content = std::fs::read_to_string(&full_path)
        .with_context(|| format!("failed to read {}", evidence.core.path))?;
    let lines: Vec<&str> = content.lines().collect();
    let total_lines = lines.len() as u64;

    // Validate end_line <= file line count
    if evidence.core.end_line > total_lines {
        bail!(
            "end_line ({}) exceeds file line count ({})",
            evidence.core.end_line,
            total_lines
        );
    }

    // If meta.excerpt exists, verify it matches the current line range content
    if let Some(ref meta) = evidence.meta
        && let Some(ref excerpt) = meta.excerpt
    {
        let start_idx = (evidence.core.start_line - 1) as usize;
        let end_idx = evidence.core.end_line as usize;
        let actual_excerpt = lines[start_idx..end_idx].join("\n");
        if excerpt != &actual_excerpt {
            bail!(
                "excerpt mismatch for {}:{}-{}: excerpt content does not match current file",
                evidence.core.path,
                evidence.core.start_line,
                evidence.core.end_line
            );
        }
    }

    Ok(())
}

/// Build a context-lite pack.
fn build_context_lite(repo_root: &Path, write_files: bool) -> Result<ContextLitePack> {
    let trace_id = format!("ctx-{}", Utc::now().timestamp_millis());
    let mut generated_files = Vec::new();

    if write_files {
        let ctx_dir = repo_root.join(".openlocus").join("context");
        fs::create_dir_all(&ctx_dir)?;

        // Write dirty-summary.json placeholder
        let dirty_summary_path = ctx_dir.join("dirty-summary.json");
        let dirty_summary = serde_json::json!({
            "repo_root": repo_root.to_string_lossy(),
            "timestamp": Utc::now().to_rfc3339(),
            "dirty_files": []
        });
        fs::write(
            &dirty_summary_path,
            serde_json::to_string_pretty(&dirty_summary)?,
        )?;
        generated_files.push(".openlocus/context/dirty-summary.json".into());

        // Write retrieval-latest.jsonl placeholder
        let retrieval_path = ctx_dir.join("retrieval-latest.jsonl");
        fs::write(&retrieval_path, "")?;
        generated_files.push(".openlocus/context/retrieval-latest.jsonl".into());
    }

    Ok(ContextLitePack {
        session_id: None,
        generated_files,
        diagnostics: None,
        dirty_summary: None,
        recent_reads: None,
        recent_edits: None,
        test_outputs: None,
        trace_id,
    })
}
