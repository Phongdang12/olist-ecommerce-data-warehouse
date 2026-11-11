/*
---
Stored Procedure: Load Bronze Layer (Source -> Bronze)
---
*/


USE OlistDW;
GO

CREATE OR ALTER PROCEDURE bronze.load_bronze AS
BEGIN
    DECLARE @batch_start_time DATETIME = GETDATE();
    DECLARE @batch_end_time DATETIME;
    DECLARE @start_time DATETIME, @end_time DATETIME;
    
    BEGIN TRY
        PRINT '========================================';
        PRINT '           Loading Bronze Layer         ';
        PRINT '========================================';
        PRINT '';

        -- orders
        PRINT '>> Truncating Table: bronze.orders';
        SET @start_time = GETDATE();
        TRUNCATE TABLE bronze.orders;
        
        PRINT '>> Loading data to: bronze.orders';
        BULK INSERT bronze.orders
        FROM 'E:\debugger-workflow-backend\olist-ecommerce-data-warehouse\Data\olist_orders_dataset.csv'
        WITH (
            FORMAT = 'CSV',
            FIELDQUOTE = '"',
            FIRSTROW = 2,
            FIELDTERMINATOR = ',',
            ROWTERMINATOR = '0x0d0a',
            CODEPAGE = '65001',
            TABLOCK
        );
        SET @end_time = GETDATE();
        PRINT '>> Completed in: ' + CAST(DATEDIFF(SECOND, @start_time, @end_time) AS VARCHAR) + ' seconds';
        PRINT '';
        
        -- order_items
        PRINT '>> Truncating Table: bronze.order_items';
        SET @start_time = GETDATE();
        TRUNCATE TABLE bronze.order_items;
        
        PRINT '>> Loading data to: bronze.order_items';
        BULK INSERT bronze.order_items
        FROM 'E:\debugger-workflow-backend\olist-ecommerce-data-warehouse\Data\olist_order_items_dataset.csv'
        WITH (
            FORMAT = 'CSV',
            FIELDQUOTE = '"',
            FIRSTROW = 2,
            FIELDTERMINATOR = ',',
            ROWTERMINATOR = '0x0d0a',
            CODEPAGE = '65001',
            TABLOCK
        );
        SET @end_time = GETDATE();
        PRINT '>> Completed in: ' + CAST(DATEDIFF(SECOND, @start_time, @end_time) AS VARCHAR) + ' seconds';
        PRINT '';
        
        -- customers
        PRINT '>> Truncating Table: bronze.customers';
        SET @start_time = GETDATE();
        TRUNCATE TABLE bronze.customers;
        
        PRINT '>> Loading data to: bronze.customers';
        BULK INSERT bronze.customers
        FROM 'E:\debugger-workflow-backend\olist-ecommerce-data-warehouse\Data\olist_customers_dataset.csv'
        WITH (
            FORMAT = 'CSV',
            FIELDQUOTE = '"',
            FIRSTROW = 2,
            FIELDTERMINATOR = ',',
            ROWTERMINATOR = '0x0d0a',
            CODEPAGE = '65001',
            TABLOCK
        );
        SET @end_time = GETDATE();
        PRINT '>> Completed in: ' + CAST(DATEDIFF(SECOND, @start_time, @end_time) AS VARCHAR) + ' seconds';
        PRINT '';
        
  
        
        -- sellers
        PRINT '>> Truncating Table: bronze.sellers';
        SET @start_time = GETDATE();
        TRUNCATE TABLE bronze.sellers;
        
        PRINT '>> Loading data to: bronze.sellers';
        BULK INSERT bronze.sellers
        FROM 'E:\debugger-workflow-backend\olist-ecommerce-data-warehouse\Data\olist_sellers_dataset.csv'
        WITH (
            FORMAT = 'CSV',
            FIELDQUOTE = '"',
            FIRSTROW = 2,
            FIELDTERMINATOR = ',',
            ROWTERMINATOR = '0x0d0a',
            CODEPAGE = '65001',
            TABLOCK
        );
        SET @end_time = GETDATE();
        PRINT '>> Completed in: ' + CAST(DATEDIFF(SECOND, @start_time, @end_time) AS VARCHAR) + ' seconds';
        PRINT '';
        
        -- products
        PRINT '>> Truncating Table: bronze.products';
        SET @start_time = GETDATE();
        TRUNCATE TABLE bronze.products;
        
        PRINT '>> Loading data to: bronze.products';
        BULK INSERT bronze.products
        FROM 'E:\debugger-workflow-backend\olist-ecommerce-data-warehouse\Data\olist_products_dataset.csv'
        WITH (
            FORMAT = 'CSV',
            FIELDQUOTE = '"',
            FIRSTROW = 2,
            FIELDTERMINATOR = ',',
            ROWTERMINATOR = '0x0d0a',
            CODEPAGE = '65001',
            TABLOCK
        );
        SET @end_time = GETDATE();
        PRINT '>> Completed in: ' + CAST(DATEDIFF(SECOND, @start_time, @end_time) AS VARCHAR) + ' seconds';
        PRINT '';
        
        -- category_translation
        PRINT '>> Truncating Table: bronze.category_translation';
        SET @start_time = GETDATE();
        TRUNCATE TABLE bronze.category_translation;
        
        PRINT '>> Loading data to: bronze.category_translation';
        BULK INSERT bronze.category_translation
        FROM 'E:\debugger-workflow-backend\olist-ecommerce-data-warehouse\Data\product_category_name_translation.csv'
        WITH (
            FORMAT = 'CSV',
            FIELDQUOTE = '"',
            FIRSTROW = 2,
            FIELDTERMINATOR = ',',
            ROWTERMINATOR = '0x0d0a',
            CODEPAGE = '65001',
            TABLOCK
        );
        SET @end_time = GETDATE();
        PRINT '>> Completed in: ' + CAST(DATEDIFF(SECOND, @start_time, @end_time) AS VARCHAR) + ' seconds';
        PRINT '';


        -- order_reviews
        PRINT '>> Truncating Table: bronze.order_reviews';
        SET @start_time = GETDATE();
        TRUNCATE TABLE bronze.order_reviews;
        
        PRINT '>> Loading data to: bronze.order_reviews';
        BULK INSERT bronze.order_reviews
        FROM 'E:\debugger-workflow-backend\olist-ecommerce-data-warehouse\Data\olist_order_reviews_dataset.csv'
        WITH (
            FORMAT = 'CSV',
            FIELDQUOTE = '"',
            FIRSTROW = 2,
            FIELDTERMINATOR = ',',
            ROWTERMINATOR = '0x0d0a',
            CODEPAGE = '65001',
            TABLOCK
        );
        SET @end_time = GETDATE();
        PRINT '>> Completed in: ' + CAST(DATEDIFF(SECOND, @start_time, @end_time) AS VARCHAR) + ' seconds';
        PRINT '';
        
        SET @batch_end_time = GETDATE();
        
        PRINT '========================================';
        PRINT '  Loading Bronze Layer is Completed     ';
        PRINT '========================================';
        PRINT '';
        PRINT 'Total Load Duration: ' + CAST(DATEDIFF(SECOND, @batch_start_time, @batch_end_time) AS NVARCHAR) + ' seconds';
        PRINT '========================================';
        
    END TRY
    BEGIN CATCH
        SET @batch_end_time = GETDATE();
        
        PRINT '========================================';
        PRINT '  ERROR OCCURRED DURING LOADING BRONZE LAYER';
        PRINT '========================================';
        PRINT 'Error: ' + ERROR_MESSAGE();
        PRINT 'Total Duration: ' + CAST(DATEDIFF(SECOND, @batch_start_time, @batch_end_time) AS NVARCHAR) + ' seconds';
        PRINT '========================================';
        
        -- Re-throw the error to notify the caller
        THROW;
    END CATCH
END;
GO


EXEC bronze.load_bronze;
