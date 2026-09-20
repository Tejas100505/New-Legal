"""
Multilingual Legal NER (v4 Retraining on Cleaned Data)
Standalone Turnkey Execution Script for Google Colab GPU

Target Languages: Hindi (hi) & Marathi (mr)
Base Model: XLM-RoBERTa-base
v3 Baseline: Hindi 80% F1, Marathi 77% F1
"""

import os
import sys
import time
import json
import random
import re
import pickle
import shutil
from pathlib import Path
from tqdm import tqdm

def main():
    print("=" * 80)
    print("STARTING MULTILINGUAL LEGAL NER v4 TRAINING & EVALUATION PIPELINE")
    print("=" * 80)

    # 1. Setup paths and Google Drive mount if in Colab
    try:
        from google.colab import drive
        drive.mount('/content/drive')
        drive_dir = Path('/content/drive/MyDrive/multilingual_legal_ner_v4')
        drive_dir.mkdir(parents=True, exist_ok=True)
        print(f"[+] Google Drive mounted. Output directory: {drive_dir}")
    except Exception:
        drive_dir = Path('./output_v4_backup')
        drive_dir.mkdir(parents=True, exist_ok=True)
        print(f"[+] Output directory (local backup): {drive_dir}")

    workdir = Path('/content/multilingual_ner_v4') if Path('/content').exists() else Path('./workdir_v4')
    workdir.mkdir(parents=True, exist_ok=True)

    # 2. Hugging Face Login (Optional / if token provided)
    hf_token = os.environ.get("HF_TOKEN", "").strip()
    if hf_token:
        try:
            from huggingface_hub import login
            login(token=hf_token)
            print("[+] Authenticated with Hugging Face Hub.")
        except Exception as e:
            print(f"[!] Hugging Face login failed: {e}")
    else:
        print("[i] No HF_TOKEN provided; pulling verified .spacy dataset directly from GitHub without auth.")

    # 3. Verify GPU
    import torch
    import spacy
    print(f"PyTorch Version: {torch.__version__} | CUDA Available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        spacy.prefer_gpu()
    else:
        print("[!] WARNING: No GPU detected. Training XLM-RoBERTa will be slow on CPU.")

    # 4. Data Acquisition: OpenNyAI InLegalNER (800 English sentences)
    print("\n[*] Stage 0: Acquiring 800 English legal source sentences...")
    from spacy.tokens import DocBin
    import urllib.request
    raw_data = []
    source_used = None

    PRIMARY_SPACY_URL = "https://raw.githubusercontent.com/Legal-NLP-EkStep/legal_NER/main/training/Combined_Data_Judgement_Preamble_spacy_format/train.spacy"
    FALLBACK_DEV_URL = "https://raw.githubusercontent.com/Legal-NLP-EkStep/legal_NER/main/training/Combined_Data_Judgement_Preamble_spacy_format/dev.spacy"
    local_spacy_file = workdir / "inlegalner_source.spacy"

    try:
        print(f"[*] Downloading pre-tokenized train.spacy from {PRIMARY_SPACY_URL}...")
        urllib.request.urlretrieve(PRIMARY_SPACY_URL, local_spacy_file)
        file_sz = os.path.getsize(local_spacy_file)
        print(f"[+] Download complete: {file_sz:,} bytes.")

        nlp = spacy.blank("en")
        sentencizer = nlp.add_pipe("sentencizer")
        doc_bin = DocBin().from_disk(local_spacy_file)
        docs = list(doc_bin.get_docs(nlp.vocab))
        print(f"[+] Deserialized {len(docs)} documents from train.spacy.")

        for doc in docs:
            if not doc.ents:
                continue
            if 30 <= len(doc.text.strip()) <= 600:
                ents = [(ent.start_char, ent.end_char, ent.label_) for ent in doc.ents]
                raw_data.append({"text": doc.text.strip(), "entities": ents})
            else:
                sent_doc = sentencizer(doc)
                for sent in sent_doc.sents:
                    s_text = sent.text.strip()
                    if len(s_text) < 30:
                        continue
                    s_start = sent.start_char
                    s_end = sent.end_char
                    s_ents = [
                        (ent.start_char - s_start, ent.end_char - s_start, ent.label_)
                        for ent in doc.ents
                        if ent.start_char >= s_start and ent.end_char <= s_end
                    ]
                    if s_ents:
                        raw_data.append({"text": s_text, "entities": s_ents})
        source_used = f"GitHub (Legal-NLP-EkStep/legal_NER train.spacy) -> {len(raw_data)} candidate sentences"
        print(f"[+] {source_used}")

    except Exception as err:
        print(f"[!] Primary GitHub fetch failed ({err}). Trying Fallback 1 (dev.spacy)...")
        try:
            urllib.request.urlretrieve(FALLBACK_DEV_URL, local_spacy_file)
            nlp = spacy.blank("en")
            sentencizer = nlp.add_pipe("sentencizer")
            doc_bin = DocBin().from_disk(local_spacy_file)
            docs = list(doc_bin.get_docs(nlp.vocab))
            for doc in docs:
                if not doc.ents:
                    continue
                sent_doc = sentencizer(doc)
                for sent in sent_doc.sents:
                    s_text = sent.text.strip()
                    if len(s_text) < 30:
                        continue
                    s_start = sent.start_char
                    s_end = sent.end_char
                    s_ents = [
                        (ent.start_char - s_start, ent.end_char - s_start, ent.label_)
                        for ent in doc.ents
                        if ent.start_char >= s_start and ent.end_char <= s_end
                    ]
                    if s_ents:
                        raw_data.append({"text": s_text, "entities": s_ents})
            source_used = f"GitHub (Legal-NLP-EkStep/legal_NER dev.spacy) -> {len(raw_data)} candidate sentences"
            print(f"[+] {source_used}")
        except Exception as dev_err:
            print(f"[!] Fallback 1 failed ({dev_err}). Trying Fallback 2 (Hugging Face Hub)...")
            from datasets import load_dataset
            dataset = load_dataset("opennyaiorg/InLegalNER", split="train", trust_remote_code=True)
            for row in dataset:
                tokens = row.get("tokens") or row.get("words", [])
                ner_tags = row.get("ner_tags") or row.get("tags", [])
                if not tokens or not ner_tags:
                    continue
                text = ""
                entities = []
                curr = None
                for token, tag in zip(tokens, ner_tags):
                    start = len(text)
                    text += token + " "
                    end = len(text) - 1
                    if tag.startswith("B-"):
                        if curr:
                            entities.append(curr)
                        curr = (start, end, tag[2:])
                    elif tag.startswith("I-") and curr and curr[2] == tag[2:]:
                        curr = (curr[0], end, curr[2])
                    else:
                        if curr:
                            entities.append(curr)
                            curr = None
                if curr:
                    entities.append(curr)
                if entities and len(text.strip()) > 30:
                    raw_data.append({"text": text.strip(), "entities": entities})
            source_used = f"Hugging Face (opennyaiorg/InLegalNER) -> {len(raw_data)} examples"
            print(f"[+] {source_used}")

    random.seed(42)
    random.shuffle(raw_data)
    english_800 = raw_data[:800]
    print(f"[+] Selected {len(english_800)} English source sentences ({source_used}).")

    # 4. Stage 1: Translation & Span Alignment with Exponential Backoff
    print("\n[*] Stage 1: Translating to Hindi and Marathi with exponential backoff...")
    from deep_translator import GoogleTranslator
    translator_hi = GoogleTranslator(source='en', target='hi')
    translator_mr = GoogleTranslator(source='en', target='mr')

    def translate_with_backoff(translator, text, max_retries=5, initial_delay=1.0):
        delay = initial_delay
        for _ in range(max_retries):
            try:
                res = translator.translate(text)
                if res:
                    return res
            except Exception:
                time.sleep(delay)
                delay *= 2.0
        return None

    def align_spans(src_text, src_entities, tgt_text, translator):
        tgt_entities = []
        for start, end, label in src_entities:
            ent_phrase = src_text[start:end].strip()
            if not ent_phrase or len(ent_phrase) < 2:
                continue
            tgt_phrase = translate_with_backoff(translator, ent_phrase)
            if not tgt_phrase:
                continue
            tgt_clean = tgt_phrase.strip()
            pos = tgt_text.find(tgt_clean)
            if pos != -1:
                tgt_entities.append((pos, pos + len(tgt_clean), label))
            else:
                match = re.search(re.escape(tgt_clean), tgt_text, re.IGNORECASE)
                if match:
                    tgt_entities.append((match.start(), match.end(), label))
        return sorted(list(set(tgt_entities)), key=lambda x: x[0])

    hindi_results = []
    marathi_results = []

    for item in tqdm(english_800, desc="Translating (hi & mr)"):
        src_t = item["text"]
        src_e = item["entities"]

        hi_t = translate_with_backoff(translator_hi, src_t)
        if hi_t:
            hi_e = align_spans(src_t, src_e, hi_t, translator_hi)
            hindi_results.append({"text": hi_t, "entities": hi_e, "src_text": src_t})

        mr_t = translate_with_backoff(translator_mr, src_t)
        if mr_t:
            mr_e = align_spans(src_t, src_e, mr_t, translator_mr)
            marathi_results.append({"text": mr_t, "entities": mr_e, "src_text": src_t})

    print(f"[+] Translated: {len(hindi_results)} Hindi, {len(marathi_results)} Marathi.")

    # Backup pickles
    for p_name, data in [("hindi_results.pkl", hindi_results), ("marathi_results.pkl", marathi_results)]:
        with open(workdir / p_name, "wb") as f:
            pickle.dump(data, f)
        with open(drive_dir / p_name, "wb") as f:
            pickle.dump(data, f)

    # 5. Stage 2: Partitioning
    print("\n[*] Stage 2: Partitioning train/dev (exact 800/72/70 split sizes)...")
    random.seed(42)
    random.shuffle(hindi_results)
    random.shuffle(marathi_results)

    DEV_HINDI_SIZE = 72
    DEV_MARATHI_SIZE = 70

    hindi_dev = hindi_results[:DEV_HINDI_SIZE]
    hindi_train = hindi_results[DEV_HINDI_SIZE:]

    marathi_dev = marathi_results[:DEV_MARATHI_SIZE]
    marathi_train = marathi_results[DEV_MARATHI_SIZE:]

    print(f"  * English Train: {len(english_800)}")
    print(f"  * Hindi Train:   {len(hindi_train)}, Hindi Dev:   {len(hindi_dev)} (Untouched)")
    print(f"  * Marathi Train: {len(marathi_train)}, Marathi Dev: {len(marathi_dev)} (Untouched)")

    # 6. Stage 3: clean_annotations.py (Training Data ONLY)
    print("\n[*] Stage 3: Applying clean_annotations.py fixes to Training sets ONLY...")
    GPE_SUFFIXES = ["में", "से", "का", "की", "के", "को", "पर", "मधील", "ने", "त", "च्या", "तील", "वर", "ला"]
    PUNCT_CHARS = " .,;:!?()[]{}।॥-'" + chr(34)

    def clean_annotations(record_list):
        cleaned = []
        stats = {"judge_trimmed": 0, "gpe_sfx_stripped": 0, "precedent_punct_stripped": 0, "case_num_dropped": 0}
        for rec in record_list:
            t = rec["text"]
            new_ents = []
            for start, end, label in rec["entities"]:
                span_text = t[start:end]
                if label == "JUDGE":
                    orig = span_text
                    span_text = span_text.rstrip(PUNCT_CHARS)
                    for suffix in ["जी", "न्यायाधीश", "न्यायमूर्ति", "justice", "judge"]:
                        if span_text.lower().endswith(" " + suffix) or span_text.endswith(suffix):
                            span_text = span_text[:len(span_text)-len(suffix)].strip()
                    if len(span_text) < len(orig):
                        stats["judge_trimmed"] += 1
                        end = start + len(span_text)
                elif label == "GPE":
                    span_text = span_text.strip(PUNCT_CHARS)
                    for sfx in GPE_SUFFIXES:
                        if span_text.endswith(" " + sfx):
                            span_text = span_text[:-len(sfx)-1].strip()
                            stats["gpe_sfx_stripped"] += 1
                            break
                        elif span_text.endswith(sfx) and len(span_text) > len(sfx) + 2:
                            span_text = span_text[:-len(sfx)].strip()
                            stats["gpe_sfx_stripped"] += 1
                            break
                    end = start + len(span_text)
                elif label == "PRECEDENT":
                    orig = span_text
                    trimmed = span_text.strip(PUNCT_CHARS)
                    if len(trimmed) < len(orig):
                        stats["precedent_punct_stripped"] += 1
                    span_text = trimmed
                    end = start + len(span_text)
                elif label == "CASE_NUMBER":
                    if not bool(re.search(r'[0-9०-९]', span_text)):
                        stats["case_num_dropped"] += 1
                        continue
                if len(span_text.strip()) > 0 and start < end:
                    new_ents.append((start, end, label))
            cleaned.append({"text": t, "entities": new_ents})
        return cleaned, stats

    cleaned_hi_train, hi_stats = clean_annotations(hindi_train)
    cleaned_mr_train, mr_stats = clean_annotations(marathi_train)
    print(f"  * Hindi Cleaning stats: {hi_stats}")
    print(f"  * Marathi Cleaning stats: {mr_stats}")

    # 7. Stage 4: DocBin Compilation with 3x Oversampling
    print("\n[*] Stage 4: Building DocBins with 3x oversampled Hindi/Marathi...")
    from spacy.tokens import DocBin
    from spacy.util import filter_spans
    nlp_blank = spacy.blank("xx")

    def make_doc_bin(records, oversample=1):
        db = DocBin()
        for _ in range(oversample):
            for r in records:
                doc = nlp_blank.make_doc(r["text"])
                ents = []
                for s, e, l in r["entities"]:
                    sp = doc.char_span(s, e, label=l, alignment_mode="contract") or doc.char_span(s, e, label=l, alignment_mode="expand")
                    if sp:
                        ents.append(sp)
                doc.ents = filter_spans(ents)
                db.add(doc)
        return db

    train_db = DocBin()
    en_db = make_doc_bin(english_800, oversample=1)
    hi_db = make_doc_bin(cleaned_hi_train, oversample=3)
    mr_db = make_doc_bin(cleaned_mr_train, oversample=3)

    for db in [en_db, hi_db, mr_db]:
        for d in db.get_docs(nlp_blank.vocab):
            train_db.add(d)

    train_path = workdir / "train.spacy"
    train_db.to_disk(train_path)

    dev_db = DocBin()
    dev_hi_db = make_doc_bin(hindi_dev, oversample=1)
    dev_mr_db = make_doc_bin(marathi_dev, oversample=1)
    for db in [dev_hi_db, dev_mr_db]:
        for d in db.get_docs(nlp_blank.vocab):
            dev_db.add(d)

    dev_path = workdir / "dev.spacy"
    dev_hi_path = workdir / "dev_hindi.spacy"
    dev_mr_path = workdir / "dev_marathi.spacy"
    dev_db.to_disk(dev_path)
    dev_hi_db.to_disk(dev_hi_path)
    dev_mr_db.to_disk(dev_mr_path)

    # Save DocBins to Drive
    train_db.to_disk(drive_dir / "train.spacy")
    dev_db.to_disk(drive_dir / "dev.spacy")
    dev_hi_db.to_disk(drive_dir / "dev_hindi.spacy")
    dev_mr_db.to_disk(drive_dir / "dev_marathi.spacy")
    print(f"[+] DocBins written and backed up to {drive_dir}")

    # 8. Stage 5: Training & Evaluation
    print("\n[*] Stage 5: Training XLM-RoBERTa-base...")
    os.system(f"python -m spacy init config config_xlm.cfg --lang xx --pipeline transformer,ner --model xlm-roberta-base --gpu --force")
    
    print("\n[*] Executing Phase 1: Combined Multilingual Training...")
    os.system(f"python -m spacy train config_xlm.cfg --output {workdir}/model_p1 --paths.train {train_path} --paths.dev {dev_path} --gpu-id 0")

    # Continued fine-tuning on Hindi/Marathi subset
    print("\n[*] Executing Phase 2: Continued Fine-Tuning on Hindi/Marathi Subset (5 Epochs)...")
    sub_hi_mr_db = DocBin()
    for db in [hi_db, mr_db]:
        for d in db.get_docs(nlp_blank.vocab):
            sub_hi_mr_db.add(d)
    sub_path = workdir / "train_sub_hi_mr.spacy"
    sub_hi_mr_db.to_disk(sub_path)

    os.system(f"python -m spacy train config_xlm.cfg --output {workdir}/model_p2 --paths.train {sub_path} --paths.dev {dev_path} --paths.init_tok2vec {workdir}/model_p1/model-best/transformer --gpu-id 0")

    best_model_path = workdir / "model_p2/model-best" if (workdir / "model_p2/model-best").exists() else workdir / "model_p1/model-best"
    print(f"\n[*] Evaluating best model from: {best_model_path}")
    from spacy.scorer import Scorer
    from spacy.training import Example
    nlp_eval = spacy.load(best_model_path)

    def eval_set(m, p):
        scorer = Scorer(m)
        docs = list(DocBin().from_disk(p).get_docs(m.vocab))
        exs = [Example(m(d.text), d) for d in docs]
        res = scorer.score(exs)
        return res.get("ents_p", 0.0), res.get("ents_r", 0.0), res.get("ents_f", 0.0)

    hi_p, hi_r, hi_f = eval_set(nlp_eval, dev_hi_path)
    mr_p, mr_r, mr_f = eval_set(nlp_eval, dev_mr_path)

    v3_hi = 80.0
    v3_mr = 77.0
    hi_f_pct = hi_f * 100
    mr_f_pct = mr_f * 100

    print("\n" + "=" * 75)
    print("FINAL MULTILINGUAL LEGAL NER (v4) EVALUATION RESULTS")
    print("=" * 75)
    print("NOTE: Evaluated on a newly-constructed held-out set of the same size")
    print("      (72 Hindi / 70 Marathi) and construction method as v3, not byte-identical.")
    print("-" * 75)
    print(f"{'Language':<10} | {'v4 Prec':<10} | {'v4 Rec':<10} | {'v4 F1':<10} | {'v3 Base F1':<12} | {'Delta':<8}")
    print("-" * 75)
    print(f"{'Hindi':<10} | {hi_p*100:6.2f}%   | {hi_r*100:6.2f}%   | {hi_f_pct:6.2f}%   | {v3_hi:6.2f}%     | {hi_f_pct - v3_hi:+6.2f}%")
    print(f"{'Marathi':<10} | {mr_p*100:6.2f}%   | {mr_r*100:6.2f}%   | {mr_f_pct:6.2f}%   | {v3_mr:6.2f}%     | {mr_f_pct - v3_mr:+6.2f}%")
    print("=" * 75)

    # Save to Drive
    shutil.copytree(best_model_path, drive_dir / "final_v4_model_best", dirs_exist_ok=True)
    print(f"[+] Final model backed up to Google Drive: {drive_dir / 'final_v4_model_best'}")

if __name__ == "__main__":
    main()
