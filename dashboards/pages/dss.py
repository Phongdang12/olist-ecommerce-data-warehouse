import os
import time

import pandas as pd
import requests
import streamlit as st

st.title("Olist Decision Support System")

# ---------------------------------------------------------------------
# API Setup & Helper Functions
# ---------------------------------------------------------------------
default_api_url = os.getenv("DSS_API_URL", "http://127.0.0.1:8000")
api_url = st.session_state.get("dss_api_url", default_api_url)

def api_get(path, params=None, timeout=30):
    response = requests.get(f"{api_url}{path}", params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()

def api_post(path, payload=None, timeout=60):
    response = requests.post(f"{api_url}{path}", json=payload, timeout=timeout)
    response.raise_for_status()
    return response.json()

def show_api_error(exc, context):
    detail = str(exc)
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except ValueError:
            detail = exc.response.text
    st.error(f"{context}: {detail}")
    st.caption("Kiểm tra FastAPI đang chạy, URL trong sidebar và cấu hình SQL Server của backend.")

def money(value):
    try:
        return f"R$ {float(value):,.2f}"
    except (TypeError, ValueError):
        return "—"

def pct(value):
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "—"

# ---------------------------------------------------------------------
# Silent Auto Health Check (Kiểm tra kết nối ngay khi vừa load)
# ---------------------------------------------------------------------
is_connected = False
try:
    # Gọi thử API health check (không in dòng màu xanh)
    api_get("/health", timeout=3)
    is_connected = True
except requests.RequestException:
    is_connected = False

# ---------------------------------------------------------------------
# Sidebar (CHỈ HIỂN THỊ KHI KHÔNG CÓ KẾT NỐI)
# ---------------------------------------------------------------------
if not is_connected:
    with st.sidebar:
        st.header("DSS Backend")
        new_api_url = st.text_input(
            "FastAPI Base URL",
            value=api_url,
            help="Ví dụ: http://127.0.0.1:8000",
        ).strip().rstrip("/")
        st.session_state["dss_api_url"] = new_api_url

        if st.button("Kiểm tra lại kết nối", use_container_width=True):
            st.rerun()

        st.caption("Khởi chạy FastAPI bằng `uvicorn app.main:app --reload`.")
    
    # Báo lỗi và dừng trang web lại nếu mất kết nối
    st.warning("Chưa kết nối được FastAPI. Hãy kiểm tra URL trong sidebar hoặc khởi động lại backend.")
    st.stop()

# ---------------------------------------------------------------------
# Nội dung chính (Chạy khi đã có kết nối)
# ---------------------------------------------------------------------
overview_tab, analytics_tab, whatif_tab, segments_tab, recommendations_tab = st.tabs([
    "📌 Overview",
    "📊 Analytics",
    "🧪 What-if",
    "👥 Customer Segmentation",
    "💡 Recommendations",
])

# ---------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------
# ---------------------------------------------------------------------
# Overview (Cải tiến giao diện)
# ---------------------------------------------------------------------
# ---------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------
with overview_tab:
    st.subheader("Tổng quan hoạt động kinh doanh")
    
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        if st.button("🔄 Làm mới dữ liệu", key="refresh_overview", use_container_width=True):
            st.rerun()

    try:
        summary = api_get("/api/v1/dashboard/summary")
        note = summary.get("data_mode_note")
        if note:
            st.caption(f"📌 **Nguồn dữ liệu**: {note}")

        # --- Block 1: Chỉ số hiệu năng chính (KPI Metrics) ---
        st.markdown("##### 📈 Chỉ số hiệu năng chính (KPIs)")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tổng đơn hàng", f"{int(summary.get('orders', 0)):,}")
        c2.metric("Tổng giá trị đơn hàng", money(summary.get("order_value_total")))
        c3.metric("Giá trị đơn hàng TB (AOV)", money(summary.get("average_order_value")))
        c4.metric("Tổng phí vận chuyển", money(summary.get("freight_value_total")))

        st.markdown("---")

        # --- Block 2: Vận hành & Trải nghiệm khách hàng ---
        st.markdown("##### 🚚 Vận hành & Trải nghiệm khách hàng")
        c5, c6, c7 = st.columns(3)
        c5.metric("Tỷ lệ giao trễ", pct(summary.get("late_rate_pct")), delta_color="inverse")
        c6.metric("Đơn có trạng thái giao hàng", f"{int(summary.get('orders_with_known_late_status') or 0):,}")
        c7.metric("Điểm đánh giá trung bình", f"⭐ {summary.get('average_review_score', '—')}")

        st.markdown("---")

        # --- Block 3: Phân tích trực quan nhanh (Dùng API categories & delivery) ---
        st.markdown("##### 📊 Phân tích cơ cấu kinh doanh")
        chart_col1, chart_col2 = st.columns(2)

        # 1. Biểu đồ Top 5 Danh mục doanh thu cao nhất
        with chart_col1:
            st.markdown("**Top 5 danh mục doanh thu cao nhất**")
            try:
                cat_payload = api_get("/api/v1/analytics/categories")
                cat_df = pd.DataFrame(cat_payload.get("items", []))
                if not cat_df.empty and {"category", "revenue"}.issubset(cat_df.columns):
                    top5_cat = cat_df.sort_values(by="revenue", ascending=False).head(5)
                    st.bar_chart(top5_cat.set_index("category")["revenue"])
                else:
                    st.info("Chưa có dữ liệu danh mục.")
            except requests.RequestException as exc:
                show_api_error(exc, "Không tải được biểu đồ danh mục")

        # 2. Biểu đồ Top 5 Bang có tỷ lệ giao trễ cao nhất
        with chart_col2:
            st.markdown("**Top 5 bang có tỷ lệ giao trễ cao nhất**")
            try:
                deliv_payload = api_get("/api/v1/analytics/delivery-by-state")
                deliv_df = pd.DataFrame(deliv_payload.get("items", []))
                if not deliv_df.empty and {"state", "late_rate_pct"}.issubset(deliv_df.columns):
                    top5_deliv = deliv_df.dropna(subset=["late_rate_pct"]).sort_values(by="late_rate_pct", ascending=False).head(5)
                    st.bar_chart(top5_deliv.set_index("state")["late_rate_pct"])
                else:
                    st.info("Chưa có dữ liệu giao hàng.")
            except requests.RequestException as exc:
                show_api_error(exc, "Không tải được biểu đồ giao hàng")

        with st.expander("🔍 Xem chi tiết response JSON"):
            st.json(summary)

    except requests.RequestException as exc:
        show_api_error(exc, "Không tải được dashboard summary")

# ---------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------
with analytics_tab:
    st.subheader("Phân tích kinh doanh")
    left, right = st.columns(2)
    try:
        category_payload = api_get("/api/v1/analytics/categories")
        category_df = pd.DataFrame(category_payload.get("items", []))
        with left:
            st.markdown("**Doanh thu theo danh mục sản phẩm**")
            if not category_df.empty:
                st.bar_chart(category_df.head(15).set_index("category")["revenue"])
                st.dataframe(category_df, use_container_width=True, hide_index=True)
            else:
                st.info("API chưa trả về dữ liệu danh mục.")
    except requests.RequestException as exc:
        with left:
            show_api_error(exc, "Không tải được category analytics")
    try:
        delivery_payload = api_get("/api/v1/analytics/delivery-by-state")
        delivery_df = pd.DataFrame(delivery_payload.get("items", []))
        with right:
            st.markdown("**Tỷ lệ giao trễ theo bang**")
            if not delivery_df.empty:
                chart_df = delivery_df.dropna(subset=["late_rate_pct"]).head(15)
                st.bar_chart(chart_df.set_index("state")["late_rate_pct"])
                st.dataframe(delivery_df, use_container_width=True, hide_index=True)
            else:
                st.info("API chưa trả về dữ liệu giao hàng.")
    except requests.RequestException as exc:
        with right:
            show_api_error(exc, "Không tải được delivery analytics")

# ---------------------------------------------------------------------
# What-if
# ---------------------------------------------------------------------
with whatif_tab:
    st.subheader("Phân tích độ nhạy What-if")
    st.info(
        "Thay đổi các giả định để xem tác động tính toán lên kết quả kinh doanh. "
        "Đây là mô phỏng độ nhạy xác định, không phải dự báo nhân quả."
    )
    with st.form("whatif_form"):
        a, b = st.columns(2)
        with a:
            order_growth = st.slider("Tăng trưởng số đơn hàng (%)", -50, 100, 10, 1)
            order_value_change = st.slider("Thay đổi giá trị đơn hàng (%)", -50, 100, 0, 1)
        with b:
            freight_change = st.slider("Thay đổi phí vận chuyển ghi nhận (%)", -50, 100, 0, 1)
            late_reduction = st.slider("Mức giảm tỷ lệ giao trễ (%)", 0, 100, 0, 1)
        run_scenario = st.form_submit_button("Chạy mô phỏng", type="primary")
    if run_scenario:
        payload = {
            "order_growth_pct": order_growth,
            "order_value_change_pct": order_value_change,
            "freight_change_pct": freight_change,
            "late_rate_reduction_pct": late_reduction,
        }
        try:
            result = api_post("/api/v1/what-if", payload)
            baseline = result.get("baseline", {})
            scenario = result.get("scenario", {})
            change = result.get("change", {})
            st.markdown("#### So sánh baseline và kịch bản")
            metrics = [
                ("Số đơn hàng", "orders", "number"),
                ("AOV", "average_order_value", "money"),
                ("Tổng giá trị đơn hàng", "order_value_total", "money"),
                ("Tổng phí vận chuyển", "freight_value_total", "money"),
                ("Tỷ lệ giao trễ", "late_rate_pct", "percent"),
            ]
            rows = []
            for label, key, kind in metrics:
                before, after = baseline.get(key), scenario.get(key)
                if kind == "money":
                    before, after = money(before), money(after)
                elif kind == "percent":
                    before, after = pct(before), pct(after)
                elif before is not None:
                    before, after = f"{int(before):,}", f"{int(after):,}"
                rows.append({"Chỉ số": label, "Baseline": before, "Kịch bản": after})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            x, y = st.columns(2)
            x.metric("Mức thay đổi tổng giá trị đơn hàng", money(change.get("order_value_total")))
            y.metric("Tỷ lệ thay đổi tổng giá trị", pct(change.get("order_value_total_pct")))
            if result.get("warning"):
                st.warning(result["warning"])
            with st.expander("Xem response JSON"):
                st.json(result)
        except requests.RequestException as exc:
            show_api_error(exc, "Không chạy được What-if")

# ---------------------------------------------------------------------
# Customer segmentation
# ---------------------------------------------------------------------
with segments_tab:
    st.subheader("Phân khúc khách hàng RFM + K-Means")
    st.caption("Kết quả được đọc từ các bảng phân khúc trong schema dss của OlistDW.")
    seg_col, train_col = st.columns([3, 1])
    with seg_col:
        if st.button("Tải lại kết quả phân khúc", key="refresh_segments"):
            st.rerun()
    with train_col:
        start_training = st.button("Huấn luyện lại K-Means", type="primary", use_container_width=True)
    if start_training:
        try:
            job = api_post("/api/v1/segments/retrain", {})
            st.session_state["dss_retrain_job_id"] = job.get("job_id")
            st.success(f"Đã gửi yêu cầu huấn luyện. Job ID: {job.get('job_id', 'N/A')}")
            st.info("Nhấn nút kiểm tra trạng thái bên dưới để cập nhật tiến trình.")
        except requests.RequestException as exc:
            show_api_error(exc, "Không thể bắt đầu retraining")
    job_id = st.session_state.get("dss_retrain_job_id")
    if job_id:
        if st.button("Kiểm tra trạng thái retraining", key="check_retrain"):
            try:
                job = api_get(f"/api/v1/segments/retrain/{job_id}")
                status = job.get("status", "unknown")
                if status == "succeeded":
                    st.success("Huấn luyện hoàn tất.")
                    st.json(job)
                elif status == "failed":
                    st.error(f"Huấn luyện thất bại: {job.get('error', 'Không có chi tiết lỗi')}")
                else:
                    st.info(f"Trạng thái job: {status}")
                st.session_state["dss_retrain_status"] = status
            except requests.RequestException as exc:
                show_api_error(exc, "Không đọc được trạng thái job")
    try:
        segments = api_get("/api/v1/segments")
        items = segments.get("items", [])
        if items:
            s1, s2 = st.columns(2)
            s1.metric("Số phân khúc", segments.get("segment_count", len(items)))
            s2.metric("Tổng khách hàng", f"{int(segments.get('total_customers', 0)):,}")
            seg_df = pd.DataFrame(items)
            preferred = [
                "cluster_id", "segment_name", "customer_count", "customer_percentage",
                "avg_recency_days", "avg_frequency", "avg_monetary",
                "median_recency_days", "median_frequency", "median_monetary",
                "total_monetary", "silhouette_score", "trained_at",
            ]
            seg_df = seg_df[[c for c in preferred if c in seg_df.columns]]
            st.markdown("**Tổng hợp các cụm khách hàng**")
            st.dataframe(seg_df, use_container_width=True, hide_index=True)
            if {"segment_name", "customer_count"}.issubset(seg_df.columns):
                st.markdown("**Quy mô từng phân khúc**")
                st.bar_chart(seg_df.set_index("segment_name")["customer_count"])
            cluster_ids = sorted(int(item["cluster_id"]) for item in items)
            selected_cluster = st.selectbox(
                "Chọn cụm để xem danh sách khách hàng",
                cluster_ids,
                format_func=lambda cid: next(
                    (f"Cụm {cid} — {item.get('segment_name', '')}" for item in items if int(item["cluster_id"]) == cid),
                    f"Cụm {cid}",
                ),
            )
            limit = st.selectbox("Số khách hàng mỗi trang", [20, 50, 100, 200], index=1)
            offset = st.number_input("Offset", min_value=0, value=0, step=int(limit))
            customers = api_get(
                f"/api/v1/segments/{selected_cluster}/customers",
                params={"limit": int(limit), "offset": int(offset)},
            )
            st.caption(f"Hiển thị {len(customers.get('items', [])):,} / {int(customers.get('total', 0)):,} khách hàng")
            customer_df = pd.DataFrame(customers.get("items", []))
            st.dataframe(customer_df, use_container_width=True, hide_index=True)
        else:
            st.info("Chưa có kết quả phân khúc. Hãy chạy Huấn luyện lại K-Means.")
    except requests.RequestException as exc:
        show_api_error(exc, "Không tải được phân khúc khách hàng")

# ---------------------------------------------------------------------
# Decision recommendations
# ---------------------------------------------------------------------
with recommendations_tab:
    st.subheader("Decision Recommendations")
    st.caption("Khuyến nghị được sinh từ các quy tắc nghiệp vụ R001, R002 và R003 trong FastAPI.")
    st.markdown("**Tham số What-if (không nhập thì R003 không được đánh giá)**")
    use_scenario = st.checkbox("Đánh giá khuyến nghị theo kịch bản What-if", value=False)
    params = {}
    if use_scenario:
        growth = st.number_input("Tăng trưởng số đơn hàng (%)", min_value=-90.0, max_value=300.0, value=15.0, step=1.0)
        value_delta = st.number_input("Thay đổi giá trị đơn hàng (%)", min_value=-90.0, max_value=300.0, value=0.0, step=1.0)
        freight_delta = st.number_input("Thay đổi phí vận chuyển (%)", min_value=-100.0, max_value=300.0, value=0.0, step=1.0)
        late_delta = st.number_input("Mức giảm tỷ lệ giao trễ (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
        params = {
            "order_growth_pct": growth,
            "order_value_change_pct": value_delta,
            "freight_change_pct": freight_delta,
            "late_rate_reduction_pct": late_delta,
        }
    if st.button("Tạo khuyến nghị", type="primary", key="get_recommendations"):
        try:
            recs = api_get("/api/v1/recommendations", params=params)
            st.session_state["dss_recommendations"] = recs
        except requests.RequestException as exc:
            show_api_error(exc, "Không tạo được khuyến nghị")
    recs = st.session_state.get("dss_recommendations")
    if recs:
        st.caption(f"Data mode: {recs.get('data_mode', 'N/A')} · Tạo lúc: {recs.get('generated_at_utc', 'N/A')}")
        warnings = recs.get("warnings", [])
        for warning in warnings:
            st.warning(warning)
        recommendations = recs.get("recommendations", [])
        if recommendations:
            priority_labels = {"high": "Cao", "medium": "Trung bình", "low": "Thấp"}
            for item in sorted(recommendations, key=lambda x: x.get("rule_id", "")):
                with st.container(border=True):
                    title_col, priority_col = st.columns([4, 1])
                    title_col.markdown(f"**{item.get('rule_id', '')} — {item.get('title', '')}**")
                    priority_col.markdown(f"**Ưu tiên: {priority_labels.get(item.get('priority'), item.get('priority'))}**")
                    st.write(item.get("reason", ""))
                    st.markdown("**Bằng chứng**")
                    st.json(item.get("evidence", {}))
                    st.markdown("**Hành động đề xuất**")
                    st.write(item.get("suggested_action", ""))
        else:
            st.info("Không có quy tắc nào vượt ngưỡng trong lần đánh giá này.")
        with st.expander("Ngưỡng đánh giá"):
            st.json(recs.get("thresholds", {}))
    else:
        st.info("Nhấn “Tạo khuyến nghị” để gọi API và hiển thị kết quả.")
