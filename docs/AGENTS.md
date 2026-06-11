# Agent usage guide for OpenLocus

Prefer OpenLocus commands when locating code facts:

```bash
openlocus read <path[:start-end]> --json
openlocus scan --json
openlocus search regex <pattern> --json
openlocus search text <query> --json
openlocus context-lite --write-files --json
```

Rules:

- Treat `EvidenceCore` as the stable contract.
- Do not treat summaries, LLM-derived views, or history as authoritative evidence.
- Prefer citation-backed spans over broad summaries.
- Use context-lite files for long logs and diagnostics instead of injecting them into prompts.
