/*
==============================================================================
Test Script: Kiểm thử toàn bộ Data Warehouse (Bronze -> Silver -> Gold)
==============================================================================
Cách dùng:
    Chạy sau khi đã EXEC bronze.load_bronze, silver.load_silver, gold.load_gold.
    Kết quả: 1 bảng liệt kê từng test (PASS / FAIL) + 1 dòng tổng kết.

Nhóm test:
    1. Bronze  - số dòng khớp file CSV nguồn, không còn ký tự CR thừa
    2. Silver  - số dòng khớp bronze, chuyển kiểu không làm mất dữ liệu,
                 dữ liệu sạch (trim, miền giá trị hợp lệ)
    3. Gold    - số dòng dim/fact, khóa duy nhất, toàn vẹn tham chiếu,
                 dim_date liên tục, logic các cột tính toán, đối soát tổng tiền
==============================================================================
*/

USE OlistDW;
GO

SET NOCOUNT ON;

DROP TABLE IF EXISTS #test_result;
CREATE TABLE #test_result (
    test_id    INT IDENTITY(1,1),
    layer      NVARCHAR(10),
    test_name  NVARCHAR(200),
    expected   DECIMAL(38,2),
    actual     DECIMAL(38,2)
);


/* ============================================================================
   1. BRONZE
   ============================================================================ */

-- 1.1 Số dòng khớp với số bản ghi trong file CSV (không tính header)
INSERT INTO #test_result (layer, test_name, expected, actual)
SELECT 'bronze', N'orders: số dòng = CSV',               99441,  COUNT(*) FROM bronze.orders               UNION ALL
SELECT 'bronze', N'order_items: số dòng = CSV',          112650, COUNT(*) FROM bronze.order_items          UNION ALL
SELECT 'bronze', N'customers: số dòng = CSV',            99441,  COUNT(*) FROM bronze.customers            UNION ALL
SELECT 'bronze', N'sellers: số dòng = CSV',              3095,   COUNT(*) FROM bronze.sellers              UNION ALL
SELECT 'bronze', N'products: số dòng = CSV',             32951,  COUNT(*) FROM bronze.products             UNION ALL
SELECT 'bronze', N'category_translation: số dòng = CSV', 71,     COUNT(*) FROM bronze.category_translation UNION ALL
SELECT 'bronze', N'order_reviews: số dòng = CSV',        99224,  COUNT(*) FROM bronze.order_reviews;

-- 1.2 File CRLF đã load đúng ROWTERMINATOR: không còn CHAR(13) ở cột cuối
INSERT INTO #test_result (layer, test_name, expected, actual)
SELECT 'bronze', N'category_translation: không còn CHAR(13)', 0,
       COUNT(*) FROM bronze.category_translation WHERE product_category_name_english LIKE '%' + CHAR(13) + '%'
UNION ALL
SELECT 'bronze', N'order_reviews: không còn CHAR(13) ở cột cuối', 0,
       COUNT(*) FROM bronze.order_reviews WHERE review_answer_timestamp LIKE '%' + CHAR(13) + '%';


/* ============================================================================
   2. SILVER
   ============================================================================ */

-- 2.1 Số dòng silver = bronze (silver chỉ làm sạch, không thêm/bớt dòng)
INSERT INTO #test_result (layer, test_name, expected, actual)
SELECT 'silver', N'orders: số dòng = bronze',        (SELECT COUNT(*) FROM bronze.orders),        COUNT(*) FROM silver.orders        UNION ALL
SELECT 'silver', N'order_items: số dòng = bronze',   (SELECT COUNT(*) FROM bronze.order_items),   COUNT(*) FROM silver.order_items   UNION ALL
SELECT 'silver', N'customers: số dòng = bronze',     (SELECT COUNT(*) FROM bronze.customers),     COUNT(*) FROM silver.customers     UNION ALL
SELECT 'silver', N'sellers: số dòng = bronze',       (SELECT COUNT(*) FROM bronze.sellers),       COUNT(*) FROM silver.sellers       UNION ALL
SELECT 'silver', N'products: số dòng = bronze',      (SELECT COUNT(*) FROM bronze.products),      COUNT(*) FROM silver.products      UNION ALL
SELECT 'silver', N'order_reviews: số dòng = bronze', (SELECT COUNT(*) FROM bronze.order_reviews), COUNT(*) FROM silver.order_reviews;

