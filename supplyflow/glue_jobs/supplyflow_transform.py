import sys

from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql import Window
from pyspark.sql import functions as F


args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "SOURCE_BUCKET",
        "CURATED_BUCKET",
    ],
)


def get_optional_arg(name):
    flag = f"--{name}"
    if flag not in sys.argv:
        return None
    index = sys.argv.index(flag)
    return sys.argv[index + 1] if index + 1 < len(sys.argv) else None


redshift_tmp_dir = get_optional_arg("REDSHIFT_TMP_DIR")
redshift_jdbc_url = get_optional_arg("REDSHIFT_JDBC_URL")

sc = SparkContext()
glue_context = GlueContext(sc)
spark = glue_context.spark_session
job = Job(glue_context)
job.init(args["JOB_NAME"], args)

source_root = f"s3://{args['SOURCE_BUCKET']}/raw"
curated_root = f"s3://{args['CURATED_BUCKET']}/warehouse"

orders = spark.read.option("header", True).option("inferSchema", True).csv(f"{source_root}/orders/")
shipments = spark.read.option("header", True).option("inferSchema", True).csv(f"{source_root}/shipments/")
carriers = spark.read.option("header", True).option("inferSchema", True).csv(f"{source_root}/carriers/")
customers = spark.read.option("header", True).option("inferSchema", True).csv(f"{source_root}/customers/")
products = spark.read.option("header", True).option("inferSchema", True).csv(f"{source_root}/products/")
locations = spark.read.option("header", True).option("inferSchema", True).csv(f"{source_root}/locations/")

for column in ["order_date"]:
    orders = orders.withColumn(column, F.to_date(column))
for column in ["ship_date", "promised_delivery_date", "actual_delivery_date"]:
    shipments = shipments.withColumn(column, F.to_date(column))

dim_region = (
    locations.select(F.col("region").alias("region_name"))
    .union(customers.select(F.col("region").alias("region_name")))
    .distinct()
    .withColumn("region_key", F.row_number().over(Window.orderBy("region_name")))
    .select("region_key", "region_name")
)
dim_product_category = (
    products.select(F.col("category").alias("category_name"))
    .distinct()
    .withColumn("category_key", F.row_number().over(Window.orderBy("category_name")))
    .select("category_key", "category_name")
)
dim_service_level = spark.createDataFrame(
    [(1, "standard", 6), (2, "expedited", 3), (3, "same_day", 1)],
    ["service_level_key", "service_level", "promised_days"],
)

all_dates = (
    orders.select(F.col("order_date").alias("full_date"))
    .union(shipments.select(F.col("ship_date").alias("full_date")))
    .union(shipments.select(F.col("promised_delivery_date").alias("full_date")))
    .union(shipments.select(F.col("actual_delivery_date").alias("full_date")))
    .distinct()
)
dim_date = (
    all_dates.withColumn("date_key", F.date_format("full_date", "yyyyMMdd").cast("int"))
    .withColumn("year", F.year("full_date"))
    .withColumn("quarter", F.quarter("full_date"))
    .withColumn("month", F.month("full_date"))
    .withColumn("week", F.weekofyear("full_date"))
    .withColumn("day_of_month", F.dayofmonth("full_date"))
    .withColumn("is_weekend", F.dayofweek("full_date").isin([1, 7]))
    .select("date_key", "full_date", "year", "quarter", "month", "week", "day_of_month", "is_weekend")
)

dim_location = (
    locations.join(dim_region, locations.region == dim_region.region_name, "left")
    .select("location_id", "region_key", "city", "state", "latitude", "longitude", "location_type")
)
dim_customer = (
    customers.join(dim_region, customers.region == dim_region.region_name, "left")
    .select("customer_id", "customer_segment", "region_key", "priority_score")
)
dim_product = (
    products.join(dim_product_category, products.category == dim_product_category.category_name, "left")
    .select("product_id", "category_key", "product_name", "unit_cost", "unit_price", "weight_lb")
)
dim_carrier = carriers.select("carrier_id", "carrier_name", "mode", "contract_tier", "base_cost_per_mile")

fact_shipments = (
    shipments.join(orders, "order_id", "inner")
    .join(dim_service_level, "service_level", "left")
    .withColumn("order_date_key", F.date_format("order_date", "yyyyMMdd").cast("int"))
    .withColumn("ship_date_key", F.date_format("ship_date", "yyyyMMdd").cast("int"))
    .withColumn("promised_delivery_date_key", F.date_format("promised_delivery_date", "yyyyMMdd").cast("int"))
    .withColumn("actual_delivery_date_key", F.date_format("actual_delivery_date", "yyyyMMdd").cast("int"))
    .withColumn("delivery_days", F.greatest(F.datediff("actual_delivery_date", "ship_date"), F.lit(0)))
    .withColumn("late_days", F.greatest(F.datediff("actual_delivery_date", "promised_delivery_date"), F.lit(0)))
    .withColumn("on_time_flag", F.col("late_days") == 0)
    .withColumn("gross_profit", F.round(F.col("revenue") - F.col("product_cost") - F.col("shipping_cost"), 2))
    .withColumn("profit_margin", F.round(F.col("gross_profit") / F.col("revenue"), 4))
    .withColumn(
        "delivery_risk_score",
        F.least(
            F.lit(100),
            F.col("late_days") * F.lit(18)
            + F.when(~F.col("on_time_flag"), 25).otherwise(0)
            + F.when(F.col("damage_flag"), 30).otherwise(0)
            + F.when(F.col("service_level") == "same_day", 20)
            .when(F.col("service_level") == "expedited", 12)
            .otherwise(5),
        ),
    )
    .select(
        "shipment_id",
        "order_id",
        "customer_id",
        "product_id",
        "carrier_id",
        "origin_location_id",
        "destination_location_id",
        "order_date_key",
        "ship_date_key",
        "promised_delivery_date_key",
        "actual_delivery_date_key",
        "order_date",
        "ship_date",
        "promised_delivery_date",
        "actual_delivery_date",
        "service_level_key",
        "quantity",
        "distance_miles",
        "revenue",
        "product_cost",
        "shipping_cost",
        "gross_profit",
        "profit_margin",
        "delivery_days",
        "late_days",
        "on_time_flag",
        "damage_flag",
        "delivery_risk_score",
    )
)

warehouse_tables = {
    "dim_date": dim_date,
    "dim_region": dim_region,
    "dim_location": dim_location,
    "dim_customer": dim_customer,
    "dim_product_category": dim_product_category,
    "dim_product": dim_product,
    "dim_carrier": dim_carrier,
    "dim_service_level": dim_service_level,
    "fact_shipments": fact_shipments,
}


def write_redshift(table_name, dataframe):
    dataframe.write.format("io.github.spark_redshift_community.spark.redshift").option(
        "url", redshift_jdbc_url
    ).option("dbtable", f"analytics.{table_name}").option("tempdir", redshift_tmp_dir).option(
        "forward_spark_s3_credentials", "true"
    ).mode(
        "append"
    ).save()


for table_name, dataframe in warehouse_tables.items():
    dataframe.write.mode("overwrite").parquet(f"{curated_root}/{table_name}")
    if redshift_jdbc_url and redshift_tmp_dir:
        write_redshift(table_name, dataframe)

job.commit()
