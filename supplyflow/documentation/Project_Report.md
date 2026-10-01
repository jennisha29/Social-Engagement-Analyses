# SupplyFlow Project Report

## Project Aim and Scope

SupplyFlow is an AWS-style serverless data engineering project that demonstrates how supply-chain and geospatial delivery data can be transformed into a governed analytical warehouse.

The pipeline ingests raw operational files from an Amazon S3 landing zone, routes object-created events through AWS Lambda, transforms the data with AWS Glue PySpark, and loads a normalized snowflake schema into Amazon Redshift. The final warehouse supports Power BI dashboards for profitability, carrier performance, and delivery-risk analysis.

## Source Data

The project includes a local synthetic data generator so the pipeline can be demonstrated without external credentials or paid cloud resources.

Generated source entities:

- orders
- shipments
- carriers
- customers
- products
- locations

The location data includes region, state, city, latitude, and longitude fields to support geospatial dashboarding.

## Data Architecture

The architecture follows a medallion-style data flow:

1. Raw zone: source-aligned CSV files land in S3.
2. Transformation zone: Glue reads raw files, standardizes fields, generates warehouse keys, and calculates business KPIs.
3. Warehouse zone: dimensional tables and fact tables are written to S3 as Redshift-ready outputs.
4. Analytics zone: Redshift hosts the snowflake schema and Power BI consumes the model.

## Snowflake Schema

The warehouse contains eight dimension tables and one fact table.

| Table | Purpose |
|---|---|
| `dim_date` | Calendar attributes for order, ship, promised, and actual delivery dates |
| `dim_region` | Normalized regional geography |
| `dim_location` | Warehouse and destination location attributes with latitude/longitude |
| `dim_customer` | Customer segment and priority information |
| `dim_product_category` | Product category hierarchy |
| `dim_product` | Product attributes, price, cost, and weight |
| `dim_carrier` | Carrier name, transportation mode, contract tier, and base cost |
| `dim_service_level` | Standard, expedited, and same-day SLA definitions |
| `fact_shipments` | Shipment transactions, profitability metrics, delivery metrics, and risk score |

## Transformation Logic

The ETL job calculates:

- `gross_profit = revenue - product_cost - shipping_cost`
- `profit_margin = gross_profit / revenue`
- `delivery_days = actual_delivery_date - ship_date`
- `late_days = max(actual_delivery_date - promised_delivery_date, 0)`
- `on_time_flag = late_days == 0`
- `delivery_risk_score` from late days, damage flag, and service-level urgency

## AWS Service Design

| AWS Service | Function |
|---|---|
| Amazon S3 | Stores raw and curated data zones |
| AWS Lambda | Starts Glue jobs from raw-object S3 events |
| AWS Glue | Runs PySpark transformation jobs and can catalog S3 datasets |
| Amazon Athena | Verifies cataloged raw and curated data |
| Amazon Redshift | Hosts the final analytical warehouse |
| Amazon CloudWatch | Captures execution logs and operational monitoring |
| Power BI | Visualizes warehouse metrics for business users |

## Replication Steps

1. Create S3 raw and curated buckets.
2. Upload source CSV files under `raw/<entity>/`.
3. Deploy the Lambda event router from `etl_jobs/lambda_s3_event_router.py`.
4. Configure the Lambda environment with `GLUE_JOB_NAME` and `CURATED_BUCKET`.
5. Create Glue crawlers for the raw and warehouse S3 folders.
6. Create Redshift or Redshift Serverless.
7. Run `data_warehouse/ddl_snowflake_schema.sql`.
8. Run the Glue job from `etl_jobs/glue_master_etl.py`.
9. Load warehouse Parquet files with `sql/redshift_copy_examples.sql` or write directly from Glue.
10. Build Power BI reports from `bi_dashboards/PowerBI_Dashboard_Spec.md`.

## Local Validation Results

The local pipeline produces:

- 99 date rows
- 5 regions
- 32 locations
- 250 customers
- 5 product categories
- 40 products
- 6 carriers
- 3 service levels
- 2,500 fact shipment rows

It also produces dashboard marts for carrier performance, delivery risk, profitability by region/category, and shipment-level drill-through.

## Business Intelligence Outcomes

Executive stakeholders can monitor revenue, gross profit, margin, and regional profitability.

Operations teams can compare carriers by on-time delivery, damage rate, average delivery days, and shipping cost.

Logistics analysts can identify high-risk regions, service-level bottlenecks, late shipments, and shipment exceptions requiring follow-up.

## End Result

SupplyFlow demonstrates a complete AWS data pipeline from S3 ingestion through serverless transformation and Redshift warehousing, ending in Power BI dashboards that support proactive supply-chain decision-making.