-- 2.2 Chuyển kiểu không làm mất dữ liệu:
--     số giá trị khác rỗng ở bronze = số giá trị khác NULL ở silver
--     (nếu TRY_CONVERT thất bại, giá trị thành NULL và test sẽ FAIL)
INSERT INTO #test_result (layer, test_name, expected, actual)
SELECT 'silver', N'orders.order_purchase_timestamp: convert đủ',
       (SELECT COUNT(*) FROM bronze.orders WHERE TRIM(order_purchase_timestamp) <> ''),
       (SELECT COUNT(order_purchase_timestamp) FROM silver.orders)
UNION ALL
SELECT 'silver', N'orders.order_approved_at: convert đủ',
       (SELECT COUNT(*) FROM bronze.orders WHERE TRIM(order_approved_at) <> ''),
       (SELECT COUNT(order_approved_at) FROM silver.orders)
UNION ALL
SELECT 'silver', N'orders.order_delivered_carrier_date: convert đủ',
       (SELECT COUNT(*) FROM bronze.orders WHERE TRIM(order_delivered_carrier_date) <> ''),
       (SELECT COUNT(order_delivered_carrier_date) FROM silver.orders)
UNION ALL
SELECT 'silver', N'orders.order_delivered_customer_date: convert đủ',
       (SELECT COUNT(*) FROM bronze.orders WHERE TRIM(order_delivered_customer_date) <> ''),
       (SELECT COUNT(order_delivered_customer_date) FROM silver.orders)
UNION ALL
SELECT 'silver', N'orders.order_estimated_delivery_date: convert đủ',
       (SELECT COUNT(*) FROM bronze.orders WHERE TRIM(order_estimated_delivery_date) <> ''),
       (SELECT COUNT(order_estimated_delivery_date) FROM silver.orders)
UNION ALL
SELECT 'silver', N'order_items.shipping_limit_date: convert đủ',
       (SELECT COUNT(*) FROM bronze.order_items WHERE TRIM(shipping_limit_date) <> ''),
       (SELECT COUNT(shipping_limit_date) FROM silver.order_items)
UNION ALL
SELECT 'silver', N'order_items.price: convert đủ',
       (SELECT COUNT(*) FROM bronze.order_items WHERE TRIM(price) <> ''),
       (SELECT COUNT(price) FROM silver.order_items)
UNION ALL
SELECT 'silver', N'order_items.freight_value: convert đủ',
       (SELECT COUNT(*) FROM bronze.order_items WHERE TRIM(freight_value) <> ''),
       (SELECT COUNT(freight_value) FROM silver.order_items)
UNION ALL
SELECT 'silver', N'products.product_weight_g: convert đủ',
       (SELECT COUNT(*) FROM bronze.products WHERE TRIM(product_weight_g) <> ''),
       (SELECT COUNT(product_weight_g) FROM silver.products)
UNION ALL
SELECT 'silver', N'products.product_name_length: convert đủ',
       (SELECT COUNT(*) FROM bronze.products WHERE TRIM(product_name_lenght) <> ''),
       (SELECT COUNT(product_name_length) FROM silver.products)
UNION ALL
SELECT 'silver', N'order_reviews.review_score: convert đủ',
       (SELECT COUNT(*) FROM bronze.order_reviews WHERE TRIM(review_score) <> ''),
       (SELECT COUNT(review_score) FROM silver.order_reviews)
UNION ALL
SELECT 'silver', N'order_reviews.review_creation_date: convert đủ',
       (SELECT COUNT(*) FROM bronze.order_reviews WHERE TRIM(review_creation_date) <> ''),
       (SELECT COUNT(review_creation_date) FROM silver.order_reviews)
UNION ALL
SELECT 'silver', N'order_reviews.review_answer_timestamp: convert đủ',
       (SELECT COUNT(*) FROM bronze.order_reviews WHERE TRIM(review_answer_timestamp) <> ''),
       (SELECT COUNT(review_answer_timestamp) FROM silver.order_reviews);

