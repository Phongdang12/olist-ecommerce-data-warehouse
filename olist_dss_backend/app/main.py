from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from app.schemas import WhatIfRequest
from app.services.data_service import get_orders
from app.services.analytics_service import dashboard_summary, sales_by_category, delivery_by_state
from app.services.whatif_service import run_what_if
from app.services.customer_segmentation_service import start_retraining_job, run_retraining_job, get_retraining_job, get_latest_segment_summary, get_segment_customers
from app.api.recommendations import router as recommendations_router

app = FastAPI(title="Olist DSS Backend", description="Olist analytics, What-if, RFM segmentation, and rule-based decision recommendations.", version="2.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(recommendations_router)

@app.get("/health")
def health():
    return {"status":"ok", "service":"olist-dss-backend"}

@app.get("/api/v1/dashboard/summary")
def get_dashboard_summary():
    try: return dashboard_summary(get_orders())
    except Exception as exc: raise HTTPException(status_code=500, detail=f"Could not build dashboard summary: {exc}")

@app.get("/api/v1/analytics/categories")
def get_category_analytics():
    try: return {"items":sales_by_category(get_orders())}
    except Exception as exc: raise HTTPException(status_code=500, detail=f"Could not build category analytics: {exc}")

@app.get("/api/v1/analytics/delivery-by-state")
def get_delivery_by_state():
    try: return {"items":delivery_by_state(get_orders())}
    except Exception as exc: raise HTTPException(status_code=500, detail=f"Could not build delivery analytics: {exc}")

@app.post("/api/v1/what-if")
def what_if(request: WhatIfRequest):
    try: return run_what_if(get_orders(), request)
    except Exception as exc: raise HTTPException(status_code=500, detail=f"What-if simulation failed: {exc}")

@app.post("/api/v1/segments/retrain", status_code=202)
def retrain_segments(background_tasks: BackgroundTasks):
    """Trigger current-Gold RFM extraction and KMeans retraining; returns a job ID."""
    try:
        job = start_retraining_job()
        if job['status'] == 'queued': background_tasks.add_task(run_retraining_job, job['job_id'])
        return job
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not start segmentation retraining: {exc}")

@app.get("/api/v1/segments/retrain/{job_id}")
def retraining_status(job_id: str):
    job = get_retraining_job(job_id)
    if job is None: raise HTTPException(status_code=404, detail="Job not found. In-process job status is lost after API restart.")
    return job

@app.get("/api/v1/segments")
def list_segments():
    try:
        rows = get_latest_segment_summary()
        return {'segment_count':len(rows), 'total_customers':sum(int(r['customer_count']) for r in rows), 'items':rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not read segment summary; call POST /api/v1/segments/retrain first if tables are missing: {exc}")

@app.get("/api/v1/segments/{cluster_id}/customers")
def segment_customers(cluster_id: int, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)):
    if cluster_id not in (0,1,2,3): raise HTTPException(status_code=404, detail="cluster_id must be one of 0, 1, 2, 3")
    try: return get_segment_customers(cluster_id, limit, offset)
    except Exception as exc: raise HTTPException(status_code=500, detail=f"Could not read customers for segment: {exc}")
