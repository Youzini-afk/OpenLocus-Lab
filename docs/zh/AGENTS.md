# Agent usage guide for OpenLocus

> 中文译本待补充。The full Chinese translation is pending.
> 这是同名文件的占位符：保留英文原文，方便未来翻译对照。

## English source / 英文原文

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

