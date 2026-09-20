"""
Unified Benchmark Evaluation Runner

Executes:
- PART A: Full Relevance Evaluation (Enron 400 docs) via hybrid pipeline (Gemini embedding + BM25 + CrossEncoder rerank)
- PART B: Privilege Detection Evaluation (Synthetic 24 docs) via PrivilegeAgent (Regex + Gemini LLM)
- PART C: Baseline Comparisons:
    - Relevance: BM25-only baseline vs. Hybrid Semantic System
    - Privilege: Regex-only baseline vs. Full Hybrid System (Regex + LLM)

Paced to strictly respect free-tier API quotas.
Outputs results cleanly with confusion matrices, precision/recall/F1, and failure case doc IDs.
"""

import os
import sys
import csv
import json
import time
import math
import asyncio
from typing import List, Dict, Any, Tuple

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, "..", ".env"))

from rank_bm25 import BM25Okapi
from app.agents.embedding import GeminiEmbeddingProvider
from app.agents.retrieval import RetrievalAgent, RetrievalInput, ChunkData
from app.agents.privilege import PrivilegeAgent, PrivilegeInput, PRIVILEGE_PATTERNS, STRONG_PRIVILEGE_PATTERNS

BASE_DIR = os.path.abspath(os.path.join(backend_dir, ".."))
ENRON_FINAL_CSV = os.path.join(BASE_DIR, "data", "enron_evaluation", "labeling", "labeling_template_all_FINAL.csv")
SYNTH_BENCHMARK_CSV = os.path.join(BASE_DIR, "data", "synthetic_privilege_benchmark.csv")
CACHE_DIR = os.path.join(BASE_DIR, "data", "enron_evaluation", ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)
EMBEDDINGS_CACHE_FILE = os.path.join(CACHE_DIR, "enron_gemini_embeddings_1024.json")

CASE_SCENARIO_QUERY = (
    "California energy market practices, pricing, regulatory communications, and trading strategy"
)

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def calculate_metrics(tp: int, fp: int, tn: int, fn: int) -> Dict[str, float]:
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
    return {
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "total": tp + fp + tn + fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
    }

