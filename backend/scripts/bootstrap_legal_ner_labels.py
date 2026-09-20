"""
Weak-supervision bootstrapping script for legal-specific NER entity labeling.
Generates candidate entity spans across a curated subset of 144 documents (24 synthetic + 120 Enron).
Outputs data/entity_labeling/candidate_entities_bootstrap.csv with blank human_confirmed_type and notes columns.
"""

import os
import re
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
import spacy

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Workspace paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
ENRON_CSV = DATA_DIR / "enron_evaluation" / "labeling" / "labeling_template_all_FINAL.csv"
SYNTH_CSV = DATA_DIR / "synthetic_privilege_benchmark.csv"
OUTPUT_DIR = DATA_DIR / "entity_labeling"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_CSV = OUTPUT_DIR / "candidate_entities_bootstrap.csv"
OUTPUT_JSON = OUTPUT_DIR / "candidate_entities_bootstrap.json"

# 1. Privilege regex patterns (from privilege.py: STRONG_PRIVILEGE_PATTERNS and PRIVILEGE_PATTERNS)
PRIVILEGE_MARKER_PATTERNS = [
    r"(?i)\battorney[\s-]client\s+privilege\b",
    r"(?i)\bprivileged\s+(?:and|&)\s+confidential\b",
    r"(?i)\bconfidential\s+(?:and|&)\s+privileged\b",
    r"(?i)\battorney[\s-]client\s+communication\b",
    r"(?i)\battorney\s+work\s+product\b",
    r"(?i)\bwork\s+product(?:\s+doctrine)?\b",
    r"(?i)\bprepared\s+in\s+anticipation\s+of\s+litigation\b",
    r"(?i)\blitigation\s+strategy\b",
    r"(?i)\btrial\s+preparation\b",
    r"(?i)\blegal\s+advice\b",
    r"(?i)\badvice\s+of\s+counsel\b",
    r"(?i)\bseek(?:ing)?\s+legal\s+counsel\b",
    r"(?i)\bconfidentiality\s+notice\b",
    r"(?i)\bstrictly\s+confidential\b",
    r"(?i)\bnon[\s-]disclosure\s+agreement\b",
]

# 2. Attorney context regex (from AMBIGUOUS_LEGAL_TERMS in privilege.py + legal roles)
ATTORNEY_CONTEXT_PATTERN = re.compile(
    r"(?i)\b(attorney|attorneys|lawyer|lawyers|counsel|counselor|counselors|esq|esquire|solicitor|"
    r"in-house\s+counsel|outside\s+counsel|general\s+counsel|special\s+counsel|regulatory\s+counsel|"
    r"senior\s+counsel|legal\s+counsel|managing\s+partner|partner|associate|law\s+firm|llp|p\.c\.|"
    r"legal\s+group|legal\s+department|legal\s+team|bar\s+association|litigation\s+counsel|"
    r"represented\s+by|legal\s+advisors|legal\s+rep)\b"
)

# 3. Case reference regex patterns
CASE_REFERENCE_PATTERNS = [
    # Docket numbers: Docket No. PL00-1, Docket Nos. EL01-47, FERC Docket No. 2001-A
    re.compile(r"(?i)\b(?:Docket\s+(?:Nos?\.?|#)?|FERC\s+Docket(?:\s+Nos?\.?)?)\s*:?\s*([A-Z0-9]{1,8}[-–/][A-Z0-9-–/]+|\d{4,8})\b"),
    # Case / Matter numbers: Case No. 00-11234, Matter 4022, Matter #12, Civil Action No. 01-1492
    re.compile(r"(?i)\b(?:Case\s+(?:Nos?\.?|#)|Matter\s+(?:Nos?\.?|#)?|Civil\s+Action\s+(?:No\.?|#)|Proceeding\s+(?:No\.?|#)|Arbitration\s+(?:No\.?|#))\s*:?\s*([A-Z0-9]{1,8}[-–/][A-Z0-9-–/]+|\d{3,10})\b"),
    # Adversarial litigation names: Apex v. RailCorp, ENA v. Triad, PX v FERC
    re.compile(r"\b([A-Z][A-Za-z0-9&.\'-]+(?:[^\S\r\n]+[A-Z][A-Za-z0-9&.\'-]+)?)[^\S\r\n]+v[s.]*[^\S\r\n]+([A-Z][A-Za-z0-9&.\'-]+(?:[^\S\r\n]+[A-Z][A-Za-z0-9&.\'-]+)?)\b"),
    # In re: In re Enron Corp., In re Apex Logistics
    re.compile(r"\bIn\s+re\s+([A-Z][A-Za-z0-9\s,&.\'-]{2,30}?)(?:\s+Litigation|\s+Bankruptcy|,|\n|\.|\)|;)"),
    # Regulatory docket IDs: e.g. EL01-47, RP00-42
    re.compile(r"\b([A-Z]{2}\d{2}-\d+(?:-\d+)?)\b"),
]

