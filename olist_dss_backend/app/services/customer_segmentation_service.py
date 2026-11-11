"""On-demand RFM extraction, KMeans retraining and SQL Server persistence."""
from __future__ import annotations
import os, threading, uuid
from datetime import datetime, timezone
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
from app.config import DATABASE_URL, DATA_MODE, MODEL_PATH, RANDOM_SEED, BASE_DIR

JOB_LOCK = threading.Lock()
JOBS: dict[str, dict] = {}
ACTIVE_JOB_ID: str | None = None

RFM_SQL = text("""
WITH AnalysisDate AS (
 SELECT MAX(d.full_date) AS analysis_date
 FROM gold.fact_order_item f JOIN gold.dim_date d ON f.date_key=d.date_key
 WHERE f.order_status=N'delivered'
), CustomerOrders AS (
 SELECT c.customer_unique_id, f.order_id, MAX(d.full_date) AS order_date,
        SUM(CAST(f.price AS DECIMAL(18,2))) AS order_value
 FROM gold.fact_order_item f
 JOIN gold.dim_customer c ON f.customer_key=c.customer_key
 JOIN gold.dim_date d ON f.date_key=d.date_key
 WHERE f.order_status=N'delivered' AND c.customer_unique_id IS NOT NULL
 GROUP BY c.customer_unique_id, f.order_id
), CustomerRFM AS (
 SELECT co.customer_unique_id,
        DATEDIFF(DAY, MAX(co.order_date), ad.analysis_date) AS recency_days,
        COUNT_BIG(co.order_id) AS frequency, SUM(co.order_value) AS monetary
 FROM CustomerOrders co CROSS JOIN AnalysisDate ad
 GROUP BY co.customer_unique_id, ad.analysis_date
)
SELECT customer_unique_id, recency_days, frequency,
       CAST(monetary AS DECIMAL(18,2)) AS monetary
FROM CustomerRFM ORDER BY customer_unique_id
""")

CREATE_TABLES_SQL = [
 "IF SCHEMA_ID('dss') IS NULL EXEC('CREATE SCHEMA dss')",
 """IF OBJECT_ID('dss.customer_segments','U') IS NULL BEGIN
 CREATE TABLE dss.customer_segments (
  customer_id NVARCHAR(100) NOT NULL PRIMARY KEY,
  cluster_id INT NOT NULL CHECK (cluster_id BETWEEN 0 AND 3),
  segment_name NVARCHAR(100) NOT NULL,
  recency_days INT NOT NULL, frequency BIGINT NOT NULL, monetary DECIMAL(18,2) NOT NULL,
  model_version NVARCHAR(64) NOT NULL, trained_at DATETIME2(0) NOT NULL);
 CREATE INDEX IX_customer_segments_cluster ON dss.customer_segments(cluster_id);
 END""",
 "IF COL_LENGTH('dss.customer_segments','segment_name') IS NULL ALTER TABLE dss.customer_segments ADD segment_name NVARCHAR(100) NULL",
 "IF COL_LENGTH('dss.customer_segments','recency_days') IS NULL ALTER TABLE dss.customer_segments ADD recency_days INT NULL",
 "IF COL_LENGTH('dss.customer_segments','frequency') IS NULL ALTER TABLE dss.customer_segments ADD frequency BIGINT NULL",
 "IF COL_LENGTH('dss.customer_segments','monetary') IS NULL ALTER TABLE dss.customer_segments ADD monetary DECIMAL(18,2) NULL",
 "IF COL_LENGTH('dss.customer_segments','model_version') IS NULL ALTER TABLE dss.customer_segments ADD model_version NVARCHAR(64) NULL",
 "IF COL_LENGTH('dss.customer_segments','trained_at') IS NULL ALTER TABLE dss.customer_segments ADD trained_at DATETIME2(0) NULL",
 """IF OBJECT_ID('dss.customer_segment_summary','U') IS NULL BEGIN
 CREATE TABLE dss.customer_segment_summary (
  cluster_id INT NOT NULL PRIMARY KEY CHECK (cluster_id BETWEEN 0 AND 3),
  customer_count BIGINT NOT NULL, avg_recency_days FLOAT NOT NULL, median_recency_days FLOAT NOT NULL,
  avg_frequency FLOAT NOT NULL, median_frequency FLOAT NOT NULL,
  avg_monetary DECIMAL(18,2) NOT NULL, median_monetary DECIMAL(18,2) NOT NULL,
  total_monetary DECIMAL(18,2) NOT NULL, customer_percentage FLOAT NOT NULL,
  silhouette_score FLOAT NULL, segment_name NVARCHAR(100) NULL, model_version NVARCHAR(64) NOT NULL, trained_at DATETIME2(0) NOT NULL);
 END""",
 "IF COL_LENGTH('dss.customer_segment_summary','silhouette_score') IS NULL ALTER TABLE dss.customer_segment_summary ADD silhouette_score FLOAT NULL",
 "IF COL_LENGTH('dss.customer_segment_summary','segment_name') IS NULL ALTER TABLE dss.customer_segment_summary ADD segment_name NVARCHAR(100) NULL",
 "IF COL_LENGTH('dss.customer_segment_summary','model_version') IS NULL ALTER TABLE dss.customer_segment_summary ADD model_version NVARCHAR(64) NULL",
 "IF COL_LENGTH('dss.customer_segment_summary','trained_at') IS NULL ALTER TABLE dss.customer_segment_summary ADD trained_at DATETIME2(0) NULL",
 """IF OBJECT_ID('dss.customer_segment_model_runs','U') IS NULL BEGIN
 CREATE TABLE dss.customer_segment_model_runs (
  model_version NVARCHAR(64) NOT NULL PRIMARY KEY, trained_at DATETIME2(0) NOT NULL,
  customer_count BIGINT NOT NULL, cluster_count INT NOT NULL,
  silhouette_score FLOAT NULL, status NVARCHAR(20) NOT NULL);
 END"""
]

