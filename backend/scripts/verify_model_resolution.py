"""
Model Resolution & Rate-Limit Verification Script

Queries the Gemini API to determine:
1. What model name 'gemini-flash-latest' actually resolves to
2. What rate-limit headers or quota info the API returns
3. Lists all available models matching 'flash' in their name
"""

import os
import sys
import json

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
    print("GEMINI MODEL RESOLUTION & RATE-LIMIT VERIFICATION")
    print("=" * 80)

    try:
        from google import genai
    except ImportError:
        print("ERROR: google-genai SDK not installed. Run: pip install google-genai")
        return

    client = genai.Client(api_key=api_key)

    # ── Step 1: List all available models matching 'flash' ─────────────────
    print("\n[STEP 1] Listing available Flash models from API...")
    try:
        all_models = list(client.models.list())
        flash_models = [m for m in all_models if 'flash' in (m.name or '').lower()]
        print(f"  Total models returned: {len(all_models)}")
        print(f"  Flash-family models found: {len(flash_models)}")
        for m in flash_models:
            display = getattr(m, 'display_name', '') or ''
            desc = getattr(m, 'description', '') or ''
            print(f"    - {m.name}  (display: {display})")
    except Exception as e:
        print(f"  ERROR listing models: {e}")

    # ── Step 2: Resolve 'gemini-flash-latest' by fetching model info ───────
    aliases_to_check = [
        "gemini-flash-latest",
        "gemini-2.0-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.6-flash",
        "gemini-3.8-flash",
    ]

    print("\n[STEP 2] Checking model alias resolution...")
    for alias in aliases_to_check:
        try:
            model_info = client.models.get(model=alias)
            print(f"  '{alias}' -> resolved name: {model_info.name}")
            print(f"     display_name: {getattr(model_info, 'display_name', 'N/A')}")
            print(f"     version: {getattr(model_info, 'version', 'N/A')}")
        except Exception as e:
            print(f"  '{alias}' -> FAILED: {e}")

    # ── Step 3: Make a real API call and inspect rate-limit headers ────────
    print("\n[STEP 3] Making a real API call with 'gemini-flash-latest'...")
    try:
        response = client.models.generate_content(
            model="gemini-flash-latest",
            contents="Respond with exactly one word: hello"
        )
        print(f"  Response text: {response.text}")
        print(f"  Model used (from response): {getattr(response, 'model', 'N/A')}")

        # Check for usage metadata
        usage = getattr(response, 'usage_metadata', None)
        if usage:
            print(f"  Usage metadata: prompt_tokens={getattr(usage, 'prompt_token_count', 'N/A')}, "
                  f"candidates_tokens={getattr(usage, 'candidates_token_count', 'N/A')}, "
                  f"total_tokens={getattr(usage, 'total_token_count', 'N/A')}")

        # Check model_version
        model_version = getattr(response, 'model_version', None)
        if model_version:
            print(f"  Resolved model_version: {model_version}")

        # Inspect all response attributes for rate-limit info
        print(f"\n  All response attributes:")
        for attr in dir(response):
            if attr.startswith('_'):
                continue
            try:
                val = getattr(response, attr)
                if not callable(val):
                    print(f"    {attr} = {val}")
            except Exception:
                pass

    except Exception as e:
        error_str = str(e)
        print(f"  API call failed: {error_str}")
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            print(f"\n  ** RATE LIMIT HIT! Full error body: **")
            print(f"  {error_str}")

    # ── Step 4: Rapid-fire requests to try triggering 429 ─────────────────
    print("\n[STEP 4] Rapid-fire 5 requests to check for RPM rate-limit response...")
    for i in range(5):
        try:
            r = client.models.generate_content(
                model="gemini-flash-latest",
                contents=f"Reply with just the number {i}"
            )
            model_ver = getattr(r, 'model_version', 'N/A')
            print(f"  Request {i+1}: OK (model_version={model_ver}, text={r.text.strip()[:30]})")
        except Exception as e:
            error_str = str(e)
            print(f"  Request {i+1}: ERROR - {error_str[:200]}")
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print(f"\n  ** RPM RATE LIMIT HIT on request {i+1}! **")
                print(f"  Full error: {error_str}")
                break

    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
