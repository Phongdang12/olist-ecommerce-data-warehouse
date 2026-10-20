
/*
==============================================================================
DDL Script: Create Bronze Tables
==============================================================================

*/

USE OlistDW;
GO

DROP TABLE IF EXISTS bronze.orders;
CREATE TABLE bronze.orders (
    order_id                       NVARCHAR(50),
    customer_id                    NVARCHAR(50),
    order_status                   NVARCHAR(30),
    order_purchase_timestamp       NVARCHAR(30),
    order_approved_at              NVARCHAR(30),
    order_delivered_carrier_date   NVARCHAR(30),
    order_delivered_customer_date  NVARCHAR(30),
    order_estimated_delivery_date  NVARCHAR(30)
);

DROP TABLE IF EXISTS bronze.order_items;
CREATE TABLE bronze.order_items (
    order_id             NVARCHAR(50),
    order_item_id        NVARCHAR(10),
    product_id           NVARCHAR(50),
    seller_id            NVARCHAR(50),
    shipping_limit_date  NVARCHAR(30),
    price                NVARCHAR(20),
    freight_value        NVARCHAR(20)
);

DROP TABLE IF EXISTS bronze.customers;
CREATE TABLE bronze.customers (
    customer_id               NVARCHAR(50),
    customer_unique_id        NVARCHAR(50),
    customer_zip_code_prefix  NVARCHAR(10),
    customer_city             NVARCHAR(100),
    customer_state            NVARCHAR(5)
);

DROP TABLE IF EXISTS bronze.sellers;
CREATE TABLE bronze.sellers (
    seller_id               NVARCHAR(50),
    seller_zip_code_prefix  NVARCHAR(10),
    seller_city             NVARCHAR(100),
    seller_state            NVARCHAR(5)
);

-- Lưu ý: tên cột gốc trong CSV bị sai chính tả "lenght", giữ nguyên ở bronze
DROP TABLE IF EXISTS bronze.products;
CREATE TABLE bronze.products (
    product_id                  NVARCHAR(50),
    product_category_name       NVARCHAR(100),
    product_name_lenght         NVARCHAR(10),
    product_description_lenght  NVARCHAR(10),
    product_photos_qty          NVARCHAR(10),
    product_weight_g            NVARCHAR(20),
    product_length_cm           NVARCHAR(20),
    product_height_cm           NVARCHAR(20),
    product_width_cm            NVARCHAR(20)
);

DROP TABLE IF EXISTS bronze.category_translation;
CREATE TABLE bronze.category_translation (
    product_category_name          NVARCHAR(100),
    product_category_name_english  NVARCHAR(100)
);

DROP TABLE IF EXISTS bronze.order_reviews;
CREATE TABLE bronze.order_reviews (
    review_id                NVARCHAR(50),
    order_id                 NVARCHAR(50),
    review_score             NVARCHAR(5),
    review_comment_title     NVARCHAR(200),
    review_comment_message   NVARCHAR(1000),
    review_creation_date     NVARCHAR(30),
    review_answer_timestamp  NVARCHAR(30)
);
GO

PRINT N'Đã tạo 7 bảng bronze.';
