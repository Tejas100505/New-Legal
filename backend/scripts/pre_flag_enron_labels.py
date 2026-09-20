"""
Pre-Flagging Heuristic Script for Enron Dataset

Adds transparent, rule-based suggestion columns to labeling CSV templates:
- suggested_relevant (TRUE / FALSE)
- suggestion_confidence (high / low)
- needs_privilege_review (TRUE / FALSE)
- suggested_relevance_terms (comma-separated matched terms)
- suggested_privilege_terms (comma-separated matched terms)

CRITICAL: Pure keyword heuristic ONLY (no LLM, no AI agent calls).
Ground-truth fields (is_relevant, is_privileged, notes) remain 100% blank.
"""

import os
import re
import csv
from collections import Counter

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DATA_DIR = os.path.join(BASE_DIR, "data", "enron_evaluation")
LABELING_DIR = os.path.join(DATA_DIR, "labeling")

# ── Case Scenario Relevance Keyword Patterns ──────────────────────────────────
# Target: "california", "regulator", "ferc", "cpuc", "iso", "rate increase",
# "price", "market manipulation", "scheduling", "trading strategy"
RELEVANCE_PATTERNS = {
    "california": re.compile(r"\bcalifornia\b", re.IGNORECASE),
    "regulator": re.compile(r"\bregulat", re.IGNORECASE),  # regulator, regulatory, regulation
    "ferc": re.compile(r"\bferc\b", re.IGNORECASE),
    "cpuc": re.compile(r"\bcpuc\b", re.IGNORECASE),
    "iso": re.compile(r"\biso\b", re.IGNORECASE),
    "rate increase": re.compile(r"\brate increases?\b", re.IGNORECASE),
    "price": re.compile(r"\bpricing\b|\bprices?\b", re.IGNORECASE),
    "market manipulation": re.compile(r"\bmarket manipulation\b", re.IGNORECASE),
    "scheduling": re.compile(r"\bschedul", re.IGNORECASE),  # schedule, scheduling
    "trading strategy": re.compile(r"\btrading strateg", re.IGNORECASE),
}

# ── Privilege Flag Keyword Patterns ───────────────────────────────────────────
# Target: "counsel", "attorney", "esq", "legal department", "general counsel",
# "attorney-client", "privileged"
PRIVILEGE_PATTERNS = {
    "counsel": re.compile(r"\bcounsel", re.IGNORECASE),
    "attorney": re.compile(r"\battorney", re.IGNORECASE),
    "esq": re.compile(r"\besq\b", re.IGNORECASE),
    "legal department": re.compile(r"\blegal department\b", re.IGNORECASE),
    "general counsel": re.compile(r"\bgeneral counsel\b", re.IGNORECASE),
    "attorney-client": re.compile(r"\battorney[-\s]client\b", re.IGNORECASE),
    "privileged": re.compile(r"\bprivilege", re.IGNORECASE),
}

SUGGESTION_COLUMNS = [
    "suggested_relevant",
    "suggestion_confidence",
    "needs_privilege_review",
    "suggested_relevance_terms",
    "suggested_privilege_terms",
]

def analyze_text(text: str):
    """Evaluates text against relevance and privilege keyword sets."""
    # 1. Relevance analysis
    matched_relevance = []
    for term, pattern in RELEVANCE_PATTERNS.items():
        if pattern.search(text):
            matched_relevance.append(term)

    rel_count = len(matched_relevance)
    if rel_count >= 2:
        suggested_relevant = "TRUE"
        suggestion_confidence = "high"
    elif rel_count == 1:
        suggested_relevant = "TRUE"
        suggestion_confidence = "low"
    else:
        suggested_relevant = "FALSE"
        suggestion_confidence = "high"

    # 2. Privilege review flag
    matched_privilege = []
    for term, pattern in PRIVILEGE_PATTERNS.items():
        if pattern.search(text):
            matched_privilege.append(term)

    needs_privilege = "TRUE" if len(matched_privilege) > 0 else "FALSE"

    return {
        "suggested_relevant": suggested_relevant,
        "suggestion_confidence": suggestion_confidence,
        "needs_privilege_review": needs_privilege,
        "suggested_relevance_terms": "; ".join(matched_relevance),
        "suggested_privilege_terms": "; ".join(matched_privilege),
    }