-- 2.3 Khóa nghiệp vụ không NULL và không trùng
INSERT INTO #test_result (layer, test_name, expected, actual)
SELECT 'silver', N'orders.order_id: không trùng',       COUNT(*), COUNT(DISTINCT order_id)    FROM silver.orders    UNION ALL
SELECT 'silver', N'customers.customer_id: không trùng', COUNT(*), COUNT(DISTINCT customer_id) FROM silver.customers UNION ALL
SELECT 'silver', N'sellers.seller_id: không trùng',     COUNT(*), COUNT(DISTINCT seller_id)   FROM silver.sellers   UNION ALL
SELECT 'silver', N'products.product_id: không trùng',   COUNT(*), COUNT(DISTINCT product_id)  FROM silver.products  UNION ALL
SELECT 'silver', N'order_items (order_id, order_item_id): không trùng', COUNT(*),
       (SELECT COUNT(*) FROM (SELECT DISTINCT order_id, order_item_id FROM silver.order_items) x) FROM silver.order_items;

-- 2.4 Dữ liệu sạch và miền giá trị hợp lệ
INSERT INTO #test_result (layer, test_name, expected, actual)
SELECT 'silver', N'customers: city/state không còn khoảng trắng thừa', 0,
       COUNT(*) FROM silver.customers
       WHERE DATALENGTH(customer_city) <> DATALENGTH(TRIM(customer_city))
          OR DATALENGTH(customer_state) <> DATALENGTH(TRIM(customer_state))
UNION ALL
SELECT 'silver', N'customers: state đúng 2 ký tự', 0,
       COUNT(*) FROM silver.customers WHERE LEN(customer_state) <> 2
UNION ALL
SELECT 'silver', N'customers: region không NULL (mọi bang đều được map)', 0,
       COUNT(*) FROM silver.customers WHERE customer_region IS NULL
UNION ALL
SELECT 'silver', N'sellers: region không NULL (mọi bang đều được map)', 0,
       COUNT(*) FROM silver.sellers WHERE seller_region IS NULL
UNION ALL
SELECT 'silver', N'customers: zip code đủ 5 ký tự', 0,
       COUNT(*) FROM silver.customers WHERE LEN(customer_zip_code_prefix) <> 5
UNION ALL
SELECT 'silver', N'orders: order_status là chữ thường', 0,
       COUNT(*) FROM silver.orders WHERE order_status COLLATE Latin1_General_CS_AS <> LOWER(order_status)
UNION ALL
SELECT 'silver', N'order_items: price > 0', 0,
       COUNT(*) FROM silver.order_items WHERE price <= 0
UNION ALL
SELECT 'silver', N'order_items: freight_value >= 0', 0,
       COUNT(*) FROM silver.order_items WHERE freight_value < 0
UNION ALL
SELECT 'silver', N'order_reviews: review_score trong khoảng 1-5', 0,
       COUNT(*) FROM silver.order_reviews WHERE review_score NOT BETWEEN 1 AND 5
UNION ALL
SELECT 'silver', N'products: category_name_english không NULL', 0,
       COUNT(*) FROM silver.products WHERE product_category_name_english IS NULL
UNION ALL
SELECT 'silver', N'products: category_name_english không còn CHAR(13)', 0,
       COUNT(*) FROM silver.products WHERE product_category_name_english LIKE '%' + CHAR(13) + '%'
UNION ALL
SELECT 'silver', N'products: sản phẩm không danh mục -> ''unknown''',
       (SELECT COUNT(*) FROM silver.products WHERE product_category_name IS NULL),
       (SELECT COUNT(*) FROM silver.products WHERE product_category_name_english = 'unknown');

-- 2.5 Toàn vẹn tham chiếu giữa các bảng silver
INSERT INTO #test_result (layer, test_name, expected, actual)
SELECT 'silver', N'order_items -> orders: không mồ côi', 0,
       COUNT(*) FROM silver.order_items i WHERE NOT EXISTS (SELECT 1 FROM silver.orders o WHERE o.order_id = i.order_id)
UNION ALL
SELECT 'silver', N'order_items -> products: không mồ côi', 0,
       COUNT(*) FROM silver.order_items i WHERE NOT EXISTS (SELECT 1 FROM silver.products p WHERE p.product_id = i.product_id)
UNION ALL
SELECT 'silver', N'order_items -> sellers: không mồ côi', 0,
       COUNT(*) FROM silver.order_items i WHERE NOT EXISTS (SELECT 1 FROM silver.sellers s WHERE s.seller_id = i.seller_id)
