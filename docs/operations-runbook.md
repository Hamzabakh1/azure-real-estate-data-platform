# Operations runbook

## Healthy run

1. Expected sources are present in the landing container.
2. Copy activities succeed after no more than three retries.
3. Rejection rate stays below the agreed threshold (start at 2%).
4. Gold row counts reconcile to accepted Silver records.
5. Power BI refresh completes against the `mart` views.

## Alerts

Create Azure Monitor alerts for any failed pipeline, duration above the service-level objective, no successful master run in 26 hours, rejection rate above threshold, and Gold reconciliation mismatch.

## Recovery

1. Use the run ID to inspect Bronze inputs and ADF activity output.
2. Correct source data or a contract configuration; do not modify historical Bronze files.
3. Run again with a new run ID.
4. Reconcile Silver accepted/rejected counts and Gold rows before refreshing Power BI.