def _engine():
    if DATA_MODE != 'sql':
        raise ValueError("Retraining requires DSS_DATA_MODE=sql; demo data must not be used for production training.")
    if not DATABASE_URL:
        raise ValueError("Set DSS_DATABASE_URL in .env before retraining.")
    return create_engine(DATABASE_URL, pool_pre_ping=True, future=True)

def _create_tables(conn):
    for stmt in CREATE_TABLES_SQL:
        conn.execute(text(stmt))

def extract_latest_rfm(engine) -> pd.DataFrame:
    with engine.connect() as conn:
        df = pd.read_sql_query(RFM_SQL, conn)
    required = {'customer_unique_id', 'recency_days', 'frequency', 'monetary'}
    missing = required - set(df.columns)
    if missing: raise ValueError(f"Gold RFM query missing columns: {sorted(missing)}")
    for col in ('recency_days', 'frequency', 'monetary'):
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['customer_unique_id'] = df['customer_unique_id'].astype('string').str.strip()
    df = df.dropna(subset=['customer_unique_id','recency_days','frequency','monetary'])
    df = df[df.customer_unique_id.ne('')].drop_duplicates('customer_unique_id', keep='last')
    df = df[(df.recency_days >= 0) & (df.frequency >= 1) & (df.monetary > 0)].copy()
    if len(df) < 10: raise ValueError(f"Only {len(df)} valid customers found in Gold; at least 10 are required.")
    return df

