/*
---
Build Star Schema Procedure: Load Gold Layer (Silver -> Gold)
---
*/
USE OlistDW;
GO

CREATE OR ALTER PROCEDURE gold.load_gold AS
BEGIN

-- Xóa fact trước: các dim đang bị fact tham chiếu bằng khóa ngoại
DELETE FROM gold.fact_order_item;

PRINT '--- Processing table: gold.dim_date ---';
DELETE FROM gold.dim_date;

-- Khoảng ngày: trọn năm, từ năm của đơn đầu tiên đến năm của ngày giao / dự kiến giao muộn nhất
DECLARE @start_date DATE, @end_date DATE;
SELECT
    @start_date = DATEFROMPARTS(YEAR(MIN(order_purchase_timestamp)), 1, 1),
    @end_date   = DATEFROMPARTS(YEAR(MAX(v.dt)), 12, 31)
FROM silver.orders
CROSS APPLY (VALUES (order_purchase_timestamp),
                    (order_delivered_customer_date),
                    (order_estimated_delivery_date)) AS v(dt);


WITH dates AS (
    -- Dãy ngày liên tục, không bỏ sót ngày không có đơn
    SELECT @start_date AS dt
    UNION ALL
    SELECT DATEADD(DAY, 1, dt) FROM dates WHERE dt < @end_date
)


INSERT INTO gold.dim_date(
    date_key,
    full_date,
    day_of_month,
    day_of_week,
    day_name,
    is_weekend,
    week_of_year,
    month_num,
    month_name,
    year_month,
    quarter_num,
    quarter_name,
    year_num
)
SELECT
    YEAR(d.dt) * 10000 + MONTH(d.dt) * 100 + DAY(d.dt),
    d.dt,
    DAY(d.dt),
    w.dow,
    CHOOSE(w.dow, 'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'),
    CASE WHEN w.dow IN (6, 7) THEN 1 ELSE 0 END,
    DATEPART(ISO_WEEK, d.dt),
    MONTH(d.dt),
    CHOOSE(MONTH(d.dt), 'January','February','March','April','May','June',
                        'July','August','September','October','November','December'),
    CONVERT(CHAR(7), d.dt, 126),
    DATEPART(QUARTER, d.dt),
    CONCAT(YEAR(d.dt), '-Q', DATEPART(QUARTER, d.dt)),
    YEAR(d.dt)
FROM dates AS d
-- Thứ trong tuần cố định 1 = Thứ 2 ... 7 = Chủ nhật, không phụ thuộc SET DATEFIRST (1900-01-01 là Thứ 2)
CROSS APPLY (SELECT DATEDIFF(DAY, '19000101', d.dt) % 7 + 1 AS dow) AS w
OPTION (MAXRECURSION 0);



PRINT '--- Processing table: gold.dim_customer ---';
DELETE FROM gold.dim_customer;


INSERT INTO gold.dim_customer(
    customer_unique_id,
    customer_zip_code_prefix,
    current_city,
    current_state,
    current_region
)
SELECT
    customer_unique_id,
    customer_zip_code_prefix,
    customer_city ,
    customer_state ,
    customer_region
FROM (
    SELECT 
        c.customer_unique_id,
        c.customer_zip_code_prefix,
        c.customer_city ,
        c.customer_state ,
        c.customer_region ,
        ROW_NUMBER() OVER(PARTITION BY c.customer_unique_id ORDER BY o.order_purchase_timestamp DESC) AS rn

    FROM silver.customers c
    LEFT JOIN silver.orders o ON c.customer_id = o.customer_id
    WHERE c.customer_unique_id IS NOT NULL
) t
    
WHERE rn = 1;

PRINT '--- Processing table: gold.dim_seller ---';
DELETE FROM gold.dim_seller;

INSERT INTO gold.dim_seller(
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state,
    seller_region
)
SELECT
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state,
    seller_region
FROM(
    SELECT *,
        ROW_NUMBER() OVER(PARTITION BY seller_id ORDER BY seller_id) AS rn
    FROM silver.sellers
    WHERE seller_id IS NOT NULL
) t
WHERE rn = 1;


PRINT '--- Processing table: gold.dim_product ---';
DELETE FROM gold.dim_product;

INSERT INTO gold.dim_product(
    product_id,
    category_name_pt,
    category_name_en,
    name_length,
    description_length,
    photos_qty,
    weight_g,
    length_cm,
    height_cm,
    width_cm,
    volume_cm3,
    weight_class
)
SELECT
    product_id,
    product_category_name,
    product_category_name_english,
    product_name_length,
    product_description_length,
    product_photos_qty,
    product_weight_g,
    product_length_cm,
    product_height_cm,
    product_width_cm,
    product_length_cm * product_height_cm * product_width_cm,
    CASE 
        WHEN product_weight_g IS NULL THEN NULL
        WHEN product_weight_g < 1000 THEN 'light'
        WHEN product_weight_g >= 1000 AND product_weight_g < 5000 THEN 'medium'
        ELSE 'heavy'
    END
FROM(
    SELECT *,
        ROW_NUMBER() OVER(PARTITION BY product_id ORDER BY product_id) AS rn
    FROM silver.products
    WHERE product_id IS NOT NULL
) t
WHERE rn = 1;

PRINT '--- Processing table: gold.fact_order_items ---';

INSERT INTO gold.fact_order_item(
    order_id,
    order_item_id,
    date_key,
    customer_key,
    seller_key,
    product_key,
    delivery_city,
    delivery_state,
    delivery_region,
    order_status,
    price,
    freight_value,
    delivery_days,     -- NULL nếu chưa giao / bị hủy
    delay_days,     -- dương = trễ, âm = sớm
    is_late,
    review_score
)
SELECT 
    i.order_id,
    i.order_item_id,
    TRY_CONVERT(INT,FORMAT(o.order_purchase_timestamp,'yyyyMMdd')),
    dc.customer_key,
    s.seller_key,
    p.product_key,
    c.customer_city,
    c.customer_state,
    c.customer_region,
    o.order_status,
    i.price,
    i.freight_value,
    -- số ngày từ lúc đặt đến lúc khách nhận (NULL nếu chưa giao)
    DATEDIFF(DAY, o.order_purchase_timestamp, o.order_delivered_customer_date),
    -- số ngày trễ hẹn (NULL nếu chưa giao)
    DATEDIFF(DAY, o.order_estimated_delivery_date, o.order_delivered_customer_date),
    CASE
        
        WHEN o.order_delivered_customer_date IS NULL OR o.order_estimated_delivery_date IS NULL THEN NULL 
        WHEN DATEDIFF(DAY, o.order_estimated_delivery_date, o.order_delivered_customer_date) > 0 THEN 1
        ELSE 0
    END ,
    r.review_score
        
FROM silver.order_items i
JOIN silver.orders o ON i.order_id = o.order_id
JOIN silver.customers c ON o.customer_id = c.customer_id
JOIN gold.dim_seller s ON i.seller_id = s.seller_id
JOIN gold.dim_product p ON i.product_id = p.product_id
JOIN gold.dim_customer dc ON c.customer_unique_id = dc.customer_unique_id
LEFT JOIN (
     -- mỗi đơn chỉ lấy 1 review: review trả lời gần nhất
    SELECT order_id, review_score,
        ROW_NUMBER() OVER(PARTITION BY order_id ORDER BY review_creation_date DESC, review_answer_timestamp DESC) AS rn
    FROM silver.order_reviews
) r ON o.order_id = r.order_id AND r.rn = 1




END;
GO


EXEC gold.load_gold;