# Non-person stopwords that spaCy sometimes misclassifies as PERSON in email headers/bodies
PERSON_STOPWORDS = {
    "may be", "will", "dear", "sent", "please", "thanks", "subject", "hello",
    "yes", "no", "best", "regards", "sincerely", "fyi", "enron", "houston",
    "london", "california", "daily thought", "thyme", "javamail", "corp",
    "inc", "llc", "com", "pm", "am", "re", "fw", "ect", "date", "from", "to", "cc"
}

def clean_person_span(text: str) -> str:
    """Cleans up raw person span extracted by spaCy."""
    # Split newline if spaCy captured multi-line
    cleaned = text.split("\n")[0].strip()
    # Strip email routing prefixes/suffixes like /HOU/ECT
    cleaned = re.sub(r'(?:/(?:HOU|ECT|Enron|Corp|NYC|LON|Notes))+', '', cleaned, flags=re.IGNORECASE).strip()
    # Strip leading/trailing punctuation
    cleaned = cleaned.strip(" ,;:.\"\'()[]<>{}")
    return cleaned

def extract_name_from_email(email_str: str) -> str:
    """Extracts a human name from email address or display name."""
    if not email_str:
        return ""
    display_match = re.match(r'^"?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)"?\s*<', email_str.strip())
    if display_match:
        return display_match.group(1).strip()
    local = email_str.split("@")[0].strip()
    parts = re.split(r"[._-]", local)
    if len(parts) >= 2 and all(p.isalpha() for p in parts[:2]):
        return f"{parts[0].capitalize()} {parts[1].capitalize()}"
    elif len(parts) == 1 and parts[0].isalpha() and len(parts[0]) > 2:
        return parts[0].capitalize()
    return ""

def get_context_snippet(text: str, start: int, end: int, window: int = 50) -> str:
    """Generates surrounding context snippet with the entity enclosed in brackets."""
    left = max(0, start - window)
    right = min(len(text), end + window)
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(text) else ""
    
    before = text[left:start].replace("\n", " ").replace("\r", " ")
    entity = text[start:end].replace("\n", " ").replace("\r", " ")
    after = text[end:right].replace("\n", " ").replace("\r", " ")
    # Normalize multiple whitespace
    before = re.sub(r'\s+', ' ', before)
    entity = re.sub(r'\s+', ' ', entity)
    after = re.sub(r'\s+', ' ', after)
    return f"{prefix}{before}[{entity}]{after}{suffix}"