def _fit_kmeans(rfm: pd.DataFrame):
    features = pd.DataFrame({
      'recency_log': np.log1p(rfm.recency_days.astype(float)),
      'frequency_log': np.log1p(rfm.frequency.astype(float)),
      'monetary_log': np.log1p(rfm.monetary.astype(float)),
    }, index=rfm.index)
    scaler = StandardScaler(); X = scaler.fit_transform(features)
    model = KMeans(n_clusters=4, random_state=RANDOM_SEED, n_init=10)
    labels = model.fit_predict(X)
    score = float(silhouette_score(X, labels, sample_size=min(10000,len(rfm)), random_state=RANDOM_SEED))
    result = rfm.copy(); result['cluster_id'] = labels.astype(int)
    summary = result.groupby('cluster_id').agg(
      customer_count=('customer_unique_id','count'), avg_recency_days=('recency_days','mean'),
      median_recency_days=('recency_days','median'), avg_frequency=('frequency','mean'),
      median_frequency=('frequency','median'), avg_monetary=('monetary','mean'),
      median_monetary=('monetary','median'), total_monetary=('monetary','sum')).reset_index()
    if set(summary.cluster_id.astype(int)) != {0,1,2,3}:
        raise ValueError('KMeans did not produce all four non-empty clusters. Results were not saved.')
    summary['customer_percentage'] = summary.customer_count / len(result) * 100
    # Cluster IDs are arbitrary and may be permuted on every retrain. Derive business labels from RFM profile.
    remaining = set(summary.cluster_id.astype(int))
    names = {}
    high_repeat = summary.sort_values(['avg_frequency','avg_monetary'], ascending=False).iloc[0]
    names[int(high_repeat.cluster_id)] = 'Repeat Buyers, High Monetary'
    remaining.remove(int(high_repeat.cluster_id))
    recent = summary[summary.cluster_id.isin(remaining)].sort_values(['avg_recency_days','avg_frequency'], ascending=[True,False]).iloc[0]
    names[int(recent.cluster_id)] = 'Recently Active, Low Frequency'
    remaining.remove(int(recent.cluster_id))
    high_value_inactive = summary[summary.cluster_id.isin(remaining)].sort_values(['avg_monetary','avg_recency_days'], ascending=[False,False]).iloc[0]
    names[int(high_value_inactive.cluster_id)] = 'High Monetary, Inactive'
    remaining.remove(int(high_value_inactive.cluster_id))
    names[next(iter(remaining))] = 'Low Monetary, Inactive'
    summary['segment_name'] = summary.cluster_id.astype(int).map(names)
    result['segment_name'] = result.cluster_id.astype(int).map(names)
    return model, scaler, result, summary, score, list(features.columns)

def _persist(engine, result, summary, score, version, trained_at):
    with engine.begin() as conn:
        _create_tables(conn)
        conn.execute(text('DELETE FROM dss.customer_segments'))
        conn.execute(text('DELETE FROM dss.customer_segment_summary'))
        assignments = result[['customer_unique_id','cluster_id','recency_days','frequency','monetary']].rename(columns={'customer_unique_id':'customer_id'})
        assignments['segment_name']=result['segment_name'].values
        assignments['model_version']=version; assignments['trained_at']=trained_at
        conn.execute(text("""INSERT INTO dss.customer_segments
          (customer_id,cluster_id,segment_name,recency_days,frequency,monetary,model_version,trained_at)
          VALUES (:customer_id,:cluster_id,:segment_name,:recency_days,:frequency,:monetary,:model_version,:trained_at)"""), assignments.to_dict('records'))
        summary=summary.copy(); summary['silhouette_score']=score; summary['model_version']=version; summary['trained_at']=trained_at
        conn.execute(text("""INSERT INTO dss.customer_segment_summary
          (cluster_id,customer_count,avg_recency_days,median_recency_days,avg_frequency,median_frequency,
           avg_monetary,median_monetary,total_monetary,customer_percentage,silhouette_score,segment_name,model_version,trained_at)
          VALUES (:cluster_id,:customer_count,:avg_recency_days,:median_recency_days,:avg_frequency,:median_frequency,
           :avg_monetary,:median_monetary,:total_monetary,:customer_percentage,:silhouette_score,:segment_name,:model_version,:trained_at)"""), summary.to_dict('records'))
        conn.execute(text("""INSERT INTO dss.customer_segment_model_runs
          (model_version,trained_at,customer_count,cluster_count,silhouette_score,status)
          VALUES (:model_version,:trained_at,:customer_count,4,:silhouette_score,'succeeded')"""),
          {'model_version':version,'trained_at':trained_at,'customer_count':len(result),'silhouette_score':score})

