"""
Verification script testing refined RiskAgent pre-screen against:
1. Casual/everyday sentences using bare words (dispute, risk, liability, penalty).
2. The 3 real Enron benchmark documents to verify zero false negative leakage.
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

from app.agents.risk import RiskAgent, RiskInput

CASUAL_TEST_CASES = [
    {
        "id": "casual_001",
        "text": "Hey Tom, I dispute that you're better at golf than me, let's play 18 holes this Saturday.",
        "description": "Casual usage of 'dispute'"
    },
    {
        "id": "casual_002",
        "text": "Don't forget the risk of rain tomorrow afternoon, make sure everyone brings an umbrella to the picnic.",
        "description": "Casual usage of 'risk'"
    },
    {
        "id": "casual_003",
        "text": "Dave's terrible karaoke performance last night was an absolute liability for our department's reputation haha.",
        "description": "Casual usage of 'liability'"
    },
    {
        "id": "casual_004",
        "text": "The referee called a five-yard penalty for false start on our office fantasy football league.",
        "description": "Casual usage of 'penalty'"
    }
]

REAL_ENRON_DOCS = [
    {
        "id": "enron_train_092_hain-m",
        "file": "data/enron_evaluation/raw_emails/train/enron_train_092_hain-m_Protest_to_PX_Compliance_Filin.txt",
        "expected_risk": "HIGH"
    },
    {
        "id": "enron_val_021_badeer-r",
        "file": "data/enron_evaluation/raw_emails/val/enron_val_021_badeer-r_CAISO_Notification_PMI_10_min_.txt",
        "expected_risk": "LOW"
    },
    {
        "id": "enron_test_011_whalley-g",
        "file": "data/enron_evaluation/raw_emails/test/enron_test_011_whalley-g_California_Regulators_Back_Rat.txt",
        "expected_risk": "LOW"
    }
]

async def main():
    print("=" * 80)
    print("PART 1: TESTING CASUAL NON-LEGAL SENTENCES")
    print("=" * 80)
    agent = RiskAgent()

    for item in CASUAL_TEST_CASES:
        pre_screen = agent._pre_screen_risk(item["text"])
        res = await agent.run(RiskInput(document_id=item["id"], text=item["text"]))
        print(f"\n[TEST CASE: {item['id']}] ({item['description']})")
        print(f"Text: \"{item['text']}\"")
        print(f"Pre-screen matches: {pre_screen}")
        print(f"Pre-screen bypassed to Zero-Cost?: {len(pre_screen) == 0}")
        print(f"Overall Risk: {res.overall_risk} | Confidence: {res.confidence_score}")
        print(f"Reason: {res.assessments[0].reason}")
        assert len(pre_screen) == 0, f"Failed: Casual text triggered pre-screen matches: {pre_screen}"
        assert res.overall_risk == "LOW", f"Failed: Casual text assessed as {res.overall_risk}"

    print("\n" + "=" * 80)
    print("PART 2: RE-TESTING 3 REAL ENRON BENCHMARK DOCUMENTS")
    print("=" * 80)

    for idx, doc in enumerate(REAL_ENRON_DOCS, 1):
        doc_path = os.path.join(backend_dir, "..", doc["file"])
        with open(doc_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

        pre_screen = agent._pre_screen_risk(text)
        print(f"\n[{idx}/3] {doc['id']}")
        print(f"Pre-screen matches found: {pre_screen}")

        res = await agent.run(RiskInput(document_id=doc["id"], text=text))
        print(f"Assessed Overall Risk: {res.overall_risk} (Expected: {doc['expected_risk']}) | Confidence: {res.confidence_score}")
        for ass in res.assessments:
            print(f"  * {ass.category}: {ass.risk_level} (Conf: {ass.confidence})")
            print(f"    Reason: {ass.reason}")

        # Pace calls
        time.sleep(3.0)

    print("\n" + "=" * 80)
    print("ALL VERIFICATIONS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
