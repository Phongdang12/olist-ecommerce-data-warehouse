/*
Gold schema contract based on the supplied DDL.
This view is one row per order and supports analytics + a basic ML classifier.
It uses is_late as the target label and never includes is_late/delay_days as model features.

Caveats:
- A multi-seller order is represented by the lexicographically first seller_state/category
  for the compact order-level model. For production, use an order-item model instead.
- MAX(is_late) means an order is labelled late if any item is marked late.
- Confirm date_key is the purchase date in your Gold load procedure.
*/
IF SCHEMA_ID('dss') IS NULL EXEC('CREATE SCHEMA dss');
GO
CREATE OR ALTER VIEW dss.vw_dss_orders AS
WITH item_rows AS (
    SELECT
        f.order_id,
        d.full_date AS purchase_date,
        c.current_state AS customer_state,
        s.seller_state,
        p.category_name_en,
        f.order_status,
        CAST(f.price AS decimal(18,2)) AS price,
        CAST(f.freight_value AS decimal(18,2)) AS freight_value,
        f.delivery_days,
        f.delay_days,
        CAST(f.is_late AS int) AS is_late,
        CAST(f.review_score AS int) AS review_score
    FROM gold.fact_order_item AS f
    INNER JOIN gold.dim_date AS d ON d.date_key = f.date_key
    INNER JOIN gold.dim_customer AS c ON c.customer_key = f.customer_key
    INNER JOIN gold.dim_seller AS s ON s.seller_key = f.seller_key
    INNER JOIN gold.dim_product AS p ON p.product_key = f.product_key
),
order_agg AS (
    SELECT
        order_id,
        MIN(purchase_date) AS purchase_date,
        MAX(customer_state) AS customer_state,
        MAX(seller_state) AS seller_state,
        MAX(category_name_en) AS category_name_en,
        MAX(order_status) AS order_status,
        SUM(price) AS order_value,
        SUM(freight_value) AS freight_value,
        COUNT(*) AS item_count,
        MAX(delivery_days) AS delivery_days,
        MAX(delay_days) AS delay_days,
        MAX(is_late) AS is_late,
        MAX(review_score) AS review_score
    FROM item_rows
    GROUP BY order_id
)
SELECT
    order_id, purchase_date, customer_state, seller_state, category_name_en,
    order_status, order_value, freight_value, item_count, delivery_days,
    delay_days, is_late, review_score
FROM order_agg;
GO
