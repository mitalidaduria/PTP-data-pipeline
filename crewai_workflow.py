from crewai import Agent, Task, Crew, Process
from crewai.tools import BaseTool
from pydantic import BaseModel
import pandas as pd
import numpy as np
import json
import os
from typing import Type

# ── CUSTOM TOOLS ─────────────────────────────────────────────
class PaymentDataInput(BaseModel):
    gateway: str = "all"
    days: int = 7

class FetchPaymentDataTool(BaseTool):
    name: str = "fetch_payment_failure_data"
    description: str = "Fetch payment failure summary statistics from the data warehouse."
    args_schema: Type[BaseModel] = PaymentDataInput

    def _run(self, gateway: str = "all", days: int = 7) -> str:
        np.random.seed(42)
        gateways = ['RazorpayV2', 'PayU_Enterprise', 'HDFC_SmartPay']
        data = [{
            'gateway': g,
            'total_failures': int(np.random.randint(800, 2000)),
            'failure_rate_pct': round(np.random.uniform(1.5, 4.0), 2),
            'top_category': np.random.choice(['GATEWAY_TIMEOUT', 'BANK_REJECTION']),
            'avg_resolution_mins': int(np.random.randint(12, 45)),
            'stp_rate_pct': round(np.random.uniform(76, 84), 1)
        } for g in (gateways if gateway == 'all' else [gateway])]
        return json.dumps(data, indent=2)

class DQStatusInput(BaseModel):
    severity: str = "all"

class GetDQStatusTool(BaseTool):
    name: str = "get_dq_status"
    description: str = "Get current data quality monitoring status and active breaches."
    args_schema: Type[BaseModel] = DQStatusInput

    def _run(self, severity: str = "all") -> str:
        return json.dumps({
            "total_rules": 18,
            "passing": 16,
            "breaching": 2,
            "breaches": [
                {"rule": "DQ-003", "severity": "HIGH", "issue": "amount null rate 0.08% vs threshold 0.05%"},
                {"rule": "DQ-015", "severity": "LOW", "issue": "GATEWAY_TIMEOUT at 41% of failures (threshold 40%)"}
            ]
        }, indent=2)

# ── AGENT 1: DATA RESEARCH AGENT ─────────────────────────────
data_researcher = Agent(
    role="Senior Data Research Analyst",
    goal="""Gather comprehensive payment failure data across all gateways
    for the past 7 days. Fetch both failure statistics and DQ monitoring
    status. Produce a structured summary for the analyst.""",
    backstory="""You are a Senior Data Analyst specialising in payments data.
    You have deep knowledge of the PITAP system's 8 failure categories
    and 3 gateway sources. Your job is to gather accurate, complete data
    before any analysis begins. You never skip a data source.""",
    tools=[FetchPaymentDataTool(), GetDQStatusTool()],
    verbose=True,
    allow_delegation=False
)

# ── AGENT 2: PAYMENT ANALYTICS AGENT ─────────────────────────
payment_analyst = Agent(
    role="Payment Intelligence Analyst",
    goal="""Analyse the gathered payment failure data, identify anomalies
    and trends, compare against SLA targets (STP ≥ 81%, P95 < 300ms),
    and produce a concise executive summary with prioritised actions.""",
    backstory="""You are a Payment Intelligence Analyst at a FinTech company.
    You understand the business consequence of each failure category.
    FRAUD_BLOCK issues are always Priority 1. You produce structured
    reports that Risk, Operations, and Product teams can act on immediately.""",
    tools=[],
    verbose=True,
    allow_delegation=False
)

# ── TASKS ────────────────────────────────────────────────────
research_task = Task(
    description="""Fetch payment failure statistics for ALL gateways
    for the past 7 days. Also fetch the current DQ monitoring status.
    Return a structured summary including: per-gateway failure rates,
    STP rates, top failure categories, and any active DQ breaches.""",
    expected_output="""A structured JSON summary with:
    - gateway_stats: list of per-gateway metrics
    - dq_status: current DQ monitoring state and any breaches
    - data_period: the time range covered""",
    agent=data_researcher
)

analysis_task = Task(
    description="""Using the research summary, produce an executive report:
    1. Which gateway is underperforming vs SLA targets?
    2. Are any DQ breaches business-critical?
    3. What is the STP trend vs the 81% target?
    4. Prioritised action items (Priority 1 = immediate, P2 = this sprint).
    Format as a structured executive summary.""",
    expected_output="""Executive summary with:
    - Overall health status (GREEN / AMBER / RED)
    - Top 3 insights with evidence
    - Prioritised action list with owner and deadline
    - SLA compliance status""",
    agent=payment_analyst,
    context=[research_task]
)

# ── CREW ASSEMBLY ────────────────────────────────────────────
crew = Crew(
    agents=[data_researcher, payment_analyst],
    tasks=[research_task, analysis_task],
    process=Process.sequential,
    verbose=True
)

if __name__ == "__main__":
    print("=" * 60)
    print("CrewAI Architecture Simulation Initialized Successfully")
    print("=" * 60)
    print("Agent 1 (Data Researcher) -> Configured with Retrieval Tools.")
    print("Agent 2 (Payment Analyst) -> Configured for SLA Compliance Reasonings.")
    print("\n[SUCCESS] Multi-Agent graph compiled cleanly.")
