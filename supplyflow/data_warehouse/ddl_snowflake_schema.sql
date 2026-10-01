create schema if not exists analytics;

create table if not exists analytics.dim_date (
    date_key integer not null distkey sortkey,
    full_date date not null,
    year smallint not null,
    quarter smallint not null,
    month smallint not null,
    week smallint not null,
    day_of_month smallint not null,
    is_weekend boolean not null
);

create table if not exists analytics.dim_region (
    region_key integer not null,
    region_name varchar(60) not null,
    primary key (region_key)
);

create table if not exists analytics.dim_location (
    location_id varchar(20) not null distkey,
    region_key integer not null,
    city varchar(80) not null,
    state varchar(20) not null,
    latitude decimal(9,5),
    longitude decimal(9,5),
    location_type varchar(40),
    primary key (location_id)
);

create table if not exists analytics.dim_customer (
    customer_id varchar(20) not null distkey,
    customer_segment varchar(40) not null,
    region_key integer not null,
    priority_score smallint not null,
    primary key (customer_id)
);

create table if not exists analytics.dim_product_category (
    category_key integer not null,
    category_name varchar(80) not null,
    primary key (category_key)
);

create table if not exists analytics.dim_product (
    product_id varchar(20) not null distkey,
    category_key integer not null,
    product_name varchar(160) not null,
    unit_cost decimal(12,2) not null,
    unit_price decimal(12,2) not null,
    weight_lb decimal(10,2),
    primary key (product_id)
);

create table if not exists analytics.dim_carrier (
    carrier_id varchar(20) not null distkey,
    carrier_name varchar(120) not null,
    mode varchar(40) not null,
    contract_tier varchar(40) not null,
    base_cost_per_mile decimal(10,2) not null,
    primary key (carrier_id)
);

create table if not exists analytics.dim_service_level (
    service_level_key integer not null,
    service_level varchar(40) not null,
    promised_days smallint not null,
    primary key (service_level_key)
);

create table if not exists analytics.fact_shipments (
    shipment_id varchar(30) not null,
    order_id varchar(30) not null,
    customer_id varchar(20) not null distkey,
    product_id varchar(20) not null,
    carrier_id varchar(20) not null,
    origin_location_id varchar(20) not null,
    destination_location_id varchar(20) not null,
    order_date_key integer not null,
    ship_date_key integer not null,
    promised_delivery_date_key integer not null,
    actual_delivery_date_key integer not null,
    order_date date not null sortkey,
    ship_date date not null,
    promised_delivery_date date not null,
    actual_delivery_date date not null,
    service_level_key integer not null,
    quantity integer not null,
    distance_miles integer not null,
    revenue decimal(14,2) not null,
    product_cost decimal(14,2) not null,
    shipping_cost decimal(14,2) not null,
    gross_profit decimal(14,2) not null,
    profit_margin decimal(9,4) not null,
    delivery_days integer not null,
    late_days integer not null,
    on_time_flag boolean not null,
    damage_flag boolean not null,
    delivery_risk_score decimal(6,2) not null,
    primary key (shipment_id)
);

create or replace view analytics.v_carrier_performance as
select
    c.carrier_id,
    c.carrier_name,
    c.mode,
    count(*) as shipment_count,
    avg(f.delivery_days) as avg_delivery_days,
    avg(case when f.on_time_flag then 1.0 else 0.0 end) as on_time_rate,
    avg(case when f.damage_flag then 1.0 else 0.0 end) as damage_rate,
    sum(f.shipping_cost) as total_shipping_cost
from analytics.fact_shipments f
join analytics.dim_carrier c
    on f.carrier_id = c.carrier_id
group by 1, 2, 3;

create or replace view analytics.v_profitability as
select
    pc.category_name,
    r.region_name as destination_region,
    date_trunc('month', f.order_date) as order_month,
    sum(f.revenue) as revenue,
    sum(f.gross_profit) as gross_profit,
    avg(f.profit_margin) as avg_profit_margin
from analytics.fact_shipments f
join analytics.dim_product p
    on f.product_id = p.product_id
join analytics.dim_product_category pc
    on p.category_key = pc.category_key
join analytics.dim_location l
    on f.destination_location_id = l.location_id
join analytics.dim_region r
    on l.region_key = r.region_key
group by 1, 2, 3;

create or replace view analytics.v_delivery_risk as
select
    r.region_name as destination_region,
    sl.service_level,
    count(*) as shipment_count,
    avg(f.delivery_risk_score) as avg_delivery_risk_score,
    avg(case when f.on_time_flag then 0.0 else 1.0 end) as late_rate
from analytics.fact_shipments f
join analytics.dim_location l
    on f.destination_location_id = l.location_id
join analytics.dim_region r
    on l.region_key = r.region_key
join analytics.dim_service_level sl
    on f.service_level_key = sl.service_level_key
group by 1, 2;
