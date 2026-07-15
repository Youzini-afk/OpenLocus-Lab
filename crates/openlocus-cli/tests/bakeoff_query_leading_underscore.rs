use std::fs;
use std::path::Path;
use std::process::{Command, Output};

use serde_json::Value;

fn run_openlocus(root: &Path, args: &[&str]) -> Output {
    Command::new(env!("CARGO_BIN_EXE_openlocus"))
        .args(args)
        .env("OPENLOCUS_ALLOW_REMOTE", "0")
        .current_dir(root)
        .output()
        .expect("run OpenLocus CLI")
}

fn assert_success(output: &Output, operation: &str) {
    assert!(
        output.status.success(),
        "{operation} failed: stdout={} stderr={}",
        String::from_utf8_lossy(&output.stdout),
        String::from_utf8_lossy(&output.stderr),
    );
}

#[test]
fn bakeoff_query_bm25_accepts_leading_underscore_identifier() {
    let dir = tempfile::tempdir().expect("temporary source root");
    let root = dir.path();
    fs::write(
        root.join("sample.py"),
        "def public_symbol():\n    return 1\n\ndef _hidden_symbol():\n    return 2\n",
    )
    .expect("write synthetic source");

    let root_arg = root.to_str().expect("UTF-8 temporary path");
    let build = run_openlocus(
        root,
        &[
            "index",
            "build",
            "--source-root",
            root_arg,
            "--state-root",
            root_arg,
            "--chunk-strategy",
            "line",
            "--json",
        ],
    );
    assert_success(&build, "index build");

    let audit_dir = root.join(".openlocus").join("audit");
    fs::create_dir_all(&audit_dir).expect("create provider audit directory");
    fs::write(audit_dir.join("embeddings.jsonl"), b"").expect("write empty provider audit");

    let query = run_openlocus(
        root,
        &[
            "bakeoff-query",
            "context",
            "--source-root",
            root_arg,
            "--state-root",
            root_arg,
            "--query",
            "_hidden_symbol",
            "--components",
            "bm25",
            "--task-family",
            "symbol_lookup",
            "--max-results",
            "8",
            "--json",
        ],
    );
    assert_success(&query, "bakeoff query");

    let envelope: Value = serde_json::from_slice(&query.stdout).expect("parse bakeoff envelope");
    assert_eq!(envelope["success"], true);
    assert!(
        envelope["evidence_count"].as_u64().unwrap_or(0) > 0,
        "underscore-leading identifier should materialize current evidence"
    );
    let bm25 = envelope["receipts"]
        .as_array()
        .expect("receipt array")
        .iter()
        .find(|receipt| receipt["component"] == "bm25")
        .expect("BM25 receipt");
    assert_eq!(bm25["status"], "executed");
    assert_eq!(bm25["diagnostics"]["stale_hits_skipped"], 0);
    assert_eq!(bm25["diagnostics"]["invalid_hits_skipped"], 0);
}
