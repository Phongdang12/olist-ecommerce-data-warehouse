# Olist DSS 
Backend xây dựng bằng **FastAPI** cho hệ thống hỗ trợ ra quyết định
(Decision Support System --- DSS) trên cơ sở dữ liệu `OlistDW`.

Hệ thống cung cấp các API phân tích dữ liệu kinh doanh, phân tích độ
nhạy **What-if**, phân khúc khách hàng bằng **RFM + K-Means**, và
**Decision Recommendations** --- khuyến nghị hỗ trợ ra quyết định dựa
trên quy tắc nghiệp vụ.

## 1. Công nghệ sử dụng

-   **Python**: ngôn ngữ lập trình chính.
-   **FastAPI**: xây dựng REST API và tài liệu OpenAPI.
-   **SQL Server**: lưu trữ dữ liệu OlistDW.
-   **SQLAlchemy + pyodbc**: kết nối và truy vấn SQL Server.
-   **Pandas + NumPy**: xử lý và phân tích dữ liệu.
-   **scikit-learn**: chuẩn hóa dữ liệu, huấn luyện K-Means và đánh giá
    phân cụm.
-   **Joblib**: lưu artifact mô hình phân cụm và bộ chuẩn hóa.

## 2. Cài đặt môi trường

Các bước dưới đây dành cho Windows, sử dụng PowerShell trong VS Code.

### Bước 1 --- Tạo môi trường ảo

Mở terminal tại thư mục dự án:

``` powershell
python -m venv .venv
```

### Bước 2 --- Kích hoạt môi trường ảo

``` powershell
.\.venv\Scripts\Activate.ps1
```

Nếu PowerShell chặn việc chạy script, có thể dùng terminal CMD:

``` cmd
.venv\Scripts\activate.bat
```

### Bước 3 --- Cài đặt thư viện

``` powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Bước 4 --- Tạo file cấu hình

``` powershell
Copy-Item .env.example .env
```

Mở `.env` và điều chỉnh chuỗi kết nối theo cấu hình SQL Server của máy
đang chạy dự án.

Ví dụ:

``` env
DSS_DATA_MODE=sql
DSS_DATABASE_URL=mssql+pyodbc://@localhost/OlistDW?driver=ODBC+Driver+18+for+SQL+Server&trusted_connection=yes&TrustServerCertificate=yes
DSS_RANDOM_SEED=42
DSS_MODEL_PATH=artifacts/late_risk_model.joblib
```

**Lưu ý cấu hình:**

-   Cài đặt Microsoft ODBC Driver for SQL Server tương ứng với driver
    được ghi trong chuỗi kết nối.
-   Chuỗi kết nối phải phù hợp với tên server/instance, database, phương
    thức xác thực và phiên bản ODBC trên máy.
-   Tài khoản SQL Server cần có quyền đọc các bảng Gold mà API sử dụng.
-   Chức năng phân khúc và khuyến nghị cần quyền tạo/đọc/ghi/cập nhật dữ
    liệu trong schema `dss`.
-   `DSS_DATA_MODE=sql` yêu cầu truy vấn dữ liệu trực tiếp từ SQL
    Server.
-   `DSS_MODEL_PATH` là đường dẫn artifact được cấu hình cho chức năng
    dự đoán rủi ro giao hàng trễ nếu chức năng đó được bật trong phiên
    bản đang dùng. Đây là cấu hình riêng, không phải file model K-Means
    của phân khúc khách hàng.

## 3. Khởi chạy backend

Sau khi cấu hình xong, chạy:

``` powershell
uvicorn app.main:app --reload
```

Các địa chỉ mặc định:

-   **Swagger UI:** http://127.0.0.1:8000/docs
-   **ReDoc:** http://127.0.0.1:8000/redoc
-   **Health check:** http://127.0.0.1:8000/health

Swagger UI cho phép xem schema request/response và gửi request thử
nghiệm mà không cần xây dựng frontend.

## 4. Phân khúc khách hàng bằng RFM + K-Means
### 4.1. Quy trình huấn luyện

API retrain thực hiện quy trình tổng quát sau:

1.  Kiểm tra/khởi tạo schema và các bảng kết quả cần thiết trong SQL
    Server.
2.  Truy vấn dữ liệu Gold cần thiết.
3.  Tính RFM theo từng khách hàng.
4.  Biến đổi đặc trưng lệch bằng `log1p` và chuẩn hóa bằng
    `StandardScaler`.
5.  Huấn luyện K-Means với số cụm cố định `K = 4`.
6.  Tính Silhouette Score trên tối đa 10.000 mẫu để tham khảo chất lượng
    phân cụm.
7.  Tạo tên mô tả các cụm dựa trên hồ sơ RFM, không gán tên theo ID số
    cố định.
8.  Ghi kết quả khách hàng, thống kê cụm và metadata lần huấn luyện vào
    SQL Server.
9.  Lưu artifact model/scaler theo cấu hình của module phân khúc.

`K = 4` được cố định theo yêu cầu nghiệp vụ. Silhouette Score chỉ là chỉ
số đánh giá, không tự động thay đổi số cụm. ID cụm K-Means có thể đổi
giữa các lần train; vì vậy cần đọc `segment_name` và chỉ số RFM thay vì
giả định `cluster_id = 0` luôn có cùng ý nghĩa.

### 4.2. Bắt đầu huấn luyện

1.  Khởi chạy backend và mở Swagger UI.
2.  Tìm `POST /api/v1/segments/retrain`.
3.  Chọn **Try it out** rồi **Execute**.

API tiếp nhận công việc và trả về HTTP `202 Accepted` cùng `job_id`. Ví
dụ minh họa:

``` json
{
  "job_id": "your-job-id",
  "status": "accepted"
}
```

Giá trị `job_id` trên chỉ là ví dụ, không phải mã công việc thực tế.

### 4.3. Theo dõi trạng thái

Gọi:

``` http
GET /api/v1/segments/retrain/{job_id}
```

Thay `{job_id}` bằng mã trả về từ bước trước. Theo dõi cho đến khi trạng
thái là:

-   `succeeded`: quá trình hoàn tất thành công.
-   `failed`: quá trình thất bại; xem thông báo lỗi trong response.

Sau khi train thành công, truy vấn thống kê cụm và danh sách khách hàng
bằng các API phân khúc ở mục 5.

## 5. Danh sách API

Các endpoint dưới đây phản ánh giao diện API dự kiến của backend; chi
tiết schema, tham số và mã lỗi thực tế cần đối chiếu trong `/docs` của
phiên bản đang chạy.

### 5.1. Health, analytics và What-if

  ---------------------------------------------------------------------------------------
  Phương thức             Endpoint                                Chức năng
  ----------------------- --------------------------------------- -----------------------
  `GET`                   `/health`                               Kiểm tra trạng thái
                                                                  backend

  `GET`                   `/api/v1/dashboard/summary`             Tổng hợp chỉ số kinh
                                                                  doanh

  `GET`                   `/api/v1/analytics/categories`          Phân tích theo danh mục
                                                                  sản phẩm

  `GET`                   `/api/v1/analytics/delivery-by-state`   Phân tích giao hàng
                                                                  theo bang

  `POST`                  `/api/v1/what-if`                       Phân tích độ nhạy theo
                                                                  các tham số kịch bản
                                                                  
  ---------------------------------------------------------------------------------------

### 5.2. Customer Segmentation

  -------------------------------------------------------------------------------------------
  Phương thức             Endpoint                                    Chức năng
  ----------------------- ------------------------------------------- -----------------------
  `POST`                  `/api/v1/segments/retrain`                  Khởi chạy quy trình
                                                                      truy vấn RFM, train
                                                                      K-Means và lưu kết quả

  `GET`                   `/api/v1/segments/retrain/{job_id}`         Kiểm tra trạng thái/kết
                                                                      quả một lần train

  `GET`                   `/api/v1/segments`                          Truy vấn thống kê các
                                                                      cụm và chỉ số RFM

  `GET`                   `/api/v1/segments/{cluster_id}/customers`   Truy vấn khách hàng
                                                                      theo cụm, có phân trang
                                                                      
  -------------------------------------------------------------------------------------------

Ví dụ:

``` http
GET /api/v1/segments/0/customers?limit=100&offset=0
```

-   `cluster_id`: ID cụm cần truy vấn.
-   `limit`: số bản ghi tối đa.
-   `offset`: số bản ghi bỏ qua để phân trang.

`0` chỉ là ví dụ; hãy dùng ID cụm có trong response thực tế.

### 5.3. Decision Recommendations

  -----------------------------------------------------------------------------------------------
  Phương thức             Endpoint                                        Chức năng
  ----------------------- ----------------------------------------------- -----------------------
  `GET`                   `/api/v1/recommendations`                       Tạo danh sách khuyến
                                                                          nghị từ dữ liệu hiện có

  `GET`                   `/api/v1/recommendations?order_growth_pct=10`   Đánh giá khuyến nghị
                                                                          khi áp dụng kịch bản
                                                                          What-if tăng số đơn 10%
                                                                          
  -----------------------------------------------------------------------------------------------

Module khuyến nghị dùng quy tắc nghiệp vụ, không huấn luyện thêm mô hình
ML và không yêu cầu bảng lưu khuyến nghị riêng trong phiên bản hiện tại.

#### Quy tắc R001 --- Cụm khách hàng có giá trị cao

-   Xem thống kê RFM đã lưu của các cụm.
-   Chọn cụm theo giá trị `avg_monetary` thực tế, không mặc định cụm nào
    theo `cluster_id`.
-   Ngưỡng hiện tại: giá trị mua hàng trung bình của cụm cao nhất phải
    đạt ít nhất `1.5x` mức trung bình mỗi khách hàng trên toàn bộ các
    cụm.
-   Hành động gợi ý: ưu tiên giữ chân, chăm sóc cá nhân hóa và chương
    trình khách hàng thân thiết cho cụm đó.

R001 cần dữ liệu phân khúc đã được tạo thành công. Nếu chưa có, response
có thể chứa cảnh báo rằng quy tắc chưa được đánh giá.

#### Quy tắc R002 --- Tỷ lệ giao trễ cao theo bang

-   Cần tối thiểu `100` đơn có kết quả giao hàng xác định tại bang.
-   Tỷ lệ giao trễ của bang phải cao hơn tỷ lệ toàn hệ thống ít nhất `3`
    điểm phần trăm.
-   Hành động gợi ý: kiểm tra hãng vận chuyển, thời gian xử lý và hoạt
    động giao hàng tại bang được nêu trong bằng chứng.

Tỷ lệ của bang và tỷ lệ toàn hệ thống phải dùng cùng định nghĩa đơn giao
trễ và cùng cách loại trừ đơn chưa xác định được kết quả giao hàng.

#### Quy tắc R003 --- Kịch bản làm tăng phí vận chuyển ghi nhận

-   Được đánh giá khi request có tham số kịch bản What-if.
-   Ngưỡng hiện tại: tổng `freight_value` trong kịch bản tăng ít nhất
    `10%` so với đường cơ sở.
-   Hành động gợi ý: xem xét chính sách phí, năng lực xử lý đơn và
    phương án làm việc với đối tác vận chuyển.

`freight_value` là phí vận chuyển được ghi nhận trong dữ liệu đơn hàng,
không mặc nhiên bằng chi phí vận hành thực tế. What-if là phân tích độ
nhạy theo giả định, không phải dự báo nhân quả.

#### Cấu trúc response khuyến nghị

Response gồm danh sách `recommendations`; mỗi phần tử có các trường như
`rule_id`, `title`, `priority`, `evidence`, `suggested_action` và
`reason`. Response cũng có thể chứa thời điểm tạo, chế độ dữ liệu, cảnh
báo và các ngưỡng đã dùng. Dùng `/docs` để xem schema chính xác của
phiên bản đang chạy.

Lưu ý: nếu gọi endpoint không kèm tham số What-if, R003 không được đánh
giá. Danh sách rỗng nghĩa là không có quy tắc nào vượt ngưỡng trong lần
đánh giá đó, không chứng minh rằng hoạt động kinh doanh không có vấn đề.

## 6. Lưu trữ dữ liệu

Module phân khúc sử dụng schema `dss` trong database `OlistDW`. Các bảng
kết quả được khởi tạo tự động khi quy trình retrain chạy, theo logic của
phiên bản ứng dụng.

Các nhóm dữ liệu bao gồm:

-   **Kết quả khách hàng:** `customer_id`, `cluster_id`, tên phân khúc
    và các chỉ số RFM.
-   **Thống kê cụm:** số khách, tỷ lệ khách, trung bình/trung vị RFM và
    tổng giá trị mua hàng.
-   **Lịch sử huấn luyện:** metadata của các lần chạy trong bảng
    `dss.customer_segment_model_runs`.
-   **Artifact:** model K-Means và scaler được lưu theo cấu hình module.

Sau lần retrain thành công, kết quả phân khúc hiện tại được cập nhật.
Metadata lịch sử được lưu theo cơ chế triển khai của service.

Decision Recommendations được tính từ dữ liệu hiện có tại thời điểm gọi
API; phiên bản này không bắt buộc lưu lịch sử khuyến nghị hoặc trạng
thái xử lý của người quản lý.

## 7. Vận hành và xử lý sự cố

### 7.1. Kiểm tra dữ liệu Gold

Phân tích và phân khúc phụ thuộc vào các bảng Gold. Nếu bảng chưa được
tạo, chưa nạp đủ dữ liệu hoặc thiếu cột cần thiết, API có thể trả lỗi
hoặc không có dữ liệu để phân tích.

Trước khi train, kiểm tra:

-   Các bảng Gold đã tồn tại và được nạp dữ liệu.
-   Có đơn hàng giao thành công để tính RFM.
-   Các khóa liên kết khách hàng, đơn hàng và ngày tháng hợp lệ.
-   Tài khoản kết nối có đủ quyền đọc Gold và ghi các bảng kết quả trong
    `dss`.

### 7.2. Job huấn luyện

Trạng thái job retrain của phiên bản hiện tại được giữ trong bộ nhớ của
tiến trình FastAPI:

-   Chạy một Uvicorn worker để tránh các worker không chia sẻ trạng thái
    job.
-   Khởi động lại backend có thể làm mất trạng thái job đang theo dõi.
-   Dữ liệu đã ghi vào SQL Server và artifact đã lưu trên đĩa không tự
    động bị xóa khi backend khởi động lại.
-   Với triển khai nhiều worker/production, cân nhắc hàng đợi tác vụ và
    kho trạng thái bền vững.

### 7.3. Phân biệt kết quả phân tích và dự báo

-   **Dashboard summary/analytics:** mô tả dữ liệu lịch sử trong
    warehouse.
-   **What-if:** tính kết quả theo các giả định kịch bản.
-   **Customer segmentation:** nhóm khách hàng theo hành vi RFM.
-   **Decision Recommendations:** áp dụng quy tắc nghiệp vụ để chỉ ra
    dấu hiệu cần chú ý và hành động nên xem xét.

Khuyến nghị là hỗ trợ quyết định, không phải quyết định tự động hoặc bảo
đảm kết quả kinh doanh.

## 8. Luồng chức năng tổng quan

``` text
OlistDW (SQL Server)
        |
        v
   FastAPI Backend
        |
        +--> Dashboard Summary
        |
        +--> Analytics
        |      +--> Categories
        |      +--> Delivery by State
        |
        +--> What-if Analysis
        |
        +--> Customer Segmentation
        |      +--> Extract delivered orders
        |      +--> Calculate RFM
        |      +--> Standardize features
        |      +--> Train K-Means (K=4)
        |      +--> Save segment results
        |
        +--> Decision Recommendations
               +--> R001: High-value customer segment
               +--> R002: Late delivery by state
               +--> R003: What-if freight increase
```

## 9. Kiểm thử nhanh

Thực hiện theo thứ tự:

1.  Gọi `GET /health`.
2.  Gọi `GET /api/v1/dashboard/summary`.
3.  Kiểm tra `GET /api/v1/analytics/categories`.
4.  Kiểm tra `GET /api/v1/analytics/delivery-by-state`.
5.  Gửi request hợp lệ đến `POST /api/v1/what-if`.
6.  Gọi `POST /api/v1/segments/retrain`.
7.  Theo dõi job bằng `GET /api/v1/segments/retrain/{job_id}`.
8.  Khi job thành công, gọi `GET /api/v1/segments`.
9.  Truy vấn một cụm bằng `GET /api/v1/segments/{cluster_id}/customers`.
10. Gọi `GET /api/v1/recommendations`.
11. Gọi `GET /api/v1/recommendations?order_growth_pct=11` để kiểm tra
    luồng đánh giá What-if của R003.

Kết quả mong đợi là backend kết nối được với OlistDW, trả về các phân
tích lịch sử, thực hiện phân khúc khách hàng, lưu kết quả vào SQL Server
và cung cấp khuyến nghị dựa trên các ngưỡng nghiệp vụ đã định nghĩa.
