/*
=====================================================================
 DDL: Gold Layer (Star Schema)
---------------------------------------------------------------------
 - 4 dimension: dim_date, dim_customer, dim_seller, dim_product
 - 1 fact     : fact_order_item
   Grain: 1 dòng = 1 sản phẩm trong 1 đơn hàng
 - Dim dùng surrogate key tự tăng (identity), riêng dim_date dùng
   date_key dạng yyyymmdd
 - Fact dùng khóa chính kép (order_id, order_item_id) = grain
=====================================================================
*/
USE OlistDW;
GO

-- Xóa theo thứ tự: fact trước, dim sau
DROP TABLE IF EXISTS gold.fact_order_item;
DROP TABLE IF EXISTS gold.dim_date;
DROP TABLE IF EXISTS gold.dim_customer;
DROP TABLE IF EXISTS gold.dim_seller;
DROP TABLE IF EXISTS gold.dim_product;
GO

-- dim_date
CREATE TABLE gold.dim_date (
    date_key        int           NOT NULL,   -- yyyymmdd, ví dụ 20171124
    full_date       date          NOT NULL,
    day_of_month    tinyint       NOT NULL,
    day_of_week     tinyint       NOT NULL,   -- 1 = thứ 2 ... 7 = chủ nhật
    day_name        nvarchar(20)  NOT NULL,
    is_weekend      bit           NOT NULL,
    week_of_year    tinyint       NOT NULL,
    month_num       tinyint       NOT NULL,
    month_name      nvarchar(20)  NOT NULL,
    year_month      char(7)       NOT NULL,   -- 2017-11
    quarter_num     tinyint       NOT NULL,
    quarter_name    char(7)       NOT NULL,   -- 2017-Q4
    year_num        smallint      NOT NULL,
    CONSTRAINT pk_dim_date PRIMARY KEY (date_key)
);

-- dim_customer
CREATE TABLE gold.dim_customer (
    customer_key              int IDENTITY(1,1) NOT NULL,
    customer_unique_id        nvarchar(50)  NOT NULL,
    customer_zip_code_prefix  nvarchar(10)  NULL,
    current_city             nvarchar(100) NULL,
    current_state            nvarchar(2)   NULL,
    current_region           nvarchar(20)  NULL,
    CONSTRAINT pk_dim_customer PRIMARY KEY (customer_key),
    CONSTRAINT uk_dim_customer UNIQUE (customer_unique_id)
);

-- dim_seller
CREATE TABLE gold.dim_seller (
    seller_key              int IDENTITY(1,1) NOT NULL,
    seller_id               nvarchar(50)  NOT NULL,
    seller_zip_code_prefix  nvarchar(10)  NULL,
    seller_city             nvarchar(100) NULL,
    seller_state            nvarchar(2)   NULL,
    seller_region           nvarchar(20)  NULL,
    CONSTRAINT pk_dim_seller PRIMARY KEY (seller_key),
    CONSTRAINT uk_dim_seller UNIQUE (seller_id)
);

-- dim_product
CREATE TABLE gold.dim_product (
    product_key         int IDENTITY(1,1) NOT NULL,
    product_id          nvarchar(50)  NOT NULL,
    category_name_pt    nvarchar(100) NULL,
    category_name_en    nvarchar(100) NOT NULL,   -- không có danh mục -> 'unknown'
    name_length         int           NULL,
    description_length  int           NULL,
    photos_qty          int           NULL,
    weight_g            int           NULL,
    length_cm           int           NULL,
    height_cm           int           NULL,
    width_cm            int           NULL,
    volume_cm3          int           NULL,       -- dài x cao x rộng
    weight_class        nvarchar(10)  NULL,       -- light / medium / heavy
    CONSTRAINT pk_dim_product PRIMARY KEY (product_key),
    CONSTRAINT uk_dim_product UNIQUE (product_id)
);

-- fact_order_item
CREATE TABLE gold.fact_order_item (
    order_id        nvarchar(50)   NOT NULL,
    order_item_id   int            NOT NULL,
    date_key        int            NOT NULL,
    customer_key    int            NOT NULL,
    seller_key      int            NOT NULL,
    product_key     int            NOT NULL,
    delivery_city   nvarchar(100)  NULL,
    delivery_state  nvarchar(2)    NULL,
    delivery_region nvarchar(20)   NULL,
    order_status    nvarchar(20)   NOT NULL,
    price           decimal(10,2)  NOT NULL,
    freight_value   decimal(10,2)  NOT NULL,
    delivery_days   int            NULL,     -- NULL nếu chưa giao / bị hủy
    delay_days      int            NULL,     -- dương = trễ, âm = sớm
    is_late         bit            NULL,
    review_score    tinyint        NULL,     -- điểm của cả đơn, lặp cho từng sản phẩm
    CONSTRAINT pk_fact_order_item PRIMARY KEY (order_id, order_item_id),
    CONSTRAINT fk_fact_date     FOREIGN KEY (date_key)     REFERENCES gold.dim_date (date_key),
    CONSTRAINT fk_fact_customer FOREIGN KEY (customer_key) REFERENCES gold.dim_customer (customer_key),
    CONSTRAINT fk_fact_seller   FOREIGN KEY (seller_key)   REFERENCES gold.dim_seller (seller_key),
    CONSTRAINT fk_fact_product  FOREIGN KEY (product_key)  REFERENCES gold.dim_product (product_key)
);
GO

-- Index cho các khóa ngoại: tăng tốc join khi truy vấn OLAP / dashboard
CREATE INDEX ix_fact_date     ON gold.fact_order_item (date_key);
CREATE INDEX ix_fact_customer ON gold.fact_order_item (customer_key);
CREATE INDEX ix_fact_seller   ON gold.fact_order_item (seller_key);
CREATE INDEX ix_fact_product  ON gold.fact_order_item (product_key);
GO

PRINT N'Đã tạo star schema gold: 4 dim + 1 fact.';