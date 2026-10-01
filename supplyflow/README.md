# SupplyFlow Supply Chain Data Pipeline: S3 to Redshift Data Warehouse

## Introduction: Project Aim and Scope

The SupplyFlow cloud data pipeline is engineered as a portfolio-ready AWS analytics solution for scalable ingestion, transformation, and warehouse modeling of supply-chain and geospatial delivery data.

This architecture uses Amazon S3 as the secure staging and storage layer, AWS Lambda as the event-driven orchestration layer, AWS Glue with PySpark as the transformation engine, and Amazon Redshift as the analytical data warehouse.

The transformed data is consolidated into a nine-table snowflake-schema warehouse that supports profitability analysis, carrier performance monitoring, and delivery-risk dashboards in Power BI.

Data source: synthetic supply-chain and geospatial data generated locally for reproducible demos. The data model is designed so real CSV extracts from ERP, carrier, customer, product, and location systems can replace the synthetic files.

## Repository Structure and Code Organization

The repository is structured to clearly separate infrastructure, source data, ETL logic, DDL scripts, BI assets, and documentation for reproducibility.

```text
SupplyFlow_AWS_ETL/
|
|-- README.md                              # Project overview and replication guide
|
|-- infrastructure/
|   |-- 01_iam_roles.json                  # IAM role and policy reference template
|   |-- 02_redshift_vpc_config.json        # Redshift VPC/security group reference template
|
|-- source_data/                           # Folder for raw and metadata source files
|   |-- raw_data/                          # Original CSV extracts
|   |-- geojson/                           # Raw GeoJSON route input files
|   |-- metadata/                          # Mapping and lookup files
|
|-- etl_jobs/
|   |-- lambda_geojson_processor.py        # Lambda function for GeoJSON flattening into WKT
|   |-- lambda_s3_event_router.py          # Lambda function that starts Glue from S3 events
|   |-- glue_master_etl.py                 # PySpark ETL script for warehouse tables
|
|-- data_warehouse/
|   |-- ddl_snowflake_schema.sql           # CREATE TABLE scripts for all dimensions and facts
|
|-- bi_dashboards/
|   |-- PowerBI_Dashboard_Spec.md          # Power BI pages, measures, and drill-through design
|   |-- Dashboard.pdf                      # Power BI dashboard/report preview
|
|-- documentation/
|   |-- Project_Report.md                  # Final project report with architecture details
|   |-- Project_Report.pdf                 # PDF project report
|
|-- image/
|   |-- architecture_diagram.svg           # System architecture diagram
|   |-- architecture_diagram.png           # System architecture diagram image
|
|-- src/supplyflow/                        # Local generator, local ETL, validator, dashboard
|-- data/raw/                              # Generated raw demo data
|-- data/warehouse/                        # Local nine-table warehouse CSV output
|-- data/marts/                            # Dashboard-ready aggregate marts
```

## Data Warehouse Creation and Multidimensional Modeling

The data warehouse transforms flat operational files into an optimized OLAP structure for supply-chain analytics.

### Operational Database Source

The source layer represents operational CSV extracts:

- `orders`
- `shipments`
- `carriers`
- `customers`
- `products`
- `locations`

These files model high-volume order and shipment activity plus descriptive dimensions for carrier, product, customer, and geospatial location analysis.

### Multidimensional Model Target

The final Redshift snowflake schema contains eight dimension tables and one fact table:

- `dim_date`
- `dim_region`
- `dim_location`
- `dim_customer`
- `dim_product_category`
- `dim_product`
- `dim_carrier`
- `dim_service_level`
- `fact_shipments`

Foreign keys connect transactional shipment measures to descriptive attributes such as region, product category, carrier mode, service level, and date.

## Key Analytical Features

Snowflake hierarchy: `dim_region -> dim_location`, `dim_product_category -> dim_product`, and `dim_date -> fact_shipments` support multi-level analysis across geography, product mix, and time.

Geospatial integration: `dim_location` stores latitude and longitude so Power BI can map delivery risk, late shipment concentration, and regional performance.

Operational insights: the model supports profitability monitoring, carrier reliability scorecards, late-delivery alerts, damage-rate tracking, and shipment-level drill-through.

## AWS Architecture and Service Components

The pipeline is designed for a serverless AWS deployment with scalable compute and managed storage.