def process_csv(csv_path: str):
    """Processes a labeling template CSV, reading raw file text and appending suggestions."""
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        original_fields = reader.fieldnames
        rows = list(reader)

    # Ensure suggestion fields are appended to the header
    new_fieldnames = list(original_fields)
    for col in SUGGESTION_COLUMNS:
        if col not in new_fieldnames:
            new_fieldnames.append(col)

    updated_rows = []
    stats = {
        "total": len(rows),
        "relevant_true": 0,
        "relevant_false": 0,
        "conf_high": 0,
        "conf_low": 0,
        "privilege_true": 0,
        "privilege_false": 0,
        "term_freq": Counter(),
        "priv_term_freq": Counter(),
    }

    for row in rows:
        # Guarantee ground truth fields remain completely untouched
        assert row.get("is_relevant", "") == "", f"Ground truth is_relevant polluted in {csv_path}"
        assert row.get("is_privileged", "") == "", f"Ground truth is_privileged polluted in {csv_path}"
        assert row.get("notes", "") == "", f"Ground truth notes polluted in {csv_path}"

        # Load raw email file text
        rel_filename = row["filename"]
        full_filepath = os.path.join(BASE_DIR, rel_filename)
        if os.path.exists(full_filepath):
            with open(full_filepath, "r", encoding="utf-8", errors="replace") as f:
                full_text = f.read()
        else:
            # Fallback to subject + preview if file not found
            full_text = f"{row.get('subject', '')}\n{row.get('text_preview', '')}"

        # Run heuristic keyword analysis
        analysis = analyze_text(full_text)

        # Append suggestions
        row.update(analysis)
        updated_rows.append(row)

        # Track stats
        if analysis["suggested_relevant"] == "TRUE":
            stats["relevant_true"] += 1
        else:
            stats["relevant_false"] += 1

        if analysis["suggestion_confidence"] == "high":
            stats["conf_high"] += 1
        else:
            stats["conf_low"] += 1

        if analysis["needs_privilege_review"] == "TRUE":
            stats["privilege_true"] += 1
        else:
            stats["privilege_false"] += 1

        if analysis["suggested_relevance_terms"]:
            for t in analysis["suggested_relevance_terms"].split("; "):
                stats["term_freq"][t] += 1

        if analysis["suggested_privilege_terms"]:
            for t in analysis["suggested_privilege_terms"].split("; "):
                stats["priv_term_freq"][t] += 1

    # Overwrite the CSV with updated columns
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=new_fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(updated_rows)

    return stats

def main():
    print("=" * 80)
    print("RUNNING PRE-FLAGGING KEYWORD HEURISTIC ON ENRON LABELING TEMPLATES")
    print("=" * 80)

    csv_files = [
        "labeling_template_train.csv",
        "labeling_template_val.csv",
        "labeling_template_test.csv",
        "labeling_template_all.csv",
    ]

    all_stats = None

    for fname in csv_files:
        fpath = os.path.join(LABELING_DIR, fname)
        if not os.path.exists(fpath):
            print(f"Skipping missing file: {fpath}")
            continue

        stats = process_csv(fpath)
        print(f"\nProcessed {fname} ({stats['total']} rows):")
        print(f"  suggested_relevant = TRUE:  {stats['relevant_true']} ({stats['relevant_true']/stats['total']*100:.1f}%)")
        print(f"    - confidence = high (2+ terms): {stats['conf_high'] - stats['relevant_false']}")
        print(f"    - confidence = low (1 term):    {stats['conf_low']}")
        print(f"  suggested_relevant = FALSE: {stats['relevant_false']} ({stats['relevant_false']/stats['total']*100:.1f}%)")
        print(f"  needs_privilege_review = TRUE:  {stats['privilege_true']} ({stats['privilege_true']/stats['total']*100:.1f}%)")
        print(f"  needs_privilege_review = FALSE: {stats['privilege_false']} ({stats['privilege_false']/stats['total']*100:.1f}%)")

        if fname == "labeling_template_all.csv":
            all_stats = stats

    print("\n" + "=" * 80)
    print("OVERALL 400-EMAIL DATASET DISTRIBUTION SUMMARY")
    print("=" * 80)
    if all_stats:
        t = all_stats["total"]
        print(f"Total Emails Analyzed: {t}")
        print(f"\n1. RELEVANCE SUGGESTIONS:")
        print(f"   * Suggested Relevant (TRUE):  {all_stats['relevant_true']}/{t} ({all_stats['relevant_true']/t*100:.1f}%)")
        print(f"     - High Confidence (2+ terms): {all_stats['relevant_true'] - all_stats['conf_low']}/{t} ({(all_stats['relevant_true'] - all_stats['conf_low'])/t*100:.1f}%)")
        print(f"     - Low Confidence (1 term):    {all_stats['conf_low']}/{t} ({all_stats['conf_low']/t*100:.1f}%)")
        print(f"   * Suggested Non-Relevant (FALSE): {all_stats['relevant_false']}/{t} ({all_stats['relevant_false']/t*100:.1f}%)")
        print(f"   -> Top Relevance Keywords Matched:")
        for term, count in all_stats["term_freq"].most_common():
            print(f"      - '{term}': {count} occurrences")

        print(f"\n2. PRIVILEGE REVIEW FLAGS:")
        print(f"   * Needs Privilege Review (TRUE):  {all_stats['privilege_true']}/{t} ({all_stats['privilege_true']/t*100:.1f}%)")
        print(f"   * Routine Email (FALSE):         {all_stats['privilege_false']}/{t} ({all_stats['privilege_false']/t*100:.1f}%)")
        print(f"   -> Top Privilege Keywords Matched:")
        for term, count in all_stats["priv_term_freq"].most_common():
            print(f"      - '{term}': {count} occurrences")

        saved_reading_pct = (all_stats['relevant_false'] / t) * 100
        saved_priv_pct = (all_stats['privilege_false'] / t) * 100
        print(f"\n3. ESTIMATED TIME SAVINGS FOR REVIEW TEAM:")
        print(f"   * ~{saved_reading_pct:.1f}% of emails have ZERO case scenario terms (can be reviewed in fast-triage pass).")
        print(f"   * ~{saved_priv_pct:.1f}% of emails have ZERO attorney/legal terms (team does not need deep privilege analysis).")
        print(f"   * Only {all_stats['privilege_true']} emails (~{all_stats['privilege_true']/t*100:.1f}%) need close privilege scrutiny.")

    print("\n" + "=" * 80)
    print("PRE-FLAGGING COMPLETED: GROUND TRUTH COLUMNS REMAIN 100% UNTOUCHED")
    print("=" * 80)

if __name__ == "__main__":
    main()
