"""
Empirical Quota Verification Script for gemini-3.5-flash-lite

Tests:
1. REST API call with raw headers inspection (x-ratelimit-*, x-goog-*, etc.)
2. google-genai SDK call
3. Burst/concurrency check to inspect any 429 quota payload
"""

import os
import sys
import json
import requests

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, "..", ".env"))

def main():
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not found in environment")
        return

    print("=" * 80)
    print("EMPIRICAL QUOTA VERIFICATION FOR gemini-3.5-flash-lite")
    print("=" * 80)

    # ── Step 1: Raw REST Request with Header Inspection ──────────────────
    print("\n[STEP 1] Direct REST API request to inspect HTTP response headers...")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": "Reply with 'pong'"}]}]
    }
    headers = {"Content-Type": "application/json"}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
        print(f"  HTTP Status: {resp.status_code}")
        print("  Response Headers:")
        for k, v in resp.headers.items():
            if any(term in k.lower() for term in ["rate", "quota", "limit", "goog"]):
                print(f"    {k}: {v}")
        
        if resp.status_code == 200:
            data = resp.json()
            print("  Response Body snippet:", json.dumps(data)[:200])
        elif resp.status_code == 429:
            print("  429 RATE LIMIT ENCOUNTERED:")
            print(json.dumps(resp.json(), indent=2))
        else:
            print(f"  Status: {resp.status_code}, Body: {resp.text[:300]}")
    except Exception as e:
        print(f"  REST request failed: {e}")

    # ── Step 2: SDK Client Resolution ────────────────────────────────────
    print("\n[STEP 2] Querying SDK model details...")
    from google import genai
    client = genai.Client(api_key=api_key)

    try:
        m = client.models.get(model="gemini-3.5-flash-lite")
        print(f"  Model Name: {m.name}")
        print(f"  Display Name: {getattr(m, 'display_name', 'N/A')}")
        print(f"  Version: {getattr(m, 'version', 'N/A')}")
        print(f"  Input Token Limit: {getattr(m, 'input_token_limit', 'N/A')}")
        print(f"  Output Token Limit: {getattr(m, 'output_token_limit', 'N/A')}")
    except Exception as e:
        print(f"  SDK model get failed: {e}")

    # ── Step 3: Test Request Sequence ───────────────────────────────────
    print("\n[STEP 3] Sending requests to gemini-3.5-flash-lite to test limit behavior...")
    success_count = 0
    for i in range(1, 26):
        try:
            r = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=f"Say the number {i}"
            )
            success_count += 1
            print(f"  Request {i}: SUCCESS (text: '{r.text.strip()}')")
        except Exception as e:
            err = str(e)
            print(f"  Request {i}: EXCEPTION: {err}")
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                print(f"\n  >>> 429 HIT ON REQUEST {i} <<<")
                print(f"  Full Error: {err}")
                break

    print(f"\n  Total successful calls in test: {success_count}")

    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
