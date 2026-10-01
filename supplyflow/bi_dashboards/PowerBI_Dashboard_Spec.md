# SupplyFlow Power BI Dashboard Spec

## Pages

### Executive Overview

- KPI cards: revenue, gross profit, average margin, on-time delivery rate, average delivery-risk score.
- Weekly revenue and gross-profit trend.
- Profitability matrix by region and product category.
- Top at-risk lanes by destination region and service level.

### Carrier Performance

- Carrier scorecard with shipment count, on-time rate, damage rate, average delivery days, and cost per mile.
- Drill-through from carrier to shipment-level exceptions.
- Conditional formatting for late rate and damage rate thresholds.

### Delivery Risk

- Regional delivery-risk heatmap using latitude and longitude from `dim_location`.
- Service-level comparison for same-day, expedited, and standard shipments.
- Shipment exception table sorted by `delivery_risk_score`.

## DAX Measures

```DAX
Revenue = SUM(fact_shipments[revenue])

Gross Profit = SUM(fact_shipments[gross_profit])

Gross Margin % = DIVIDE([Gross Profit], [Revenue])

On-Time Rate =
AVERAGEX(
    fact_shipments,
    IF(fact_shipments[on_time_flag], 1, 0)
)

Late Shipment Rate = 1 - [On-Time Rate]

Average Delivery Risk = AVERAGE(fact_shipments[delivery_risk_score])

Cost Per Mile =
DIVIDE(
    SUM(fact_shipments[shipping_cost]),
    SUM(fact_shipments[distance_miles])
)
```

## Data Model

- `fact_shipments[carrier_id]` to `dim_carrier[carrier_id]`
- `fact_shipments[customer_id]` to `dim_customer[customer_id]`
- `fact_shipments[product_id]` to `dim_product[product_id]`
- `dim_product[category_key]` to `dim_product_category[category_key]`
- `fact_shipments[destination_location_id]` to `dim_location[location_id]`
- `dim_location[region_key]` to `dim_region[region_key]`
- `fact_shipments[service_level_key]` to `dim_service_level[service_level_key]`
- `fact_shipments[order_date_key]` to `dim_date[date_key]`

## Drill-through Fields

- `carrier_id`
- `dim_region[region_name]`
- `dim_service_level[service_level]`
- `product_id`
- `shipment_id`

## Recommended Filters

- Date range
- Region
- Carrier
- Product category
- Service level
- Customer segment
