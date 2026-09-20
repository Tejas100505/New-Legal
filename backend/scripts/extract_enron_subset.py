"""
Enron Subset Extractor and Stratified Splitter
Streams live from CMU, filters diverse emails, and organizes into train/val/test splits.
"""

import os
import sys
import io
import re
import json
import email
import hashlib
import tarfile
import random
import requests
from collections import defaultdict

# Ensure immediate unbuffered output
sys.stdout.reconfigure(line_buffering=True)

CMU_URL = "https://www.cs.cmu.edu/~enron/enron_mail_20150507.tar.gz"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BASE_DIR, "data", "enron_evaluation")
RAW_DIR = os.path.join(DATA_DIR, "raw_emails")

TRAIN_DIR = os.path.join(RAW_DIR, "train")
VAL_DIR = os.path.join(RAW_DIR, "val")
TEST_DIR = os.path.join(RAW_DIR, "test")

def clean_subject_slug(subject: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", (subject or "no_subject").strip()).strip("_")
    return clean[:30] if clean else "email"

def extract_body(msg) -> str:
    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        parts.append(payload.decode("latin1", errors="replace"))
                except Exception:
                    pass
        return "\n".join(parts).strip()
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            try:
                return payload.decode("latin1", errors="replace").strip()
            except Exception:
                pass
        raw = msg.get_payload()
        return (str(raw) if raw else "").strip()

def main():
    for d in [TRAIN_DIR, VAL_DIR, TEST_DIR]:
        os.makedirs(d, exist_ok=True)

    print("=" * 80, flush=True)
    print("STREAMING & EXTRACTING 400 ENRON EMAILS FROM LIVE CMU ARCHIVE", flush=True)
    print("=" * 80, flush=True)

    resp = requests.get(CMU_URL, stream=True, timeout=30)
    if resp.status_code != 200:
        print(f"ERROR: Failed to connect to CMU (Status: {resp.status_code})", flush=True)
        return

    print("Connected to CMU stream. Opening tar archive...", flush=True)
    tar = tarfile.open(fileobj=resp.raw, mode="r|gz")

    extracted_records = []
    seen_hashes = set()
    custodian_counts = defaultdict(int)
    MAX_PER_CUSTODIAN = 20
    TARGET_TOTAL = 400

    scanned = 0

    for member in tar:
        if not member.isfile():
            continue

        scanned += 1
        # Fast filter: skip tiny stubs or huge attachments immediately
        if member.size < 350 or member.size > 25000:
            continue

        # Extract custodian: maildir/<custodian>/<folder>/...
        parts = member.name.replace("\\", "/").split("/")
        if len(parts) >= 3 and parts[0] == "maildir":
            custodian = parts[1]
            folder = parts[2]
        else:
            custodian = "general"
            folder = "general"

        if custodian_counts[custodian] >= MAX_PER_CUSTODIAN:
            continue

        f = tar.extractfile(member)
        if not f:
            continue

        raw_bytes = f.read()
        try:
            msg = email.message_from_bytes(raw_bytes)
        except Exception:
            continue

        body = extract_body(msg)

        # Quality criteria:
        # 1. Meaningful body text length (between 150 and 4000 characters)
        if len(body) < 150 or len(body) > 4000:
            continue

        # 2. De-duplication check
        norm_body = re.sub(r"\s+", " ", body.lower().strip())
        b_hash = hashlib.sha256(norm_body.encode("utf-8")).hexdigest()
        if b_hash in seen_hashes:
            continue
        seen_hashes.add(b_hash)

        # 3. Skip purely automated calendar invites with no content
        if "Invitation:" in body and len(body) < 300:
            continue

        subject = (msg.get("Subject") or "No Subject").strip()
        date_str = (msg.get("Date") or "Unknown Date").strip()
        from_str = (msg.get("From") or "Unknown Sender").strip()
        to_str = (msg.get("To") or "Unknown Recipient").strip()

        custodian_counts[custodian] += 1
        record = {
            "index": len(extracted_records),
            "original_path": member.name,
            "custodian": custodian,
            "folder": folder,
            "date": date_str,
            "sender": from_str,
            "recipient": to_str,
            "subject": subject,
            "raw_text": raw_bytes.decode("latin1", errors="replace"),
            "body_text": body,
            "char_length": len(body),
            "sha256": b_hash,
        }
        extracted_records.append(record)

        if len(extracted_records) % 25 == 0:
            print(f"  [Progress] Extracted {len(extracted_records)}/{TARGET_TOTAL} diverse emails across {len(custodian_counts)} custodians (scanned: {scanned})...", flush=True)

        if len(extracted_records) >= TARGET_TOTAL:
            break

    resp.close()
    print(f"\nExtraction complete! Extracted exactly {len(extracted_records)} emails across {len(custodian_counts)} distinct custodians.", flush=True)
    print(f"Total archive members scanned: {scanned}", flush=True)

    # ── Stratified Train/Val/Test Split: 70% (280) / 15% (60) / 15% (60) ──
    random.seed(42)
    shuffled = list(extracted_records)
    random.shuffle(shuffled)

    train_set = shuffled[:280]
    val_set = shuffled[280:340]
    test_set = shuffled[340:400]

    splits = [
        ("train", train_set, TRAIN_DIR),
        ("val", val_set, VAL_DIR),
        ("test", test_set, TEST_DIR),
    ]

    manifest = []

    for split_name, dataset, target_dir in splits:
        print(f"Writing {len(dataset)} files for split '{split_name}' to {target_dir}...", flush=True)
        for i, item in enumerate(dataset, 1):
            doc_id = f"enron_{split_name}_{i:03d}_{item['custodian']}"
            slug = clean_subject_slug(item["subject"])
            fname = f"{doc_id}_{slug}.txt"
            fpath = os.path.join(target_dir, fname)

            with open(fpath, "w", encoding="utf-8", errors="replace") as out:
                out.write(item["raw_text"])

            clean_preview = re.sub(r"\s+", " ", item["body_text"]).strip()
            manifest_entry = {
                "document_id": doc_id,
                "split": split_name,
                "filename": f"data/enron_evaluation/raw_emails/{split_name}/{fname}",
                "custodian": item["custodian"],
                "folder": item["folder"],
                "date": item["date"],
                "sender": item["sender"],
                "recipient": item["recipient"],
                "subject": item["subject"],
                "char_length": item["char_length"],
                "sha256": item["sha256"],
                "text_preview": (clean_preview[:280] + "...") if len(clean_preview) > 280 else clean_preview
            }
            manifest.append(manifest_entry)

    # Persist manifest.json
    manifest_path = os.path.join(DATA_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Manifest written to: {manifest_path} ({len(manifest)} total entries)", flush=True)
    print("=" * 80, flush=True)
    print(f"SUCCESS: 280 Train + 60 Val + 60 Test = {len(manifest)} Total", flush=True)
    print("=" * 80, flush=True)

if __name__ == "__main__":
    main()
