# OpenLocus

OpenLocus is a local-first but not local-only code fact retrieval kernel for coding agents.

The current research implementation follows the evidence-gated roadmap in `openlocus-research-design.md`:

```text
R0 Research Harness -> R1 Local Evidence Kernel -> R2 Retrieval Bakeoff -> R3 Storage Bakeoff -> ...
```

Early invariant:

```text
EvidenceCore = path + line range + content_sha + score + why + channels
```

All intelligent or experimental layers must bottom out in source-backed evidence.

## Initial CLI targets

```bash
cargo run -p openlocus-cli -- read README.md:1-20 --json
cargo run -p openlocus-cli -- scan --json
cargo run -p openlocus-cli -- search regex "EvidenceCore" --json
cargo run -p openlocus-cli -- context-lite --write-files --json
```
