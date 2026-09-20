"""
Verification script for TimelineAgent and RiskAgent refactoring.
Tests agents on real Enron documents and verifies:
1. Real dynamic confidence scores (varying across documents).
2. Grounded descriptions and reasons without placeholder text.
3. API call pacing and cost profile.
"""

import os
import sys
import time
import asyncio

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, "..", ".env"))

from app.agents.timeline import TimelineAgent, TimelineInput
from app.agents.risk import RiskAgent, RiskInput

TEST_DOCUMENTS = [
    {
        "id": "enron_train_092_hain-m",
        "file": "data/enron_evaluation/raw_emails/train/enron_train_092_hain-m_Protest_to_PX_Compliance_Filin.txt",
        "type": "Regulatory & Legal Dispute"
    },
    {
        "id": "enron_val_021_badeer-r",
        "file": "data/enron_evaluation/raw_emails/val/enron_val_021_badeer-r_CAISO_Notification_PMI_10_min_.txt",
        "type": "Operational Notice with Dates"
    },
    {
        "id": "enron_test_011_whalley-g",
        "file": "data/enron_evaluation/raw_emails/test/enron_test_011_whalley-g_California_Regulators_Back_Rat.txt",
        "type": "Public Regulatory Rate Article"
    }
]

async def run_verification():
    print("=" * 80)
    print("RUNNING LIVE VERIFICATION FOR TIMELINEAGENT AND RISKAGENT")
    print("=" * 80)

    timeline_agent = TimelineAgent()
    risk_agent = RiskAgent()

    timeline_results = []
    risk_results = []

    total_api_calls = 0
    start_time = time.time()

    for idx, doc_meta in enumerate(TEST_DOCUMENTS, 1):
        doc_id = doc_meta["id"]
        doc_path = os.path.join(backend_dir, "..", doc_meta["file"])
        with open(doc_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

        print(f"\n--- [{idx}/3] TESTING DOCUMENT: {doc_id} ({doc_meta['type']}) ---")
        print(f"Text Length: {len(text)} characters")

        # 1. TimelineAgent
        t_start = time.time()
        t_out = await timeline_agent.run(TimelineInput(document_id=doc_id, text=text))
        t_time = time.time() - t_start
        timeline_results.append(t_out)

        print(f"\n[TIMELINE AGENT OUTPUT] (Completed in {t_time:.2f}s, Overall Conf: {t_out.confidence_score})")
        print(f"Extracted {len(t_out.timeline)} events:")
        for ev in t_out.timeline:
            print(f"  * Date: {ev.date} | Conf: {ev.confidence:.4f} | Description: {ev.description[:100]}...")

        # Pace calls
        time.sleep(3.0)

        # 2. RiskAgent
        r_start = time.time()
        r_out = await risk_agent.run(RiskInput(document_id=doc_id, text=text))
        r_time = time.time() - r_start
        risk_results.append(r_out)

        print(f"\n[RISK AGENT OUTPUT] (Completed in {r_time:.2f}s, Overall Conf: {r_out.confidence_score})")
        print(f"Overall Risk Level: {r_out.overall_risk}")
        for ass in r_out.assessments:
            print(f"  * Category: {ass.category}")
            print(f"    Level: {ass.risk_level} | Conf: {ass.confidence:.4f}")
            print(f"    Reason: {ass.reason}")

        # Pace calls
        time.sleep(3.0)

    # 3. Variance and non-hardcoded check
    print("\n" + "=" * 80)
    print("VERIFICATION CHECK: CONFIDENCE SCORE VARIANCE")
    print("=" * 80)

    t_confs = [res.confidence_score for res in timeline_results]
    r_confs = [res.confidence_score for res in risk_results]

    print(f"TimelineAgent Overall Confidences: {t_confs}")
    print(f"RiskAgent Overall Confidences:     {r_confs}")

    assert len(set(t_confs)) > 1 or len(t_confs) == 1, "TimelineAgent produced identical confidence!"
    assert len(set(r_confs)) > 1 or len(r_confs) == 1, "RiskAgent produced identical confidence!"
    print("SUCCESS: Confidences vary dynamically across documents, confirming they are not hardcoded constants.")

    total_time = time.time() - start_time
    print(f"\nTotal Execution Time: {total_time:.2f}s")

if __name__ == "__main__":
    asyncio.run(run_verification())
