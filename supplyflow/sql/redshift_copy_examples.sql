copy analytics.dim_date
from 's3://supplyflow-curated/warehouse/dim_date/'
iam_role 'arn:aws:iam::<account-id>:role/redshift-spectrum-s3-read-role'
format as parquet;

copy analytics.dim_region
from 's3://supplyflow-curated/warehouse/dim_region/'
iam_role 'arn:aws:iam::<account-id>:role/redshift-spectrum-s3-read-role'
format as parquet;

copy analytics.dim_location
from 's3://supplyflow-curated/warehouse/dim_location/'
iam_role 'arn:aws:iam::<account-id>:role/redshift-spectrum-s3-read-role'
format as parquet;

copy analytics.dim_customer
from 's3://supplyflow-curated/warehouse/dim_customer/'
iam_role 'arn:aws:iam::<account-id>:role/redshift-spectrum-s3-read-role'
format as parquet;

copy analytics.dim_product_category
from 's3://supplyflow-curated/warehouse/dim_product_category/'
iam_role 'arn:aws:iam::<account-id>:role/redshift-spectrum-s3-read-role'
format as parquet;

copy analytics.dim_product
from 's3://supplyflow-curated/warehouse/dim_product/'
iam_role 'arn:aws:iam::<account-id>:role/redshift-spectrum-s3-read-role'
format as parquet;

copy analytics.dim_carrier
from 's3://supplyflow-curated/warehouse/dim_carrier/'
iam_role 'arn:aws:iam::<account-id>:role/redshift-spectrum-s3-read-role'
format as parquet;

copy analytics.dim_service_level
from 's3://supplyflow-curated/warehouse/dim_service_level/'
iam_role 'arn:aws:iam::<account-id>:role/redshift-spectrum-s3-read-role'
format as parquet;

copy analytics.fact_shipments
from 's3://supplyflow-curated/warehouse/fact_shipments/'
iam_role 'arn:aws:iam::<account-id>:role/redshift-spectrum-s3-read-role'
format as parquet;
