import pandas as pd
import numpy as np
import json
import re
from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime

# Seed for workflow consistency
np.random.seed(42)

# ── WORKFLOW STATE TRACKER ──
@dataclass
class WorkflowRun:
    run_id: str
    started_at: str
    status: str = "RUNNING"
    nodes_run: int = 0
    records_in: int = 0
    records_out: int = 0
    errors: List[Dict] = field(default_factory=list)

# ── NODE 1: TRIGGER & CRM EXTRACTION ──
def node_trigger_extract_crm(run: WorkflowRun) -> List[Dict]:
    """n8n Node 1: Simulates an automated Cron Trigger running a CRM SOQL/REST pull."""
    run.nodes_run += 1
    print("[NODE 1] CRM Trigger Activated — Fetching updated sync accounts...")
    
    # Generate 120 batch records from legacy database
    records = [{
        "crm_id": f"CRM-{i:06d}",
        "company_name": f"Company {i}",
        "email": f"contact{i}@company{i}.com" if i != 12 else "malformed_email_at_12",
        "revenue_band": np.random.choice(["SMB", "MID", "ENT"]),
        "last_payment": np.random.choice(["SUCCESS", "FAILED", "PENDING"]),
        "payment_count": int(np.random.randint(1, 50)),
        "raw_notes": "Customer flagged payment failure issues during last checkout checkout window."
    } for i in range(120)]
    
    run.records_in = len(records)
    print(f"  → Success: Extracted {run.records_in} pipeline rows from CRM.")
    return records

# ── NODE 2: DATA VALIDATION FILTER ──
def node_validate(records: List[Dict], run: WorkflowRun) -> List[Dict]:
    """n8n Node 2: If/Else conditional node validating format and integrity."""
    run.nodes_run += 1
    valid_batch = []
    
    email_regex = r'^[\w.-]+@[\w.-]+\.\w+$'
    
    for r in records:
        record_errors = []
        if not re.match(email_regex, r['email']):
            record_errors.append("invalid_email_format")
            
        if record_errors:
            run.errors.append({"crm_id": r['crm_id'], "failures": record_errors})
        else:
            valid_batch.append(r)
            
    invalid_count = len(records) - len(valid_batch)
    print(f"[NODE 2] Integrity Filter — {len(valid_batch)} records passed, {invalid_count} rejected.")
    return valid_batch

# ── NODE 3: AI PIPELINE ENRICHMENT ──
def node_ai_enrich(records: List[Dict], run: WorkflowRun) -> List[Dict]:
    """n8n Node 3: HTTP Request node calling downstream LLM / FastAPI models."""
    run.nodes_run += 1
    enriched_batch = []
    
    for r in records:
        # Simulating automated ML predictive scoring
        r['predicted_churn_risk'] = np.random.choice(['LOW', 'MEDIUM', 'HIGH'], p=[0.7, 0.2, 0.1])
        # Simulating generative LLM call summarizing messy log text
        r['notes_summary'] = "Payment pipeline checkout failure noted; immediate client follow-up needed."
        r['enriched_at'] = datetime.utcnow().isoformat()
        enriched_batch.append(r)
        
    print(f"[NODE 3] AI Pipeline Gateway — {len(enriched_batch)} accounts semantic-enriched.")
    return enriched_batch

# ── NODE 4: WRITE BACK ──
def node_write_back(records: List[Dict], run: WorkflowRun) -> None:
    """n8n Node 4: Data outbound node writing back to target system endpoints."""
    run.nodes_run += 1
    run.records_out = len(records)
    print(f"[NODE 4] Write Back Outbound — {len(records)} updates synced to CRM and analytics warehouse.")

# ── NODE 5: SLACK ALERTS & GOVERNANCE REPORT ──
def node_notify(run: WorkflowRun) -> None:
    """n8n Node 5: Triggers notification webhooks and serializes metadata runtime logs."""
    run.nodes_run += 1
    run.status = "COMPLETED"
    success_rate = (run.records_out / run.records_in) * 100
    
    print(f"""
[NODE 5] Workflow Run Concluded — Final Execution State
  ======================================================
  • Run ID:        {run.run_id}
  • Nodes Invoked: {run.nodes_run}
  • Records In:    {run.records_in}
  • Records Out:   {run.records_out}
  • Sync Rate:     {success_rate:.1f}%
  • Intercepts:    {len(run.errors)} data structural exceptions noted.
  • Status Code:   {run.status}
  
  → Post Status Webhook Sent to: #crm-automation Live ✓
  """)

# ── ORCHESTRATE GRAPH EXECUTION ──
if __name__ == "__main__":
    print("=" * 65)
    print("n8n Workflow Execution Simulation: CRM → AI Pipeline Loop")
    print("=" * 65)
    
    tracker = WorkflowRun(
        run_id=f"RUN-{datetime.utcnow().strftime('%Y%m%d-%H%M')}",
        started_at=datetime.utcnow().isoformat()
    )
    
    extracted = node_trigger_extract_crm(tracker)
    validated = node_validate(extracted, tracker)
    enriched  = node_ai_enrich(validated, tracker)
    node_write_back(enriched, tracker)
    node_notify(tracker)