# ─────────────────────────────────────────────────────────────────────────────
# PART A: RELEVANCE EVALUATION (400 Real Enron Docs)
# ─────────────────────────────────────────────────────────────────────────────
def get_or_generate_enron_embeddings(doc_texts: List[str]) -> Tuple[List[float], List[List[float]]]:
    """Caches query and document embeddings to preserve API quota."""
    provider = GeminiEmbeddingProvider()
    
    cached_data = {}
    if os.path.exists(EMBEDDINGS_CACHE_FILE):
        try:
            with open(EMBEDDINGS_CACHE_FILE, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            print(f"Loaded {len(cached_data.get('doc_embeddings', []))} cached document embeddings from {EMBEDDINGS_CACHE_FILE}")
        except Exception as e:
            print(f"Failed to load cache ({e}), regenerating...")

    query_vector = cached_data.get("query_embedding")
    doc_vectors = cached_data.get("doc_embeddings")

    if not query_vector:
        print("Generating query embedding via GeminiEmbeddingProvider...")
        query_vector = provider.embed_batch([CASE_SCENARIO_QUERY])[0]

    if not doc_vectors or len(doc_vectors) != len(doc_texts):
        print(f"Generating embeddings for {len(doc_texts)} Enron documents in batches...")
        doc_vectors = []
        BATCH_SIZE = 50
        for i in range(0, len(doc_texts), BATCH_SIZE):
            batch = doc_texts[i:i + BATCH_SIZE]
            print(f"  Embedding batch {i // BATCH_SIZE + 1} ({len(batch)} texts)...")
            batch_vecs = provider.embed_batch(batch)
            doc_vectors.extend(batch_vecs)
            time.sleep(2.0)  # Pacing between embedding batches

        with open(EMBEDDINGS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump({"query_embedding": query_vector, "doc_embeddings": doc_vectors}, f)
        print("Cached all embeddings successfully.")

    return query_vector, doc_vectors

async def run_relevance_evaluation():
    print("\n" + "=" * 80)
    print("PART A: RELEVANCE & RETRIEVAL EVALUATION (400 REAL ENRON DOCS)")
    print("=" * 80)
    print(f"Scenario Query: '{CASE_SCENARIO_QUERY}'\n")

    with open(ENRON_FINAL_CSV, "r", encoding="utf-8") as f:
        enron_rows = list(csv.DictReader(f))

    doc_texts = []
    for r in enron_rows:
        rel_path = r["filename"].replace("/", os.sep)
        full_path = os.path.join(BASE_DIR, rel_path)
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                doc_texts.append(f.read())
        else:
            doc_texts.append(f"Subject: {r.get('subject', '')}\n\n{r.get('text_preview', '')}")

    query_vector, doc_vectors = get_or_generate_enron_embeddings(doc_texts)

    # Compute vector similarity scores
    print("Computing cosine similarities against query vector...")
    vector_scores = [cosine_similarity(query_vector, dv) for dv in doc_vectors]

    # Run BM25 & Cross-Encoder Hybrid Pipeline
    retrieval_agent = RetrievalAgent()
    candidate_chunks = []
    for i, r in enumerate(enron_rows):
        candidate_chunks.append(ChunkData(
            chunk_id=f"chunk_{r['document_id']}",
            document_id=r["document_id"],
            page=1,
            section="email_body",
            text=doc_texts[i],
            metadata={"split": r["split"], "subject": r["subject"], "filename": r["filename"]},
            vector_score=vector_scores[i]
        ))

    # Retrieval agent execution across all candidates
    print("Running Hybrid Retrieval Agent (BM25 + CrossEncoder + Vector Combination)...")
    r_input = RetrievalInput(
        query=CASE_SCENARIO_QUERY,
        candidate_chunks=candidate_chunks,
        metadata_filters={},
        top_k=len(candidate_chunks)
    )
    r_output = await retrieval_agent.run(r_input)
    score_by_doc_id = {res.citation.strip("[]").split(",")[0]: res.score for res in r_output.results}
    # Map back to doc_id
    chunk_to_score = {res.chunk_id.replace("chunk_", ""): res.score for res in r_output.results}

    # Evaluate across thresholds to determine optimal calibration on train split
    train_scores = []
    for r in enron_rows:
        if r["split"] == "train":
            score = chunk_to_score.get(r["document_id"], 0.0)
            ground = r["is_relevant"] == "TRUE"
            train_scores.append((score, ground))

    # Find optimal threshold on train split
    best_thresh = 0.35
    best_train_f1 = -1.0
    for t_int in range(10, 80, 2):
        t = t_int / 100.0
        tp = sum(1 for s, g in train_scores if s >= t and g)
        fp = sum(1 for s, g in train_scores if s >= t and not g)
        fn = sum(1 for s, g in train_scores if s < t and g)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        if f1 > best_train_f1:
            best_train_f1 = f1
            best_thresh = t

    print(f"Optimal relevance decision threshold calibrated on train split: {best_thresh:.2f} (Train F1: {best_train_f1:.4f})")

    # Evaluate per split and overall
    results_by_split = {"train": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
                        "val": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
                        "test": {"tp": 0, "fp": 0, "tn": 0, "fn": 0}}
    
    disagreements = {"fp": [], "fn": []}

    for r in enron_rows:
        doc_id = r["document_id"]
        split = r["split"]
        score = chunk_to_score.get(doc_id, 0.0)
        human_relevant = (r["is_relevant"] == "TRUE")
        system_relevant = (score >= best_thresh)

        if human_relevant and system_relevant:
            results_by_split[split]["tp"] += 1
        elif not human_relevant and system_relevant:
            results_by_split[split]["fp"] += 1
            disagreements["fp"].append({
                "document_id": doc_id, "split": split, "score": score,
                "subject": r["subject"], "notes": r["notes"]
            })
        elif not human_relevant and not system_relevant:
            results_by_split[split]["tn"] += 1
        elif human_relevant and not system_relevant:
            results_by_split[split]["fn"] += 1
            disagreements["fn"].append({
                "document_id": doc_id, "split": split, "score": score,
                "subject": r["subject"], "notes": r["notes"]
            })

    # Combined stats
    comb_counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for s in ["train", "val", "test"]:
        for k in comb_counts:
            comb_counts[k] += results_by_split[s][k]

    metrics_by_split = {s: calculate_metrics(**results_by_split[s]) for s in ["train", "val", "test"]}
    metrics_comb = calculate_metrics(**comb_counts)

    print("\n--- RELEVANCE RETRIEVAL PERFORMANCE (HYBRID PIPELINE) ---")
    for s in ["train", "val", "test"]:
        m = metrics_by_split[s]
        print(f"[{s.upper()}] P: {m['precision']:.4f} | R: {m['recall']:.4f} | F1: {m['f1']:.4f} | Acc: {m['accuracy']:.4f} | (TP={m['tp']}, FP={m['fp']}, TN={m['tn']}, FN={m['fn']})")
    
    print(f"[COMBINED 400 DOCS] P: {metrics_comb['precision']:.4f} | R: {metrics_comb['recall']:.4f} | F1: {metrics_comb['f1']:.4f} | Acc: {metrics_comb['accuracy']:.4f}")
    print(f"  Confusion Matrix: TP={metrics_comb['tp']}, FP={metrics_comb['fp']}, TN={metrics_comb['tn']}, FN={metrics_comb['fn']}")

    return enron_rows, doc_texts, metrics_by_split, metrics_comb, disagreements, best_thresh, chunk_to_score

# ─────────────────────────────────────────────────────────────────────────────
# PART B: PRIVILEGE DETECTION EVALUATION (24 Synthetic Benchmark Docs)
# ─────────────────────────────────────────────────────────────────────────────
async def run_privilege_evaluation():
    print("\n" + "=" * 80)
    print("PART B: PRIVILEGE DETECTION EVALUATION (24 SYNTHETIC BENCHMARK DOCS)")
    print("=" * 80)

    with open(SYNTH_BENCHMARK_CSV, "r", encoding="utf-8") as f:
        benchmark_rows = list(csv.DictReader(f))

    agent = PrivilegeAgent()
    results = []

    tp, fp, tn, fn = 0, 0, 0, 0
    hard_negative_details = []
    genuine_privilege_details = []

    start_time = time.time()
    api_calls = 0

    print(f"Executing PrivilegeAgent across {len(benchmark_rows)} documents with 4.5s pacing on LLM calls...\n")

    for i, r in enumerate(benchmark_rows, 1):
        doc_id = r["benchmark_id"]
        gt_priv = (r["is_privileged"] == "TRUE")
        category = r["category"]

        item_start = time.time()
        print(f"[{i:02d}/24] Evaluating {doc_id} ({category[:35]})...", end=" ", flush=True)

        p_input = PrivilegeInput(document_id=doc_id, text=r["text"])
        out = await agent.run(p_input)
        elapsed = time.time() - item_start

        pred_priv = out.is_privileged
        method = out.detection_method
        conf = out.confidence_score
        reason = out.reasoning

        if method in ["llm_only", "both"]:
            api_calls += 1

        if gt_priv and pred_priv:
            tp += 1
        elif not gt_priv and pred_priv:
            fp += 1
        elif not gt_priv and not pred_priv:
            tn += 1
        elif gt_priv and not pred_priv:
            fn += 1

        print(f"Verdict={pred_priv} (GT={gt_priv}) | Method={method} | Conf={conf:.2f} ({elapsed:.1f}s)", flush=True)

        record = {
            "benchmark_id": doc_id,
            "category": category,
            "ground_truth": gt_priv,
            "pred_privileged": pred_priv,
            "detection_method": method,
            "confidence": conf,
            "reasoning": reason,
            "subject": r["subject"]
        }
        results.append(record)

        if not gt_priv:
            hard_negative_details.append(record)
        else:
            genuine_privilege_details.append(record)

        # Pace calls to respect 15 RPM if LLM was invoked
        if method in ["llm_only", "both"] and i < len(benchmark_rows):
            time.sleep(4.2)

    total_time = time.time() - start_time
    metrics = calculate_metrics(tp, fp, tn, fn)

    print("\n--- PRIVILEGE DETECTION PERFORMANCE (SYNTHETIC BENCHMARK) ---")
    print(f"Precision: {metrics['precision']:.4f}")
    print(f"Recall:    {metrics['recall']:.4f}")
    print(f"F1 Score:  {metrics['f1']:.4f}")
    print(f"Accuracy:  {metrics['accuracy']:.4f}")
    print(f"Confusion Matrix: TP={tp}, FP={fp}, TN={tn}, FN={fn}")
    print(f"Total Evaluation Time: {total_time:.1f}s | Gemini API Calls: {api_calls}")

    return metrics, hard_negative_details, genuine_privilege_details, results, total_time, api_calls

# ─────────────────────────────────────────────────────────────────────────────
# PART C: BASELINE COMPARISONS
# ─────────────────────────────────────────────────────────────────────────────
def run_relevance_bm25_baseline(enron_rows: List[Dict], doc_texts: List[str]):
    print("\n" + "=" * 80)
    print("PART C.1: RELEVANCE BASELINE (BM25 KEYWORD SEARCH ONLY)")
    print("=" * 80)

    tokenized_corpus = [t.lower().split() for t in doc_texts]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = CASE_SCENARIO_QUERY.lower().split()
    raw_bm25_scores = bm25.get_scores(tokenized_query)
    max_s = max(raw_bm25_scores) if max(raw_bm25_scores) > 0 else 1.0
    norm_bm25 = [s / max_s for s in raw_bm25_scores]

    train_data = [(norm_bm25[i], enron_rows[i]["is_relevant"] == "TRUE") for i in range(len(enron_rows)) if enron_rows[i]["split"] == "train"]
    
    best_bm25_thresh = 0.3
    best_bm25_f1 = -1.0
    for t_int in range(5, 70, 2):
        t = t_int / 100.0
        tp = sum(1 for s, g in train_data if s >= t and g)
        fp = sum(1 for s, g in train_data if s >= t and not g)
        fn = sum(1 for s, g in train_data if s < t and g)
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        if f1 > best_bm25_f1:
            best_bm25_f1 = f1
            best_bm25_thresh = t

    results_by_split = {"train": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
                        "val": {"tp": 0, "fp": 0, "tn": 0, "fn": 0},
                        "test": {"tp": 0, "fp": 0, "tn": 0, "fn": 0}}

    for i, r in enumerate(enron_rows):
        split = r["split"]
        score = norm_bm25[i]
        gt = (r["is_relevant"] == "TRUE")
        pred = (score >= best_bm25_thresh)
        if gt and pred:
            results_by_split[split]["tp"] += 1
        elif not gt and pred:
            results_by_split[split]["fp"] += 1
        elif not gt and not pred:
            results_by_split[split]["tn"] += 1
        elif gt and not pred:
            results_by_split[split]["fn"] += 1

    comb = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for s in ["train", "val", "test"]:
        for k in comb:
            comb[k] += results_by_split[s][k]

    metrics_bm25 = calculate_metrics(**comb)
    print(f"BM25 Baseline Threshold: {best_bm25_thresh:.2f}")
    print(f"BM25 Overall: P: {metrics_bm25['precision']:.4f} | R: {metrics_bm25['recall']:.4f} | F1: {metrics_bm25['f1']:.4f} | Acc: {metrics_bm25['accuracy']:.4f}")
    print(f"BM25 Confusion Matrix: TP={comb['tp']}, FP={comb['fp']}, TN={comb['tn']}, FN={comb['fn']}")

    return metrics_bm25

def run_privilege_regex_baseline(benchmark_results: List[Dict]):
    print("\n" + "=" * 80)
    print("PART C.2: PRIVILEGE BASELINE (REGEX ONLY, NO LLM REASONING)")
    print("=" * 80)

    with open(SYNTH_BENCHMARK_CSV, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    tp, fp, tn, fn = 0, 0, 0, 0
    details = []

    for r in rows:
        text = r["text"].lower()
        gt = (r["is_privileged"] == "TRUE")

        # Standard regex detection without LLM disambiguation
        # Check all regex patterns in PRIVILEGE_PATTERNS
        regex_hit = False
        for p_type, cfg in PRIVILEGE_PATTERNS.items():
            for pat in cfg["patterns"]:
                if re.search(pat, text):
                    regex_hit = True
                    break
            if regex_hit:
                break

        if gt and regex_hit:
            tp += 1
        elif not gt and regex_hit:
            fp += 1
        elif not gt and not regex_hit:
            tn += 1
        elif gt and not regex_hit:
            fn += 1

        details.append({
            "benchmark_id": r["benchmark_id"],
            "ground_truth": gt,
            "regex_detected": regex_hit
        })

    metrics = calculate_metrics(tp, fp, tn, fn)
    print(f"Regex-Only Baseline Precision: {metrics['precision']:.4f}")
    print(f"Regex-Only Baseline Recall:    {metrics['recall']:.4f}")
    print(f"Regex-Only Baseline F1 Score:  {metrics['f1']:.4f}")
    print(f"Regex-Only Confusion Matrix: TP={tp}, FP={fp}, TN={tn}, FN={fn}")
    return metrics

# ─────────────────────────────────────────────────────────────────────────────
# MAIN EXECUTION
# ─────────────────────────────────────────────────────────────────────────────
async def main():
    start_all = time.time()
    
    # 1. Relevance Evaluation (Enron 400 docs)
    enron_rows, doc_texts, rel_by_split, rel_comb, disagreements, rel_thresh, chunk_scores = await run_relevance_evaluation()

    # 2. Privilege Evaluation (Synthetic 24 docs)
    priv_metrics, hard_negs, genuine_privs, priv_results, priv_runtime, priv_api_calls = await run_privilege_evaluation()

    # 3. Baselines
    bm25_metrics = run_relevance_bm25_baseline(enron_rows, doc_texts)
    regex_priv_metrics = run_privilege_regex_baseline(priv_results)

    # 4. Save evaluation artifact
    eval_summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "relevance": {
            "threshold": rel_thresh,
            "by_split": rel_by_split,
            "combined": rel_comb,
            "bm25_baseline": bm25_metrics,
            "disagreements": disagreements
        },
        "privilege": {
            "hybrid_metrics": priv_metrics,
            "regex_baseline_metrics": regex_priv_metrics,
            "runtime_seconds": priv_runtime,
            "api_call_count": priv_api_calls,
            "hard_negatives": hard_negs,
            "genuine_privileges": genuine_privs
        }
    }

    out_json = os.path.join(BASE_DIR, "data", "full_evaluation_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(eval_summary, f, indent=2)

    print("\n" + "=" * 80)
    print(f"FULL EVALUATION COMPLETED IN {time.time() - start_all:.1f}s")
    print(f"Results saved to: {out_json}")
    print("=" * 80)

if __name__ == "__main__":
    import re
    asyncio.run(main())