def retrain_customer_segments() -> dict:
    engine = _engine()
    rfm = extract_latest_rfm(engine)
    model, scaler, result, summary, score, feature_columns = _fit_kmeans(rfm)
    trained_at = datetime.now(timezone.utc).replace(tzinfo=None)
    version = 'kmeans4-' + trained_at.strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:6]
    model_path = Path(MODEL_PATH)
    if not model_path.is_absolute(): model_path = BASE_DIR / model_path
    model_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = model_path.with_suffix(model_path.suffix + '.tmp')
    joblib.dump({'model':model,'scaler':scaler,'best_k':4,'feature_columns':feature_columns,
      'model_version':version,'trained_at_utc':trained_at.isoformat(),'silhouette_score':score}, tmp_path)
    _persist(engine,result,summary,score,version,trained_at)
    os.replace(tmp_path,model_path)
    return {'status':'succeeded','model_version':version,'trained_at_utc':trained_at.isoformat()+'Z',
      'customer_count':int(len(result)),'cluster_count':4,'silhouette_score':round(score,5),
      'model_path':str(model_path),'segments':summary[['cluster_id','segment_name','customer_count','customer_percentage']].to_dict('records'),
      'message':'RFM extracted from Gold; K-Means trained; DSS tables updated.'}

def start_retraining_job() -> dict:
    global ACTIVE_JOB_ID
    with JOB_LOCK:
        if ACTIVE_JOB_ID and JOBS.get(ACTIVE_JOB_ID,{}).get('status') in {'queued','running'}:
            return {'job_id':ACTIVE_JOB_ID,'status':JOBS[ACTIVE_JOB_ID]['status'],'message':'A retraining job is already running.'}
        job_id=str(uuid.uuid4()); JOBS[job_id]={'job_id':job_id,'status':'queued','created_at_utc':datetime.now(timezone.utc).isoformat()}
        ACTIVE_JOB_ID=job_id
        return dict(JOBS[job_id])

def run_retraining_job(job_id: str):
    global ACTIVE_JOB_ID
    with JOB_LOCK:
        if job_id not in JOBS: return
        JOBS[job_id]['status']='running'; JOBS[job_id]['started_at_utc']=datetime.now(timezone.utc).isoformat()
    try:
        result=retrain_customer_segments()
        with JOB_LOCK: JOBS[job_id].update(result)
    except Exception as exc:
        with JOB_LOCK: JOBS[job_id].update({'status':'failed','error':str(exc)})
    finally:
        with JOB_LOCK:
            JOBS[job_id]['finished_at_utc']=datetime.now(timezone.utc).isoformat()
            if ACTIVE_JOB_ID==job_id: ACTIVE_JOB_ID=None

def get_retraining_job(job_id: str):
    with JOB_LOCK:
        return dict(JOBS[job_id]) if job_id in JOBS else None

def get_latest_segment_summary():
    engine=_engine()
    query=text("""SELECT cluster_id,customer_count,avg_recency_days,median_recency_days,avg_frequency,median_frequency,
      avg_monetary,median_monetary,total_monetary,customer_percentage,silhouette_score,segment_name,model_version,trained_at
      FROM dss.customer_segment_summary ORDER BY cluster_id""")
    with engine.connect() as conn: rows=[dict(r._mapping) for r in conn.execute(query)]
    for row in rows:
        if row.get('trained_at'): row['trained_at']=row['trained_at'].isoformat()
        for k,v in list(row.items()):
            if isinstance(v,np.integer): row[k]=int(v)
            elif isinstance(v,np.floating): row[k]=float(v)
    return rows

def get_segment_customers(cluster_id: int, limit: int, offset: int):
    engine=_engine()
    count_q=text('SELECT COUNT_BIG(*) FROM dss.customer_segments WHERE cluster_id=:cluster_id')
    data_q=text('''SELECT customer_id,cluster_id,segment_name,recency_days,frequency,monetary,model_version,trained_at
      FROM dss.customer_segments WHERE cluster_id=:cluster_id ORDER BY customer_id
      OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY''')
    with engine.connect() as conn:
        total=int(conn.execute(count_q,{'cluster_id':cluster_id}).scalar_one())
        rows=[dict(r._mapping) for r in conn.execute(data_q,{'cluster_id':cluster_id,'offset':offset,'limit':limit})]
    for row in rows:
        if row.get('trained_at'): row['trained_at']=row['trained_at'].isoformat()
        for k,v in list(row.items()):
            if isinstance(v,np.integer): row[k]=int(v)
            elif isinstance(v,np.floating): row[k]=float(v)
    return {'cluster_id':cluster_id,'total':total,'limit':limit,'offset':offset,'items':rows}