def run_bootstrapping():
    print("=" * 80)
    print("STARTING WEAK-SUPERVISION LEGAL NER BOOTSTRAPPING PIPELINE")
    print("=" * 80)
    
    # 1. Load Synthetic Benchmark (all 24 documents)
    with open(SYNTH_CSV, "r", encoding="utf-8") as f:
        synth_rows = list(csv.DictReader(f))
    print(f"[+] Loaded {len(synth_rows)} synthetic benchmark documents.")
    
    # 2. Load Enron dataset
    with open(ENRON_CSV, "r", encoding="utf-8") as f:
        enron_rows = list(csv.DictReader(f))
    print(f"[+] Loaded {len(enron_rows)} total Enron candidate documents.")
    
    # Stratify selection across custodians (6 docs per custodian * 20 custodians = 120 docs)
    # Score by entity density signals to ensure rich legal content
    by_custodian = defaultdict(list)
    for r in enron_rows:
        by_custodian[r["custodian"]].append(r)
        
    selected_enron = []
    for cust, c_docs in by_custodian.items():
        scored = []
        for d in c_docs:
            score = 0
            # Privilege review flag
            if d.get("needs_privilege_review") == "True":
                score += 6
            if d.get("suggested_privilege_terms"):
                score += 5
            if d.get("is_relevant") == "TRUE":
                score += 2
                
            fn = BASE_DIR / d["filename"]
            if fn.exists():
                text_preview = fn.read_text(encoding="utf-8", errors="ignore")
                sz = len(text_preview)
                # Substantive email body preferred (300 to 4500 chars)
                if 300 <= sz <= 4500:
                    score += 3
                # Check for legal/docket/case keywords
                if re.search(r"(?i)\b(docket|case|court|attorney|counsel|lawyer|ferc|litigation|law\s+firm)\b", text_preview):
                    score += 5
            scored.append((score, d))
            
        scored.sort(key=lambda x: x[0], reverse=True)
        selected_enron.extend([item[1] for item in scored[:6]])
        
    print(f"[+] Selected {len(selected_enron)} Enron documents stratified across {len(by_custodian)} custodians.")
    
    # Build complete document list: 24 synthetic + 120 Enron = 144 total
    all_docs = []
    for r in synth_rows:
        full_text = f"Subject: {r.get('subject', '')}\nFrom: {r.get('sender', '')}\nTo: {r.get('recipient', '')}\n\n{r.get('text', '')}"
        all_docs.append({
            "document_id": r["benchmark_id"],
            "sender": r["sender"],
            "custodian": "",
            "text": full_text,
            "source": "synthetic"
        })
        
    for r in selected_enron:
        fn = BASE_DIR / r["filename"]
        content = fn.read_text(encoding="utf-8", errors="ignore")
        all_docs.append({
            "document_id": r["document_id"],
            "sender": r["sender"],
            "custodian": r["custodian"],
            "text": content,
            "source": "enron"
        })
        
    print(f"[+] Total document cohort: {len(all_docs)} documents.")
    
    # 3. Extract candidate entity spans
    candidate_spans = []
    seen_spans = set()  # (doc_id, start_char, end_char)
    
    for doc in all_docs:
        doc_id = doc["document_id"]
        text = doc["text"]
        sender_raw = doc["sender"]
        custodian_id = doc["custodian"]
        sender_name = extract_name_from_email(sender_raw)
        
        # A. PRIVILEGE_MARKER extraction via regex
        for pat in PRIVILEGE_MARKER_PATTERNS:
            for m in re.finditer(pat, text):
                start, end = m.start(), m.end()
                ent_text = text[start:end].strip()
                if len(ent_text) < 5:
                    continue
                # Normalize overlaps
                span_key = (doc_id, start, end)
                if span_key not in seen_spans:
                    seen_spans.add(span_key)
                    candidate_spans.append({
                        "document_id": doc_id,
                        "entity_text": ent_text,
                        "entity_type_suggested": "PRIVILEGE_MARKER",
                        "start_char": start,
                        "end_char": end,
                        "context_snippet": get_context_snippet(text, start, end),
                        "human_confirmed_type": "",  # STRICTLY BLANK
                        "notes": ""                  # STRICTLY BLANK
                    })
                    
        # B. CASE_REFERENCE extraction via regex
        for pat in CASE_REFERENCE_PATTERNS:
            for m in pat.finditer(text):
                start, end = m.start(), m.end()
                ent_text = text[start:end].strip()
                if len(ent_text) < 4:
                    continue
                # Skip middle initials or pure dates
                if re.match(r"^[A-Z]\.\s+[A-Z][a-z]+$", ent_text):
                    continue
                span_key = (doc_id, start, end)
                if span_key not in seen_spans:
                    seen_spans.add(span_key)
                    candidate_spans.append({
                        "document_id": doc_id,
                        "entity_text": ent_text,
                        "entity_type_suggested": "CASE_REFERENCE",
                        "start_char": start,
                        "end_char": end,
                        "context_snippet": get_context_snippet(text, start, end),
                        "human_confirmed_type": "",  # STRICTLY BLANK
                        "notes": ""                  # STRICTLY BLANK
                    })
                    
        # C. spaCy PERSON -> ATTORNEY or CUSTODIAN candidates
        # Process first 12,000 chars of document to cover full body and signatures
        doc_spacy = nlp(text[:12000])
        for ent in doc_spacy.ents:
            if ent.label_ != "PERSON":
                continue
                
            clean_name = clean_person_span(ent.text)
            if len(clean_name) < 3 or clean_name.lower() in PERSON_STOPWORDS:
                continue
            if not re.search(r"[A-Za-z]", clean_name):
                continue
            # Filter out strings with only numbers/symbols
            if len([c for c in clean_name if c.isalpha()]) < 3:
                continue
                
            start = ent.start_char
            end = start + len(clean_name)
            span_key = (doc_id, start, end)
            if span_key in seen_spans:
                continue
                
            # Context window (+/- 80 chars) for attorney terms
            ctx_start = max(0, start - 80)
            ctx_end = min(len(text), end + 80)
            surrounding_ctx = text[ctx_start:ctx_end]
            has_attorney_terms = bool(ATTORNEY_CONTEXT_PATTERN.search(surrounding_ctx))
            
            # Check match against sender or custodian
            is_sender_custodian = False
            if sender_name and len(sender_name) >= 3:
                if sender_name.lower() in clean_name.lower() or clean_name.lower() in sender_name.lower():
                    is_sender_custodian = True
            if custodian_id and len(custodian_id) >= 3:
                cust_prefix = custodian_id.split("-")[0].lower()
                if cust_prefix in clean_name.lower():
                    is_sender_custodian = True
                    
            suggested_type = None
            if has_attorney_terms:
                suggested_type = "ATTORNEY"
            elif is_sender_custodian:
                suggested_type = "CUSTODIAN"
            else:
                # Generic person not near attorney terms and not sender/custodian
                continue
                
            seen_spans.add(span_key)
            candidate_spans.append({
                "document_id": doc_id,
                "entity_text": clean_name,
                "entity_type_suggested": suggested_type,
                "start_char": start,
                "end_char": end,
                "context_snippet": get_context_snippet(text, start, end),
                "human_confirmed_type": "",  # STRICTLY BLANK
                "notes": ""                  # STRICTLY BLANK
            })
            
    # Sort deterministically
    candidate_spans.sort(key=lambda x: (x["document_id"], x["start_char"]))
    
    # 4. Write CSV file
    fieldnames = [
        "document_id",
        "entity_text",
        "entity_type_suggested",
        "context_snippet",
        "human_confirmed_type",
        "notes"
    ]
    
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in candidate_spans:
            writer.writerow({
                "document_id": c["document_id"],
                "entity_text": c["entity_text"],
                "entity_type_suggested": c["entity_type_suggested"],
                "context_snippet": c["context_snippet"],
                "human_confirmed_type": "",
                "notes": ""
            })
            
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(candidate_spans, f, indent=2)
        
    print(f"\n[+] Successfully generated {len(candidate_spans)} candidate entity spans across {len(all_docs)} documents.")
    print(f"[+] Output CSV written to: {OUTPUT_CSV}")
    print(f"[+] Output JSON written to: {OUTPUT_JSON}")
    
    # Counts by suggested type
    counts = Counter(c["entity_type_suggested"] for c in candidate_spans)
    print("\n" + "=" * 50)
    print("CANDIDATE SPANS GENERATED PER ENTITY TYPE")
    print("=" * 50)
    for etype in ["ATTORNEY", "CUSTODIAN", "PRIVILEGE_MARKER", "CASE_REFERENCE"]:
        print(f"  - {etype:<18}: {counts.get(etype, 0)}")
    print(f"  TOTAL CANDIDATES  : {len(candidate_spans)}")
    print("=" * 50)
    
    # Verify ground-truth purity (100% blank)
    non_blank_human = sum(1 for c in candidate_spans if str(c["human_confirmed_type"]).strip())
    non_blank_notes = sum(1 for c in candidate_spans if str(c["notes"]).strip())
    print("\nGROUND-TRUTH PURITY CONFIRMATION:")
    print(f"  - Non-blank 'human_confirmed_type' cells: {non_blank_human} (100.0% BLANK)")
    print(f"  - Non-blank 'notes' cells: {non_blank_notes} (100.0% BLANK)")
    
    return candidate_spans

if __name__ == "__main__":
    run_bootstrapping()
