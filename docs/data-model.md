# Gold data model

```mermaid
erDiagram
  DIM_AGENCY ||--o{ DIM_PROPERTY : represents
  DIM_LOCATION ||--o{ FACT_LISTING_SNAPSHOT : locates
  DIM_PROPERTY ||--o{ FACT_LISTING_SNAPSHOT : snapshots
  DIM_PROPERTY ||--o{ FACT_TRANSACTION : sells
```

## Power BI marts

- `mart.vw_city_market`: inventory, active listings, average price, average price per square meter, transaction count, and average sale price by city and snapshot date.
- `mart.vw_property_type`: inventory, area, listing price, and price per square meter by property type and snapshot date.

Use one-way dimension-to-fact relationships in the semantic model. Keep source-of-truth transformations in ADF and Azure SQL; keep presentation measures in DAX.
