"""
Fine-tuning and evaluation script for legal-specific Named Entity Recognition (NER).
Schema: ATTORNEY, CUSTODIAN, PRIVILEGE_MARKER, CASE_REFERENCE.

Executes:
PART A: Validation of completed labeling in candidate_entities_bootstrap_corrected.csv
PART B: Stratified document split (Train 70% / Val 15% / Test 15%) and spaCy NER fine-tuning
PART C: Evaluation on strictly held-out test split reporting per-entity P/R/F1.
"""

import os
import sys
import re
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding
from spacy.scorer import Scorer

# Workspace paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
LABEL_DIR = DATA_DIR / "entity_labeling"
CORRECTED_CSV = LABEL_DIR / "candidate_entities_bootstrap_corrected.csv"
BOOTSTRAP_JSON = LABEL_DIR / "candidate_entities_bootstrap.json"
SYNTH_CSV = DATA_DIR / "synthetic_privilege_benchmark.csv"
ENRON_CSV = DATA_DIR / "enron_evaluation" / "labeling" / "labeling_template_all_FINAL.csv"
MODEL_OUTPUT_DIR = BASE_DIR / "backend" / "models" / "legal_ner_ediscovery_v1"
MODEL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
EVAL_RESULTS_JSON = LABEL_DIR / "ner_evaluation_results.json"
SPLIT_MANIFEST_JSON = LABEL_DIR / "split_manifest.json"

CUSTOM_LABELS = ["ATTORNEY", "CUSTODIAN", "PRIVILEGE_MARKER", "CASE_REFERENCE"]
ALLOWED_CONFIRMED = set(CUSTOM_LABELS + ["NONE"])

def log(msg=""):
    print(msg, flush=True)

def validate_labels():
    log("=" * 80)
    log("PART A: VALIDATING COMPLETED HUMAN ENTITY ANNOTATIONS")
    log("=" * 80)
    
    if not CORRECTED_CSV.exists():
        raise FileNotFoundError(f"Missing corrected CSV at: {CORRECTED_CSV}")
        
    with open(CORRECTED_CSV, "r", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))
        
    log(f"[+] Loaded {len(csv_rows)} rows from {CORRECTED_CSV.name}")
    
    # 1. Purity & Validity checks
    invalid_rows = []
    blank_rows = []
    for i, r in enumerate(csv_rows):
        val = r.get("human_confirmed_type", "").strip()
        if not val:
            blank_rows.append((i, r["document_id"], r["entity_text"]))
        elif val not in ALLOWED_CONFIRMED:
            invalid_rows.append((i, r["document_id"], r["entity_text"], val))
            
    log(f"[+] Blank confirmed cells count: {len(blank_rows)} (100% complete!)")
    if blank_rows:
        raise ValueError(f"Found {len(blank_rows)} blank cells in human_confirmed_type!")
        
    log(f"[+] Invalid / unexpected values count: {len(invalid_rows)} (100% valid schema!)")
    if invalid_rows:
        raise ValueError(f"Found invalid labels: {invalid_rows[:5]}")
        
    # 2. Confirmed distribution
    confirmed_counts = Counter(r["human_confirmed_type"].strip() for r in csv_rows)
    log("\n--- CONFIRMED LABEL DISTRIBUTION ---")
    for lbl in ["ATTORNEY", "CUSTODIAN", "PRIVILEGE_MARKER", "CASE_REFERENCE", "NONE"]:
        cnt = confirmed_counts.get(lbl, 0)
        pct = (cnt / len(csv_rows)) * 100
        log(f"  - {lbl:<18}: {cnt:>3} ({pct:>5.1f}%)")
    log(f"  TOTAL SPANS       : {len(csv_rows):>3}")
    
    # 3. Agreement rate & transition matrix
    agreed = sum(1 for r in csv_rows if r["human_confirmed_type"].strip() == r["entity_type_suggested"].strip())
    agree_pct = (agreed / len(csv_rows)) * 100
    log(f"\n--- AGREEMENT STATS (SUGGESTED vs. HUMAN CONFIRMED) ---")
    log(f"  - Confirmed as suggested : {agreed} / {len(csv_rows)} ({agree_pct:.1f}%)")
    log(f"  - Corrected or marked NONE: {len(csv_rows) - agreed} / {len(csv_rows)} ({100 - agree_pct:.1f}%)")
    
    transitions = Counter((r["entity_type_suggested"].strip(), r["human_confirmed_type"].strip()) for r in csv_rows)
    log("\n  Transition Matrix (Suggested -> Confirmed):")
    for (sug, conf), cnt in sorted(transitions.items(), key=lambda x: x[1], reverse=True):
        log(f"    {sug:<18} -> {conf:<18}: {cnt:>3}")
        
    return csv_rows

