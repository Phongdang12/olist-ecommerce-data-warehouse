/*
=====================================================================
 DDL: Silver Layer
=====================================================================
*/
USE OlistDW;
GO
 
-- orders
DROP TABLE IF EXISTS silver.orders;
CREATE TABLE silver.orders (
    order_id                       NVARCHAR(50),
    customer_id                    NVARCHAR(50),
    order_status                   NVARCHAR(20),
    order_purchase_timestamp       DATETIME2(0),
    order_approved_at              DATETIME2(0),
    order_delivered_carrier_date   DATETIME2(0),
    order_delivered_customer_date  DATETIME2(0),
    order_estimated_delivery_date  DATETIME2(0),
    dwh_create_date                DATETIME2(0) DEFAULT SYSDATETIME()
);

-- order_items
DROP TABLE IF EXISTS silver.order_items;
CREATE TABLE silver.order_items (
    order_id             NVARCHAR(50),
    order_item_id        INT,
    product_id           NVARCHAR(50),
    seller_id            NVARCHAR(50),
    shipping_limit_date  DATETIME2(0),
    price                DECIMAL(10,2),
    freight_value        DECIMAL(10,2),
    dwh_create_date      DATETIME2(0) DEFAULT SYSDATETIME()
);

-- customers
DROP TABLE IF EXISTS silver.customers;
CREATE TABLE silver.customers (
    customer_id               NVARCHAR(50),
    customer_unique_id        NVARCHAR(50),
    customer_zip_code_prefix  NVARCHAR(10),
    customer_city             NVARCHAR(100),
    customer_state            NVARCHAR(5),
    customer_region           NVARCHAR(20),   -- cột tính thêm: Norte/Nordeste/Centro-Oeste/Sudeste/Sul
    dwh_create_date           DATETIME2(0) DEFAULT SYSDATETIME()
);

-- sellers
DROP TABLE IF EXISTS silver.sellers;
CREATE TABLE silver.sellers (
    seller_id               NVARCHAR(50),
    seller_zip_code_prefix  NVARCHAR(10),
    seller_city             NVARCHAR(100),
    seller_state            NVARCHAR(5),
    seller_region           NVARCHAR(20),   -- cột tính thêm: Norte/Nordeste/Centro-Oeste/Sudeste/Sul
    dwh_create_date           DATETIME2(0) DEFAULT SYSDATETIME()
);


-- Lưu ý: tên cột gốc trong CSV bị sai chính tả "lenght"
-- products
DROP TABLE IF EXISTS silver.products;
CREATE TABLE silver.products (
    product_id                  NVARCHAR(50),
    product_category_name       NVARCHAR(100),
    product_category_name_english  NVARCHAR(100),   -- cột gộp thêm
    product_name_length            INT,             -- sửa "lenght" -> "length"
    product_description_length     INT,             -- sửa "lenght" -> "length"
    product_photos_qty             INT,
    product_weight_g               INT,
    product_length_cm              INT,
    product_height_cm              INT,
    product_width_cm               INT,
    dwh_create_date                DATETIME2(0) DEFAULT SYSDATETIME()
);

-- order_reviews
DROP TABLE IF EXISTS silver.order_reviews;
CREATE TABLE silver.order_reviews (
    review_id                NVARCHAR(50),
    order_id                 NVARCHAR(50),
    review_score             TINYINT,
    review_comment_title     NVARCHAR(4000),
    review_comment_message   NVARCHAR(4000),
    review_creation_date     DATETIME2(0),
    review_answer_timestamp  DATETIME2(0),
    dwh_create_date          DATETIME2(0) DEFAULT SYSDATETIME()
);

GO

PRINT N'Đã tạo 6 bảng silver.';