| Component | Role in Pipeline | Key Function |
|---|---|---|
| Amazon S3 | Data lake and staging layer | Stores raw CSV files and curated warehouse outputs |
| AWS Lambda | Event router | Starts the Glue ETL job when raw files land in S3 |
| AWS Glue Crawlers | Schema discovery | Catalogs raw and curated S3 datasets |
| AWS Glue ETL PySpark | Core transformation engine | Joins sources, calculates KPIs, and creates warehouse tables |
| Amazon Athena | Verification layer | Queries cataloged S3 tables for schema and data checks |
| Amazon Redshift | Data warehouse | Stores the final snowflake schema for analytics |
| Amazon CloudWatch | Monitoring and logging | Tracks Lambda and Glue execution logs |
| Power BI | Business intelligence layer | Provides executive, carrier, and delivery-risk dashboards |

## Step-by-Step Execution Guide

Follow these steps to replicate the SupplyFlow pipeline locally or in AWS.

### 1. Run the Local Demo

```bash
cd SupplyFlow_AWS_ETL
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dashboard]"
supplyflow-generate --rows 2500
supplyflow-curate
supplyflow-validate
streamlit run src/supplyflow/dashboard.py
```

### 2. Create IAM Roles and Permissions

Create IAM roles for Lambda, Glue, and Redshift access.

Use `infrastructure/01_iam_roles.json` as a reference for required S3, Glue, CloudWatch, and Redshift permissions.

### 3. Create S3 Buckets and Upload Data

Create buckets similar to:

- `supplyflow-raw`
- `supplyflow-curated`

Upload files into S3 folders such as:

- `raw/orders/`
- `raw/shipments/`
- `raw/carriers/`
- `raw/customers/`
- `raw/products/`
- `raw/locations/`

### 4. Deploy the Lambda Event Router

Deploy `etl_jobs/lambda_s3_event_router.py`.

Required environment variables:

- `GLUE_JOB_NAME`
- `CURATED_BUCKET`

Optional environment variables for direct Redshift writes:

- `REDSHIFT_TMP_DIR`
- `REDSHIFT_JDBC_URL`

### 5. Create and Run Glue Crawlers

Create a Glue database, then run crawlers on:

- the raw source folders
- the curated or warehouse output folders

Use Athena to verify the cataloged schema and row counts.

### 6. Create Redshift Data Warehouse

Provision Amazon Redshift or Redshift Serverless.

Execute:

```sql
data_warehouse/ddl_snowflake_schema.sql
```

This creates all eight dimensions and the shipment fact table.

### 7. Run the Glue ETL Job

Use `etl_jobs/glue_master_etl.py` as the master PySpark transformation job.

The job:

- extracts source data from S3
- creates date, region, product, service-level, carrier, customer, and location dimensions
- calculates shipment profitability and delivery risk
- writes warehouse outputs to S3
- optionally writes directly to Redshift through the Spark Redshift connector

### 8. Load Redshift

Use `sql/redshift_copy_examples.sql` to load Parquet outputs from S3 into Redshift if not using direct Glue-to-Redshift writes.

### 9. Build Power BI Dashboards

Use `bi_dashboards/PowerBI_Dashboard_Spec.md` to build the semantic model, DAX measures, pages, drill-through fields, and filters.

## Business Intelligence and Insights

The project concludes with a three-page dashboard design for different organizational levels.

Executive Overview: focuses on revenue, gross profit, margin, on-time rate, and delivery-risk KPIs. Insight: identify high-margin regions and product categories for strategic planning.

Carrier Performance: compares carriers by shipment volume, on-time rate, damage rate, delivery days, and shipping cost. Insight: optimize carrier contracts and route assignments.

Delivery Risk: maps regional delivery risk and highlights late or damaged shipments. Insight: detect service-level bottlenecks before they affect customer experience.

## End Result

SupplyFlow delivers a complete AWS-style data pipeline that ingests supply-chain source data, transforms it into a normalized Redshift snowflake schema, and supports interactive Power BI dashboards for profitability, carrier performance, and delivery-risk decision-making.

## Tools to Install

- Required for local build: Python 3.11 or newer
- Required for local dashboard: `pip install -e ".[dashboard]"`
- Optional for AWS deployment: AWS CLI, AWS account, S3, Lambda, Glue, IAM, Redshift
- Optional for BI delivery: Power BI Desktop or Power BI Service
- Optional for local Spark testing: Java 11 and `pip install -e ".[spark]"`

## Student-Safe AWS Option

To avoid accidental cloud charges, start with the local demo and read `STUDENT_SAFE_AWS_PLAN.md` before deploying anything to AWS.

Recommended path:

1. Run the full project locally.
2. Use AWS Educate or AWS Academy for free student cloud practice.
3. Set an AWS Budget alert before using a regular AWS account.
4. Avoid Redshift and repeated Glue jobs until you are ready to monitor and clean up resources.