def build_stratified_split(csv_rows):
    log("\n" + "=" * 80)
    log("BUILDING STRATIFIED DOCUMENT-LEVEL TRAIN / VAL / TEST SPLIT")
    log("=" * 80)
    
    with open(BOOTSTRAP_JSON, "r", encoding="utf-8") as f:
        json_rows = json.load(f)
        
    items = []
    for c, j in zip(csv_rows, json_rows):
        it = dict(j)
        it["human_confirmed_type"] = c["human_confirmed_type"].strip()
        items.append(it)
        
    by_doc = defaultdict(list)
    for it in items:
        by_doc[it["document_id"]].append(it)
        
    unique_docs = sorted(list(by_doc.keys()))
    log(f"[+] Total unique documents with entity annotations: {len(unique_docs)}")
    
    # Rare entity allocation across splits
    case_train = {"enron_train_067_neal-s", "synth_priv_0019", "enron_val_014_hain-m"}
    case_val = {"enron_train_115_corman-s"}
    case_test = {"synth_priv_002"}
    
    random.seed(42)
    remaining_docs = [d for d in unique_docs if d not in case_train and d not in case_val and d not in case_test]
    random.shuffle(remaining_docs)
    
    # 70% Train (~82 docs), 15% Val (17 docs), 15% Test (17 docs)
    n_val = 17 - len(case_val)
    n_test = 17 - len(case_test)
    
    val_docs = sorted(list(case_val.union(remaining_docs[:n_val])))
    test_docs = sorted(list(case_test.union(remaining_docs[n_val:n_val + n_test])))
    train_docs = sorted(list(case_train.union(remaining_docs[n_val + n_test:])))
    
    log(f"[+] Partitioned into:")
    log(f"  - Train: {len(train_docs)} documents ({len(train_docs)/len(unique_docs)*100:.1f}%)")
    log(f"  - Val  : {len(val_docs)} documents ({len(val_docs)/len(unique_docs)*100:.1f}%)")
    log(f"  - Test : {len(test_docs)} documents ({len(test_docs)/len(unique_docs)*100:.1f}%)")
    
    split_info = {}
    for name, dset in [("TRAIN", train_docs), ("VAL", val_docs), ("TEST", test_docs)]:
        spans = [it for it in items if it["document_id"] in dset]
        counts = Counter(it["human_confirmed_type"] for it in spans)
        split_info[name] = {
            "num_docs": len(dset),
            "num_spans": len(spans),
            "doc_ids": dset,
            "counts": dict(counts)
        }
        log(f"\n  {name} Split Spans ({len(spans)} total):")
        for k in CUSTOM_LABELS + ["NONE"]:
            log(f"    - {k:<18}: {counts.get(k, 0)}")
            
    with open(SPLIT_MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump(split_info, f, indent=2)
    log(f"\n[+] Saved split manifest to: {SPLIT_MANIFEST_JSON}")
    
    return items, train_docs, val_docs, test_docs

def load_document_texts():
    doc_texts = {}
    with open(SYNTH_CSV, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            full_text = f"Subject: {r.get('subject', '')}\nFrom: {r.get('sender', '')}\nTo: {r.get('recipient', '')}\n\n{r.get('text', '')}"
            doc_texts[r["benchmark_id"]] = full_text
            
    with open(ENRON_CSV, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fn = BASE_DIR / r["filename"]
            if fn.exists():
                doc_texts[r["document_id"]] = fn.read_text(encoding="utf-8", errors="ignore")
                
    return doc_texts

def prepare_spacy_examples(doc_list, items, doc_texts, nlp, base_nlp):
    """
    Constructs focused training examples for documents.
    Preserves base entities (ORG, DATE, MONEY, GPE, PERSON) via pseudo-rehearsal.
    Drops spans marked NONE so the model learns them as negatives.
    """
    doc_annotations = defaultdict(list)
    for it in items:
        if it["document_id"] in doc_list:
            doc_annotations[it["document_id"]].append(it)
            
    examples = []
    
    for doc_id in doc_list:
        full_text = doc_texts.get(doc_id, "")
        if not full_text:
            continue
            
        # Segment document into paragraphs / sections with annotations
        anns = doc_annotations[doc_id]
        if not anns:
            continue
            
        # Group close annotations into cohesive text windows (up to 1200 chars each)
        anns.sort(key=lambda x: x["start_char"])
        windows = []
        curr_window = [anns[0]]
        
        for a in anns[1:]:
            if a["start_char"] - curr_window[-1]["end_char"] < 500 and (a["end_char"] - curr_window[0]["start_char"]) < 1200:
                curr_window.append(a)
            else:
                windows.append(curr_window)
                curr_window = [a]
        if curr_window:
            windows.append(curr_window)
            
        for w_anns in windows:
            w_min = max(0, w_anns[0]["start_char"] - 120)
            w_max = min(len(full_text), w_anns[-1]["end_char"] + 120)
            chunk_text = full_text[w_min:w_max]
            
            doc = nlp.make_doc(chunk_text)
            base_doc = base_nlp(chunk_text)
            
            # Base non-target entities
            base_spans = [
                (e.start_char, e.end_char, e.label_)
                for e in base_doc.ents
                if e.label_ in {"ORG", "DATE", "MONEY", "GPE", "PERSON", "LAW"}
            ]
            
            # Custom positive and negative spans in this chunk
            custom_pos = []
            negative_spans = []
            for a in w_anns:
                s = a["start_char"] - w_min
                e = a["end_char"] - w_min
                lbl = a["human_confirmed_type"]
                if 0 <= s < e <= len(chunk_text):
                    if lbl != "NONE":
                        custom_pos.append((s, e, lbl))
                    else:
                        negative_spans.append((s, e))
                        
            def overlaps(s1, e1, s2, e2):
                return max(s1, s2) < min(e1, e2)
                
            # Drop base entities that overlap with custom positive or negative spans
            kept_base = []
            for bs, be, blbl in base_spans:
                conflict = False
                for cs, ce, _ in custom_pos:
                    if overlaps(bs, be, cs, ce):
                        conflict = True
                        break
                if not conflict:
                    for ns, ne in negative_spans:
                        if overlaps(bs, be, ns, ne):
                            conflict = True
                            break
                if not conflict:
                    kept_base.append((bs, be, blbl))
                    
            candidate_all = kept_base + custom_pos
            candidate_all.sort(key=lambda x: x[0])
            
            aligned_ents = []
            occupied_tokens = set()
            for s, e, lbl in candidate_all:
                span = doc.char_span(s, e, label=lbl, alignment_mode="contract")
                if span is None:
                    span = doc.char_span(s, e, label=lbl, alignment_mode="expand")
                if span is not None:
                    span_tokens = set(range(span.start, span.end))
                    if not span_tokens.intersection(occupied_tokens):
                        occupied_tokens.update(span_tokens)
                        aligned_ents.append((span.start_char, span.end_char, lbl))
                        
            ex = Example.from_dict(doc, {"entities": aligned_ents})
            examples.append(ex)
            
    return examples

def train_and_evaluate():
    csv_rows = validate_labels()
    items, train_docs, val_docs, test_docs = build_stratified_split(csv_rows)
    doc_texts = load_document_texts()
    
    log("\n" + "=" * 80)
    log("PART B: FINE-TUNING SPACY NER MODEL ON CONFIRMED LABELS")
    log("=" * 80)
    
    # Load base model with only ner enabled for maximum efficiency
    base_nlp = spacy.load("en_core_web_sm", disable=["tagger", "parser", "lemmatizer", "attribute_ruler"])
    nlp = spacy.load("en_core_web_sm", disable=["tagger", "parser", "lemmatizer", "attribute_ruler"])
    
    ner = nlp.get_pipe("ner")
    for lbl in CUSTOM_LABELS:
        ner.add_label(lbl)
    log(f"[+] Added 4 custom entity labels to NER pipe: {CUSTOM_LABELS}")
    
    train_examples = prepare_spacy_examples(train_docs, items, doc_texts, nlp, base_nlp)
    val_examples = prepare_spacy_examples(val_docs, items, doc_texts, nlp, base_nlp)
    test_examples = prepare_spacy_examples(test_docs, items, doc_texts, nlp, base_nlp)
    
    log(f"[+] Constructed training examples:")
    log(f"  - Train examples : {len(train_examples)} windows (from {len(train_docs)} docs)")
    log(f"  - Val examples   : {len(val_examples)} windows (from {len(val_docs)} docs)")
    log(f"  - Test examples  : {len(test_examples)} windows (from {len(test_docs)} docs, strictly held-out)")
    
    optimizer = nlp.resume_training()
    
    n_epochs = 20
    batch_sizes = compounding(4.0, 16.0, 1.001)
    best_val_f1 = -1.0
    best_weights_path = MODEL_OUTPUT_DIR / "best_model"
    best_weights_path.mkdir(parents=True, exist_ok=True)
    
    log(f"\n[*] Starting training loop ({n_epochs} epochs)...")
    log(f"{'Epoch':<8} {'Loss':<12} {'Val P':<10} {'Val R':<10} {'Val F1':<10} {'Status'}")
    log("-" * 55)
    
    scorer = Scorer()
    
    for epoch in range(1, n_epochs + 1):
        random.shuffle(train_examples)
        losses = {}
        batches = minibatch(train_examples, size=batch_sizes)
        for batch in batches:
            nlp.update(batch, sgd=optimizer, drop=0.2, losses=losses)
            
        # Quick validation evaluation every 2 epochs
        if epoch % 2 == 0 or epoch == 1 or epoch == n_epochs:
            val_eval_examples = []
            for ex in val_examples:
                pred_doc = nlp(ex.reference.text)
                val_eval_examples.append(Example(pred_doc, ex.reference))
            val_scores = scorer.score(val_eval_examples)
            
            p = val_scores.get("ents_p", 0.0)
            r = val_scores.get("ents_r", 0.0)
            f1 = val_scores.get("ents_f", 0.0)
            
            status = ""
            if f1 > best_val_f1:
                best_val_f1 = f1
                nlp.to_disk(MODEL_OUTPUT_DIR)
                status = "[*] Best"
                
            log(f"{epoch:<8} {losses.get('ner', 0.0):<12.2f} {p:<10.3f} {r:<10.3f} {f1:<10.3f} {status}")
            
    log(f"\n[+] Fine-tuning complete. Loading best checkpoint from {MODEL_OUTPUT_DIR}...")
    best_nlp = spacy.load(MODEL_OUTPUT_DIR)
    log(f"[+] Loaded best pipeline from: {MODEL_OUTPUT_DIR}")
    
    log("\n" + "=" * 80)
    log("PART C: EVALUATION ON STRICTLY HELD-OUT TEST SPLIT")
    log("=" * 80)
    
    test_eval_examples = []
    for ex in test_examples:
        pred_doc = best_nlp(ex.reference.text)
        test_eval_examples.append(Example(pred_doc, ex.reference))
        
    test_scores = scorer.score(test_eval_examples)
    per_type = test_scores.get("ents_per_type", {})
    
    log("\n--- HELD-OUT TEST SPLIT RESULTS (PER CUSTOM ENTITY TYPE) ---")
    log(f"{'Entity Type':<20} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<10}")
    log("-" * 66)
    
    eval_summary = {}
    for lbl in CUSTOM_LABELS:
        m = per_type.get(lbl, {"p": 0.0, "r": 0.0, "f": 0.0})
        gold_support = sum(
            1 for ex in test_examples
            for ent in ex.reference.ents
            if ent.label_ == lbl
        )
        p_val = m.get("p", 0.0)
        r_val = m.get("r", 0.0)
        f_val = m.get("f", 0.0)
        log(f"{lbl:<20} {p_val:<12.3f} {r_val:<12.3f} {f_val:<12.3f} {gold_support:<10}")
        eval_summary[lbl] = {
            "precision": round(p_val, 4),
            "recall": round(r_val, 4),
            "f1": round(f_val, 4),
            "support": gold_support
        }
        
    log("\n--- BASE SPACY GENERIC ENTITY PRESERVATION (HELD-OUT TEST) ---")
    log(f"{'Base Type':<20} {'Precision':<12} {'Recall':<12} {'F1-Score':<12} {'Support':<10}")
    log("-" * 66)
    base_summary = {}
    for lbl in ["DATE", "ORG", "GPE", "MONEY", "PERSON"]:
        m = per_type.get(lbl, {"p": 0.0, "r": 0.0, "f": 0.0})
        gold_support = sum(
            1 for ex in test_examples
            for ent in ex.reference.ents
            if ent.label_ == lbl
        )
        p_val = m.get("p", 0.0)
        r_val = m.get("r", 0.0)
        f_val = m.get("f", 0.0)
        log(f"{lbl:<20} {p_val:<12.3f} {r_val:<12.3f} {f_val:<12.3f} {gold_support:<10}")
        base_summary[lbl] = {
            "precision": round(p_val, 4),
            "recall": round(r_val, 4),
            "f1": round(f_val, 4),
            "support": gold_support
        }
        
    overall_p = test_scores.get("ents_p", 0.0)
    overall_r = test_scores.get("ents_r", 0.0)
    overall_f = test_scores.get("ents_f", 0.0)
    log("\n--- OVERALL TEST METRICS (ALL ENTITIES COMBINED) ---")
    log(f"  Precision: {overall_p:.3f} | Recall: {overall_r:.3f} | F1: {overall_f:.3f}")
    
    output_data = {
        "custom_entity_metrics": eval_summary,
        "base_preserved_metrics": base_summary,
        "overall_test_metrics": {
            "precision": round(overall_p, 4),
            "recall": round(overall_r, 4),
            "f1": round(overall_f, 4)
        }
    }
    
    with open(EVAL_RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2)
    log(f"\n[+] Saved evaluation metrics to: {EVAL_RESULTS_JSON}")
    
    return output_data

if __name__ == "__main__":
    train_and_evaluate()