UNION ALL
SELECT 'silver', N'orders -> customers: không mồ côi', 0,
       COUNT(*) FROM silver.orders o WHERE NOT EXISTS (SELECT 1 FROM silver.customers c WHERE c.customer_id = o.customer_id)
UNION ALL
SELECT 'silver', N'order_reviews -> orders: không mồ côi', 0,
       COUNT(*) FROM silver.order_reviews r WHERE NOT EXISTS (SELECT 1 FROM silver.orders o WHERE o.order_id = r.order_id);


/* ============================================================================
   3. GOLD
   ============================================================================ */

-- 3.1 Số dòng dimension = số khóa nghiệp vụ khác nhau ở silver
INSERT INTO #test_result (layer, test_name, expected, actual)
SELECT 'gold', N'dim_customer: số dòng = số customer_unique_id',
       (SELECT COUNT(DISTINCT customer_unique_id) FROM silver.customers), COUNT(*) FROM gold.dim_customer
UNION ALL
SELECT 'gold', N'dim_seller: số dòng = số seller_id',
       (SELECT COUNT(DISTINCT seller_id) FROM silver.sellers), COUNT(*) FROM gold.dim_seller
UNION ALL
SELECT 'gold', N'dim_product: số dòng = số product_id',
       (SELECT COUNT(DISTINCT product_id) FROM silver.products), COUNT(*) FROM gold.dim_product
UNION ALL
SELECT 'gold', N'fact_order_item: số dòng = silver.order_items (đúng grain)',
       (SELECT COUNT(*) FROM silver.order_items), COUNT(*) FROM gold.fact_order_item;

-- 3.2 Khóa duy nhất
INSERT INTO #test_result (layer, test_name, expected, actual)
SELECT 'gold', N'dim_customer.customer_unique_id: không trùng', COUNT(*), COUNT(DISTINCT customer_unique_id) FROM gold.dim_customer UNION ALL
SELECT 'gold', N'dim_seller.seller_id: không trùng',            COUNT(*), COUNT(DISTINCT seller_id)          FROM gold.dim_seller   UNION ALL
SELECT 'gold', N'dim_product.product_id: không trùng',          COUNT(*), COUNT(DISTINCT product_id)         FROM gold.dim_product  UNION ALL
SELECT 'gold', N'dim_date.date_key: không trùng',               COUNT(*), COUNT(DISTINCT date_key)           FROM gold.dim_date;

-- 3.3 Toàn vẹn tham chiếu fact -> dim
INSERT INTO #test_result (layer, test_name, expected, actual)
SELECT 'gold', N'fact -> dim_date: không mồ côi', 0,
       COUNT(*) FROM gold.fact_order_item f WHERE NOT EXISTS (SELECT 1 FROM gold.dim_date d WHERE d.date_key = f.date_key)
UNION ALL
SELECT 'gold', N'fact -> dim_customer: không mồ côi', 0,
       COUNT(*) FROM gold.fact_order_item f WHERE NOT EXISTS (SELECT 1 FROM gold.dim_customer d WHERE d.customer_key = f.customer_key)
UNION ALL
SELECT 'gold', N'fact -> dim_seller: không mồ côi', 0,
       COUNT(*) FROM gold.fact_order_item f WHERE NOT EXISTS (SELECT 1 FROM gold.dim_seller d WHERE d.seller_key = f.seller_key)
UNION ALL
SELECT 'gold', N'fact -> dim_product: không mồ côi', 0,
       COUNT(*) FROM gold.fact_order_item f WHERE NOT EXISTS (SELECT 1 FROM gold.dim_product d WHERE d.product_key = f.product_key);

-- 3.4 dim_date: liên tục, đúng định dạng, đúng thứ trong tuần
INSERT INTO #test_result (layer, test_name, expected, actual)
SELECT 'gold', N'dim_date: không thiếu ngày (liên tục từ MIN đến MAX)',
       DATEDIFF(DAY, MIN(full_date), MAX(full_date)) + 1, COUNT(*) FROM gold.dim_date
UNION ALL
SELECT 'gold', N'dim_date: phủ hết ngày mua hàng', 0,
       COUNT(*) FROM silver.orders o
       WHERE NOT EXISTS (SELECT 1 FROM gold.dim_date d WHERE d.full_date = CAST(o.order_purchase_timestamp AS DATE))
