# Architecture decisions

The platform turns fragmented listing, agency, and transaction data into governed analytical marts. It prioritizes traceability, recoverability, least-privilege access, and BI usability.

![Architecture](../assets/architecture.svg)

| Layer | Service | Responsibility | Contract |
|---|---|---|---|
| Landing | Azure Storage | Receive source files unchanged | Source filename, timestamp, format |
| Bronze | Azure Storage | Preserve immutable source snapshots | `entity/ingest_date/run_id/file` |
| Silver | ADF Mapping Data Flow or SQL transformation | Normalize, deduplicate, validate, quarantine | Conformed agency, listing, transaction records |
| Gold | Azure SQL Database | Publish dimensions, facts, and semantic marts | Idempotent business tables |
| Consumption | Power BI | Monitor market KPIs and drill-through | Read-only `mart` views |

## Security

- Data Factory uses a system-assigned managed identity.
- Storage shared-key and public blob access are disabled in Bicep.
- Key Vault is only for optional third-party API or SFTP credentials; no secrets belong in Git or pipeline JSON.
- Azure SQL public network access is disabled by default; private endpoints are required before production use.
- ADF pipeline, activity, and trigger events are routed to Log Analytics.

## Failure path

Rejected records include the source row, violated rule, reason, and original payload in `quarantine/run_id=.../rejected_records.csv`. A failed run records status and error context without overwriting prior Bronze evidence.
