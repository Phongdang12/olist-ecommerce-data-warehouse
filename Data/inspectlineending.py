path = r"E:\debugger-workflow-backend\olist-ecommerce-data-warehouse\Data\olist_order_reviews_dataset.csv"

with open(path, "rb") as f:
    data = f.read(4096)

print("CRLF count:", data.count(b"\r\n"))
print("LF count:", data.count(b"\n"))