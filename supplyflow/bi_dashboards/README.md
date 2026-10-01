# SupplyFlow Power BI Assets

This folder follows the same structure as a final BI handoff folder.

- `PowerBI_Dashboard_Spec.md`: dashboard pages, DAX measures, relationships, filters, and drill-through fields.
- `Dashboard.pdf`: generated dashboard/report preview for portfolio review.

A real `.pbix` file must be created in Power BI Desktop by connecting to either:

- local CSV outputs in `data/warehouse/` and `data/marts/`
- Amazon Redshift tables created from `data_warehouse/ddl_snowflake_schema.sql`

Recommended final Power BI filename:

- `SupplyFlow_Analytics.pbix`
