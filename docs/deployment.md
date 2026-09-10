# Azure deployment guide

## Prerequisites

- An Azure subscription and a resource group.
- Azure CLI with Bicep, or Azure Cloud Shell.
- Permission to create resource-group resources and role assignments.
- An Entra ID principal permitted to create the Azure SQL contained user for Data Factory.

## 1. Deploy the baseline

Copy `.env.example` values into your shell or CI secret store; do not commit them. Deploy the Bicep baseline with secure parameters:

```powershell
az deployment group create `
  --resource-group rg-realestate-dev `
  --template-file infra/main.bicep `
  --parameters namePrefix=<uniqueprefix> `
               sqlAdministratorLogin=<adminlogin> `
               sqlAdministratorPassword=<secure-password>
```

The baseline creates Storage containers, Data Factory with managed identity, Key Vault with RBAC, Log Analytics, Azure SQL Database, storage access for Data Factory, and diagnostic settings.

## 2. Configure private connectivity

The baseline keeps Azure SQL public network access disabled. In a production subscription, add an Azure Data Factory managed virtual network and private endpoints for Storage, Key Vault, and Azure SQL before enabling linked services.

## 3. Bootstrap Azure SQL

Run the SQL scripts in order:

1. `sql/001_azure_sql_schema.sql`
2. `sql/002_power_bi_marts.sql`
3. `sql/003_etl_publish_procedure.sql`

Then create a contained database user for the Data Factory managed identity and grant minimum read/write/execute permissions on `stg`, `core`, `mart`, and `etl`.

## 4. Publish Data Factory artifacts

Replace `{{storage_account}}`, `{{sql_server}}`, `{{database}}`, and `{{key_vault}}` in `adf/linkedServices/`. Import the linked services, datasets, and pipelines through Git integration or the Azure portal. Configure the Silver transformation as Mapping Data Flow or a SQL transformation that writes accepted rows to `stg` and rejected rows to `quarantine`.

## 5. Load and run

Upload source files to the `landing` container by entity, for example `landing/listings/listings.csv`. Trigger `pl_real_estate_master`, pass a snapshot date, then validate the ADF run, quarantine rate, and `mart` row counts before refreshing Power BI.

## 6. Connect Power BI

Use DirectQuery or import mode against `mart.vw_city_market` and `mart.vw_property_type`. Apply a least-privilege read-only database user or Entra group. Set scheduled refresh only after pipeline health checks are operational.
