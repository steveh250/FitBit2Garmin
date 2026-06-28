# Non-Functional Requirements (ISO/IEC 25010)

One section per ISO 25010 quality characteristic. Each NFR is numbered,
measurable, and traceable to the build standard or to the project's documented
design decisions.

## Status legend

`Met` · `Partial` · `Not Met` · `Not Applicable`

| ID | Characteristic | Requirement (measurable) | Traceability | Status |
| --- | --- | --- | --- | --- |
| NFR-1 | **Functional Suitability** | All FR-1…FR-17 behaviours produce output matching Garmin's documented import format; verified by sample conversions. | docs/FR.md, docs/TEST-CASES.md | Met |
| NFR-2 | **Performance Efficiency** | Converts a multi-year single-user export in well under a minute on commodity hardware; memory bounded by aggregating to one float per day, not retaining raw records. | Standard §Performance | Met |
| NFR-3 | **Compatibility** | Output CSVs are accepted by Garmin Connect's Activities and Body importers; input tolerates Fitbit JSON, comma-CSV, and tab-CSV. | docs/ARCHITECTURE.md (data formats) | Met |
| NFR-4 | **Interaction Capability (Usability)** | CLI provides `--help`, sensible defaults (`--timezone America/Vancouver`), progress/warning messages, and a post-run spot-check reminder. | docs/DEPLOY.md | Met |
| NFR-5 | **Reliability** | A single malformed file or row never aborts a run; missing metric folders degrade gracefully to 0 with a warning. | FR-8, FR-10 | Met |
| NFR-6 | **Security** | Operates only on local files the user owns; no network, no credentials, no secret storage, no code execution of input data. | docs/ARCHITECTURE.md (auth: none) | Met |
| NFR-7 | **Maintainability** | Pure standard-library code; small, single-responsibility functions; tunable assumptions isolated as named module constants (`DISTANCE_UNIT_TO_KM`, alias maps). | docs/ARCHITECTURE.md (function inventory) | Met |
| NFR-8 | **Portability** | Runs on any OS with Python 3.9+ and a tz database; no platform-specific calls or external services. | docs/DEPLOY.md (prerequisites) | Met |
| NFR-9 | **Safety** (ISO 25010:2023) | Read-only on source data; output is written to a user-specified directory and never overwrites the Fitbit export. | docs/ARCHITECTURE.md (filesystem tiers) | Met |
| NFR-10 | **Correctness of Distance unit** | Distance must convert to the true real-world km value. | docs/FR.md FR-7 | Partial — meters assumption unverified against the Fitbit app |
| NFR-11 | **Test automation coverage** | Automated regression suite covering FRs/NFRs. | docs/TEST-CASES.md | Not Met — verification is currently manual |
| NFR-12 | **Scalability / multi-tenancy** | Concurrent/multi-user serving. | — | Not Applicable — single-user offline CLI |
| NFR-13 | **Availability / uptime** | Service uptime targets. | — | Not Applicable — no running service |
