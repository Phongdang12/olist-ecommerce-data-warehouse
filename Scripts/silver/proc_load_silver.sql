/*
---
Process Procedure: Load Silver Layer (Bronze -> Silver)
---
*/


USE OlistDW;
GO

CREATE OR ALTER PROCEDURE silver.load_silver AS
BEGIN

PRINT '--- Processing table: silver.orders ---';
TRUNCATE TABLE silver.orders;

INSERT INTO silver.orders(
    order_id,
    customer_id,
    order_status,
    order_purchase_timestamp,
    order_approved_at,
    order_delivered_carrier_date,
    order_delivered_customer_date,
    order_estimated_delivery_date
)
SELECT
    TRIM(order_id),
    TRIM(customer_id),
    LOWER(TRIM(order_status)),
    TRY_CONVERT(DATETIME2(0), NULLIF(TRIM(order_purchase_timestamp),''), 120),
    TRY_CONVERT(DATETIME2(0), NULLIF(TRIM(order_approved_at),''), 120),
    TRY_CONVERT(DATETIME2(0), NULLIF(TRIM(order_delivered_carrier_date),''), 120),
    TRY_CONVERT(DATETIME2(0), NULLIF(TRIM(order_delivered_customer_date),''), 120),
    TRY_CONVERT(DATETIME2(0), NULLIF(TRIM(REPLACE(order_estimated_delivery_date,CHAR(13),'')),''), 120)
FROM bronze.orders;

PRINT '--- Processing table: silver.order_items ---';
TRUNCATE TABLE silver.order_items;

INSERT INTO silver.order_items(
    order_id,
    order_item_id,
    product_id,
    seller_id,
    shipping_limit_date,
    price,
    freight_value
)
SELECT
    TRIM(order_id),
    TRY_CONVERT(INT, NULLIF(TRIM(order_item_id),'')),
    TRIM(product_id),
    TRIM(seller_id),
    TRY_CONVERT(DATETIME2(0), NULLIF(TRIM(shipping_limit_date),''), 120),
    TRY_CONVERT(DECIMAL(10,2), NULLIF(TRIM(price),'')),
    TRY_CONVERT(DECIMAL(10,2), NULLIF(TRIM(REPLACE(freight_value,CHAR(13),'')),''))
FROM bronze.order_items;

PRINT '--- Processing table: silver.customers ---';
TRUNCATE TABLE silver.customers;

INSERT INTO silver.customers(
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state,
    customer_region
)
SELECT
    TRIM(customer_id),
    TRIM(customer_unique_id),
    RIGHT('00000' + TRIM(customer_zip_code_prefix), 5) AS customer_zip_code_prefix,
    LOWER(TRIM(customer_city)) AS customer_city,
    UPPER(TRIM(REPLACE(customer_state,CHAR(13),''))) AS customer_state,
    CASE
        WHEN customer_state IN ('AC','AP','AM','PA','RO','RR','TO') THEN 'Norte'
        WHEN customer_state IN ('AL','BA','CE','MA','PB','PE','PI','RN','SE') THEN 'Nordeste'
        WHEN customer_state IN ('DF','GO','MT','MS') THEN 'Centro-Oeste'
        WHEN customer_state IN ('ES','MG','RJ','SP') THEN 'Sudeste'
        WHEN customer_state IN ('PR','RS','SC') THEN 'Sul'
        ELSE NULL
    END AS customer_region
FROM bronze.customers;


PRINT '--- Processing table: silver.sellers ---';
TRUNCATE TABLE silver.sellers;
INSERT INTO silver.sellers(
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state,
    seller_region
)
SELECT
    TRIM(seller_id),
    RIGHT('00000' + TRIM(seller_zip_code_prefix), 5) AS seller_zip_code_prefix,
    LOWER(TRIM(seller_city)) AS seller_city,
    UPPER(TRIM(REPLACE(seller_state,CHAR(13),''))) AS seller_state,
    CASE
        WHEN seller_state IN ('AC','AP','AM','PA','RO','RR','TO') THEN 'Norte'
        WHEN seller_state IN ('AL','BA','CE','MA','PB','PE','PI','RN','SE') THEN 'Nordeste'
        WHEN seller_state IN ('DF','GO','MT','MS') THEN 'Centro-Oeste'
        WHEN seller_state IN ('ES','MG','RJ','SP') THEN 'Sudeste'
        WHEN seller_state IN ('PR','RS','SC') THEN 'Sul'
        ELSE NULL
    END AS seller_region
FROM bronze.sellers;

PRINT '--- Processing table: silver.products ---';
TRUNCATE TABLE silver.products;

INSERT INTO silver.products(
    product_id,
    product_category_name,
    product_category_name_english,
    product_name_length,
    product_description_length,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm
)
SELECT
    TRIM(p.product_id),
    NULLIF(TRIM(p.product_category_name), '') AS product_category_name,
    COALESCE(NULLIF(TRIM(REPLACE(pct.product_category_name_english,CHAR(13),'')), ''),
             NULLIF(TRIM(p.product_category_name), ''),
             'unknown') AS product_category_name_english,
    TRY_CONVERT(INT, TRY_CONVERT(FLOAT, NULLIF(TRIM(p.product_name_lenght), ''))) AS product_name_length,
    TRY_CONVERT(INT, TRY_CONVERT(FLOAT, NULLIF(TRIM(p.product_description_lenght), ''))) AS product_description_length,
    TRY_CONVERT(INT, TRY_CONVERT(FLOAT, NULLIF(TRIM(p.product_photos_qty), ''))) AS product_photos_qty,
    TRY_CONVERT(INT, TRY_CONVERT(FLOAT, NULLIF(TRIM(p.product_weight_g), ''))) AS product_weight_g,
    TRY_CONVERT(INT, TRY_CONVERT(FLOAT, NULLIF(TRIM(p.product_length_cm), ''))) AS product_length_cm,
    TRY_CONVERT(INT, TRY_CONVERT(FLOAT, NULLIF(TRIM(p.product_height_cm), ''))) AS product_height_cm,
    TRY_CONVERT(INT, TRY_CONVERT(FLOAT, NULLIF(TRIM(p.product_width_cm), ''))) AS product_width_cm
FROM bronze.products AS p
LEFT JOIN bronze.category_translation AS pct
    ON TRIM(p.product_category_name) = TRIM(pct.product_category_name);



PRINT '--- Processing table: silver.order_reviews ---';
TRUNCATE TABLE silver.order_reviews;

INSERT INTO silver.order_reviews(
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_creation_date,
    review_answer_timestamp
)
SELECT
    TRIM(review_id),
    TRIM(order_id),
    TRY_CONVERT(TINYINT, NULLIF(TRIM(review_score), '')),
    NULLIF(TRIM(review_comment_title), '') AS review_comment_title,
    NULLIF(TRIM(review_comment_message), '') AS review_comment_message,
    TRY_CONVERT(DATETIME2(0), NULLIF(TRIM(review_creation_date), ''), 120),
    TRY_CONVERT(DATETIME2(0), NULLIF(TRIM(REPLACE(review_answer_timestamp,CHAR(13),'')), ''), 120)
FROM bronze.order_reviews;

END;

GO


EXEC silver.load_silver;