UNION ALL
SELECT 'gold', N'dim_date: date_key = yyyymmdd của full_date', 0,
       COUNT(*) FROM gold.dim_date WHERE date_key <> CAST(CONVERT(CHAR(8), full_date, 112) AS INT)
UNION ALL
SELECT 'gold', N'dim_date: 2017-11-24 là Friday (day_of_week = 5)', 1,
       COUNT(*) FROM gold.dim_date WHERE full_date = '2017-11-24' AND day_of_week = 5 AND day_name = 'Friday'
UNION ALL
SELECT 'gold', N'dim_date: is_weekend khớp Saturday/Sunday', 0,
       COUNT(*) FROM gold.dim_date
       WHERE is_weekend <> CASE WHEN day_name IN ('Saturday', 'Sunday') THEN 1 ELSE 0 END;

-- 3.5 Logic các cột tính toán trong fact / dim
INSERT INTO #test_result (layer, test_name, expected, actual)
SELECT 'gold', N'fact: delivery_days >= 0', 0,
       COUNT(*) FROM gold.fact_order_item WHERE delivery_days < 0
UNION ALL
SELECT 'gold', N'fact: is_late khớp với delay_days', 0,
       COUNT(*) FROM gold.fact_order_item
       WHERE (is_late = 1 AND delay_days <= 0)
          OR (is_late = 0 AND delay_days > 0)
          OR (is_late IS NULL AND delay_days IS NOT NULL)
          OR (is_late IS NOT NULL AND delay_days IS NULL)
UNION ALL
SELECT 'gold', N'fact: date_key = ngày mua hàng của đơn', 0,
       COUNT(*) FROM gold.fact_order_item f
       JOIN silver.orders o ON o.order_id = f.order_id
       WHERE f.date_key <> CAST(CONVERT(CHAR(8), o.order_purchase_timestamp, 112) AS INT)
UNION ALL
SELECT 'gold', N'fact: review_score có ở mọi đơn đã được review', 0,
       COUNT(*) FROM gold.fact_order_item f
       WHERE f.review_score IS NULL
         AND EXISTS (SELECT 1 FROM silver.order_reviews r WHERE r.order_id = f.order_id)
UNION ALL
SELECT 'gold', N'dim_product: weight_class NULL <=> weight_g NULL', 0,
       COUNT(*) FROM gold.dim_product
       WHERE (weight_class IS NULL AND weight_g IS NOT NULL)
          OR (weight_class IS NOT NULL AND weight_g IS NULL)
UNION ALL
SELECT 'gold', N'dim_product: volume_cm3 = dài x cao x rộng', 0,
       COUNT(*) FROM gold.dim_product WHERE volume_cm3 <> length_cm * height_cm * width_cm;

-- 3.6 Đối soát tổng tiền: gold không làm thừa/thiếu tiền so với silver
INSERT INTO #test_result (layer, test_name, expected, actual)
SELECT 'gold', N'fact: SUM(price) = silver.order_items',
       (SELECT SUM(price) FROM silver.order_items), SUM(price) FROM gold.fact_order_item
UNION ALL
SELECT 'gold', N'fact: SUM(freight_value) = silver.order_items',
       (SELECT SUM(freight_value) FROM silver.order_items), SUM(freight_value) FROM gold.fact_order_item;


/* ============================================================================
   KẾT QUẢ
   ============================================================================ */

SELECT
    test_id,
    layer,
    test_name,
    expected,
    actual,
    CASE WHEN expected = actual THEN 'PASS' ELSE 'FAIL' END AS status
FROM #test_result
ORDER BY CASE WHEN expected = actual THEN 1 ELSE 0 END, test_id;   -- test FAIL hiện lên đầu

SELECT
    COUNT(*)                                            AS total_tests,
    SUM(CASE WHEN expected = actual THEN 1 ELSE 0 END)  AS passed,
    SUM(CASE WHEN expected <> actual THEN 1 ELSE 0 END) AS failed,
    CASE WHEN SUM(CASE WHEN expected <> actual THEN 1 ELSE 0 END) = 0
         THEN N'ALL TESTS PASSED'
         ELSE N'CÓ TEST FAIL - xem bảng kết quả phía trên'
    END                                                 AS summary
FROM #test_result;
