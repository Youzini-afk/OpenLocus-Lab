use chrono::Utc;
use serde::{Deserialize, Serialize};
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::Path;

// ── TraceEvent ────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceEvent {
    pub trace_id: String,
    pub timestamp: String,
    pub event: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub input: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub output: Option<serde_json::Value>,
}

impl TraceEvent {
    pub fn new(event: impl Into<String>) -> Self {
        Self {
            trace_id: format!("tr-{}", Utc::now().timestamp_millis()),
            timestamp: Utc::now().to_rfc3339(),
            event: event.into(),
            input: None,
            output: None,
        }
    }

    pub fn with_trace_id(mut self, id: impl Into<String>) -> Self {
        self.trace_id = id.into();
        self
    }

    pub fn with_input(mut self, val: serde_json::Value) -> Self {
        self.input = Some(val);
        self
    }

    pub fn with_output(mut self, val: serde_json::Value) -> Self {
        self.output = Some(val);
        self
    }
}

/// Append a trace event as JSONL under `.openlocus/traces/trajectory-YYYYMMDD.jsonl`.
/// Creates the directory and file if they don't exist.
pub fn append_trace(root: &Path, event: &TraceEvent) -> anyhow::Result<()> {
    let traces_dir = root.join(".openlocus").join("traces");
    fs::create_dir_all(&traces_dir)?;

    let date_str = Utc::now().format("%Y%m%d").to_string();
    let filename = format!("trajectory-{}.jsonl", date_str);
    let path = traces_dir.join(&filename);

    let mut file = OpenOptions::new().create(true).append(true).open(&path)?;
    let line = serde_json::to_string(event)?;
    writeln!(file, "{}", line)?;
    Ok(())
}

// ── Tests ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn trace_event_serializes() {
        let ev = TraceEvent::new("retrieval_call")
            .with_input(serde_json::json!({"query": "auth"}))
            .with_output(serde_json::json!({"count": 3}));
        let json = serde_json::to_string(&ev).unwrap();
        assert!(json.contains("retrieval_call"));
        assert!(json.contains("auth"));
    }

    #[test]
    fn append_trace_creates_file() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let ev = TraceEvent::new("test_event");
        append_trace(root, &ev).unwrap();

        let date_str = Utc::now().format("%Y%m%d").to_string();
        let trace_file = root
            .join(".openlocus")
            .join("traces")
            .join(format!("trajectory-{}.jsonl", date_str));
        assert!(trace_file.exists());

        let content = fs::read_to_string(&trace_file).unwrap();
        let parsed: serde_json::Value = serde_json::from_str(content.trim()).unwrap();
        assert_eq!(parsed["event"], "test_event");
    }
}
