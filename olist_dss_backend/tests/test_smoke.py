from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health():
    response=client.get('/health')
    assert response.status_code==200
    assert response.json()['status']=='ok'

def test_docs_available():
    assert client.get('/openapi.json').status_code==200

def test_retraining_routes_registered():
    schema=client.get('/openapi.json').json()
    assert '/api/v1/segments/retrain' in schema['paths']
    assert '/api/v1/segments/retrain/{job_id}' in schema['paths']


def test_recommendations_route_registered():
    schema = client.get('/openapi.json').json()
    assert '/api/v1/recommendations' in schema['paths']
    assert 'get' in schema['paths']['/api/v1/recommendations']


def test_recommendations_endpoint_response(monkeypatch):
    import app.services.recommendation_service as service
    import pandas as pd

    df = pd.DataFrame({
        "order_id": [f"o{i}" for i in range(150)],
        "purchase_date": pd.to_datetime(["2018-01-01"] * 150),
        "customer_state": ["SP"] * 100 + ["RJ"] * 50,
        "seller_state": ["SP"] * 150,
        "category_name_en": ["other"] * 150,
        "order_status": ["delivered"] * 150,
        "order_value": [100.0] * 150,
        "freight_value": [10.0] * 150,
        "item_count": [1] * 150,
        "delivery_days": [5] * 150,
        "delay_days": [0] * 150,
        "is_late": [1] * 10 + [0] * 90 + [0] * 50,
        "review_score": [5] * 150,
    })
    monkeypatch.setattr(service, "get_orders", lambda: df)
    monkeypatch.setattr(service, "get_latest_segment_summary", lambda: [])
    response = client.get('/api/v1/recommendations')
    assert response.status_code == 200
    payload = response.json()
    assert "recommendations" in payload
    assert payload["data_mode"] == "WAREHOUSE DATA"
    assert any(item["rule_id"] == "R002" for item in payload["recommendations"])
