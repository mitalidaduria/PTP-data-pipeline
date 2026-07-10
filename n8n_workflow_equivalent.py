import pandas as pd
import numpy as np
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime

np.random.seed(42)

@dataclass
class WorkflowRun:
    run_id:     str
    started_at: str
    status:     str = "RUNNING"
    nodes_run:  int = 0
    records_in: int = 0
    records_out:int = 0
    errors:     List[str] = None
    def __post_init__(self): self.errors = []

def node_trigger_extract_crm(run: WorkflowRun) -> List[Dict]:
    run.nodes_run += 1
    print("[NODE 1] CRM Extract — fetching yesterday's updated records")
    records = [{
        "crm_id": f"CRM-{i:06d}",
        "company_name": f"Company {i}",
        "email": f"contact{i}@company{i}.com",
        "revenue_band": np.random.choice(["SMB", "MID", "ENT"]),
        "last_payment": np.random.choice(["SUCCESS", "FAILED", "PENDING"]),
        "payment_count": int(np.random.randint(1, 50)),
        "raw_notes": "Customer called re: last payment failure on 2024-01-14"
    } for i in range(120)]
    run.records_in = len(records)
    print(f"  → Extracted {run.records_in} records from CRM")
    return records

def node_validate(records: List[Dict], run: WorkflowRun) -> List[Dict]:
    run.nodes_run += 1
    valid = []
    for r in records:
        errors = []
        if not re.match(r'^[\w.-]+@[\w.-]+\.\w+$', r.get('email', '')):
            errors.append("invalid email format")
        if errors:
            run.errors.append({'record': r['crm_id'], 'errors': errors})
        else:
            valid.append(r)
    invalid = len(records) - len(valid)
    print(f"[NODE 2] Validation — {len(valid)} valid, {invalid} rejected")
    return valid

def node_ai_enrich(records: List[Dict], run: WorkflowRun) -> List[Dict]:
    run.nodes_run += 1
    enriched = []
    for r in records:
        r['predicted_churn_risk'] = np.random.choice(['LOW', 'MEDIUM', 'HIGH'], p=[0.6, 0.3, 0.1])
        r['notes_summary'] = "Customer reported payment failure; follow-up required."
        r['enriched_at'] = datetime.utcnow().isoformat()
        enriched.append(r)
    print(f"[NODE 3] AI Enrichment — {len(enriched)} records enriched")
    return enriched

def node_write_back(records: List[Dict], run: WorkflowRun) -> None:
    run.nodes_run += 1
    run.records_out = len(records)
    print(f"[NODE 4] Write Back — {len(records)} records written to CRM + warehouse")

def node_notify(run: WorkflowRun) -> None:
    run.nodes_run += 1
    run.status = "COMPLETED"
    success_rate = run.records_out / run.records_in * 100
    print(f"""
[NODE 5] Workflow Complete — Governance Report
  Run ID:       {run.run_id}
  Records in:   {run.records_in}
  Records out:  {run.records_out}
  Success rate: {success_rate:.1f}%
  Errors:       {len(run.errors)}
  Nodes run:    {run.nodes_run}
  Status:       {run.status}
  → Slack: #crm-automation — Daily CRM sync complete ✓
""")

if __name__ == "__main__":
    print("=" * 60)
    print("n8n WORKFLOW: CRM → AI Pipeline → Data Warehouse")
    print("=" * 60)
    run = WorkflowRun(run_id=f"RUN-{datetime.utcnow().strftime('%Y%m%d-%H%M')}", started_at=datetime.utcnow().isoformat())
    raw_records = node_trigger_extract_crm(run)
    valid_records = node_validate(raw_records, run)
    enriched_records = node_ai_enrich(valid_records, run)
    node_write_back(enriched_records, run)
    node_notify(run)
