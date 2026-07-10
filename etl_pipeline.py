import pandas as pd
import numpy as np
import os
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List
import random

# Seed for reproducibility
random.seed(42)
np.random.seed(42)

# ── LOCAL STORAGE ADAPTER (Simulates AWS S3 Zones) ──
BASE = Path("/tmp/pitap-datalake")
ZONES = {
    'landing': BASE / 'landing',
    'curated': BASE / 'curated',
    'features': BASE / 'features',
    'governance': BASE / 'governance'
}

# Ensure directories exist
for z in ZONES.values():
    z.mkdir(parents=True, exist_ok=True)

# ── GOVERNANCE LOGGER ──
@dataclass
class PipelineRun:
    pipeline_id: str
    run_at: str
    gateway: str
    records_in: int = 0
    records_out: int = 0
    dq_passes: int = 0
    dq_fails: int = 0
    status: str = "RUNNING"
    errors: List[str] = field(default_factory=list)

def log_run(run: PipelineRun):
    """Writes the pipeline execution metadata trail out to the governance log."""
    path = ZONES['governance'] / f"run_{run.pipeline_id}.json"
    path.write_text(json.dumps(vars(run), indent=2))

# ── LAYER 1: EXTRACT (Landing Zone) ──
def extract(gateway: str, run: PipelineRun) -> pd.DataFrame:
    """Extract raw events from gateway and write to immutable landing zone."""
    N = 5000
    raw = pd.DataFrame({
        'txn_id': [f'TXN{i:08d}' for i in range(N)],
        'gateway': gateway,
        'raw_status': np.random.choice(['FAILED', 'TIMEOUT', 'DECLINED'], N),
        'amount_str': [str(round(x, 2)) for x in np.random.exponential(1500, N)],
        'error_code': np.random.choice(['ERR_001', 'ERR_002', 'ERR_FRAUD'], N),
        'event_ts': ['2024-01-15T10:00:00Z'] * N
    })
    
    # Injecting data anomalies for the Data Quality Gate to capture
    raw.loc[0, 'txn_id'] = raw.loc[5, 'txn_id']   # Duplicate ID
    raw.loc[1, 'amount_str'] = 'N/A'               # Malformed non-numeric string

    # Save to Immutable Landing Zone
    landing_path = ZONES['landing'] / f"{gateway}_raw.json"
    raw.to_json(landing_path, orient='records', indent=2)
    
    run.records_in = len(raw)
    print(f"  [EXTRACT] {gateway}: {len(raw):,} raw events → landing zone.")
    return raw

# ── LAYER 2: TRANSFORM + DATA QUALITY GATE (Curated Zone) ──
def transform_and_validate(raw: pd.DataFrame, run: PipelineRun) -> pd.DataFrame:
    """Transform raw JSON to clean Parquet. Evaluate structural DQ gates."""
    df = raw.copy()
    
    # Type-casting and basic feature parsing
    df['amount'] = pd.to_numeric(df['amount_str'], errors='coerce')
    df['event_ts'] = pd.to_datetime(df['event_ts'])
    df['hour_of_day'] = df['event_ts'].dt.hour
    df['is_fraud'] = df['error_code'] == 'ERR_FRAUD'
    
    # Prune messy raw fields
    df = df.drop(columns=['amount_str', 'raw_status'])
    
    # Calculate Quality Gate Metrics
    null_pct = df['amount'].isnull().mean() * 100
    dupl_pct = (len(df) - df['txn_id'].nunique()) / len(df) * 100
    
    # Gate A: Null Verification Check
    if null_pct > 0.5:
        run.errors.append(f"DQ FAIL: amount null_pct={null_pct:.2f}% > 0.5%")
        run.dq_fails += 1
    else:
        run.dq_passes += 1
        
    # Gate B: Uniqueness Verification Check
    if dupl_pct > 0:
        run.errors.append(f"DQ FAIL: txn_id duplicate rate={dupl_pct:.4f}%")
        run.dq_fails += 1
        df = df.drop_duplicates('txn_id')  # Deduplicate prior to curated loading
    else:
        run.dq_passes += 1
        
    run.records_out = len(df)
    print(f"  [TRANSFORM] {run.records_out:,} records clean | DQ: {run.dq_passes} pass, {run.dq_fails} fail.")
    return df

# ── LAYER 3: LOAD (Curated & Feature Zones) ──
def load(df: pd.DataFrame, run: PipelineRun) -> None:
    """Write out analytical-ready Parquet datasets into Curated and Feature zones."""
    # Write to Curated Zone (Athena-ready Columnar Parquet)
    curated_path = ZONES['curated'] / f"{run.gateway}_curated.parquet"
    df.to_parquet(curated_path, index=False)
    
    # Feature Engineering Layer for Downstream ML Models
    features = df[['txn_id', 'gateway', 'amount', 'hour_of_day', 'is_fraud']].copy()
    features['amount_log'] = np.log1p(features['amount'].fillna(0))
    features['is_peak_hour'] = features['hour_of_day'].between(9, 17)
    
    # Write to Feature Zone
    feat_path = ZONES['features'] / f"{run.gateway}_features.parquet"
    features.to_parquet(feat_path, index=False)
    
    run.status = "COMPLETED"
    print(f"  [LOAD] Curated: {curated_path.name} | Features: {feat_path.name}")

# ── PIPELINE ORCHESTRATION LOOP ──
if __name__ == "__main__":
    print("PITAP ETL PIPELINE — Running 3-Layer Storage Architecture")
    print("=" * 65)

    for gateway in ['RazorpayV2', 'PayU_Enterprise', 'HDFC_SmartPay']:
        run = PipelineRun(
            pipeline_id=f"{gateway}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            run_at=datetime.utcnow().isoformat(),
            gateway=gateway
        )
        
        print(f"\nProcessing Gateway: {gateway}")
        raw_data = extract(gateway, run)
        clean_data = transform_and_validate(raw_data, run)
        load(clean_data, run)
        log_run(run)
        
        print(f"  → Pipeline Status: {run.status} | Logged Errors: {len(run.errors)}")

    print("\n✓ Pipeline execution complete! Parquet artifacts successfully stored.")
