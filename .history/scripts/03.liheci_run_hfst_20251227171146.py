#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Liheci HFST Exporter (TSV + sent_id cache)

Input: data/test_sentences.txt
Format (TSV):
    sent_id <TAB> gold_stem <TAB> gold_label <TAB> sentence
- Allows comment lines starting with '#'
- Allows header line: sent_id gold_stem gold_label sentence

Behavior:
- Run HFST only once per sent_id (sentence-level analysis)
- Export detected liheci analyses per sentence to OUTPUT_TSV
- Export evaluation per gold row (hit/miss) to EVAL_TSV
"""

import os
import sys
import csv
import subprocess
import logging
from collections import defaultdict

# ======================= 配置 =======================

TEST_FILE = "data/test_sentences.txt"

HFST_LOOKUP_BIN = os.environ.get("HFST_LOOKUP_BIN", "hfst-lookup")
HFST_FST_PATH = os.environ.get("LIHECI_SPLIT_FST", "liheci_recognizer.xfst")

OUTPUT_TSV = "data/liheci_hfst_outputs.tsv"   # 按句子导出 detected analyses
EVAL_TSV = "data/liheci_eval.tsv"             # 按 gold 行导出 hit/mis
LOG_FILE = "outputs/liheci_hfst_run.log"


# ======================= 日志配置 =======================

def setup_logging():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    logging.basicConfig(
        filename=LOG_FILE,
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    return logging.getLogger(__name__)


# ======================= HFST 调用 & 解析 =======================

def parse_hfst_analysis(analysis: str):
    """
    Example analysis:
        睡觉+Lemma+Verb-Object+SPLIT
        散步+Lemma+Verb-Object+SPLIT+REDUP
    Return:
        lemma, type_tag, shape, is_redup
    """
    parts = analysis.split("+")
    lemma = parts[0]
    tags = parts[1:]

    type_tag = None
    shape = None
    is_redup = False

    for t in tags:
        if t in {"Verb-Object", "PseudoV-O", "Modifier-Head",
                 "Simplex", "SimplexWord", "Simplex-Word"}:
            type_tag = t
        elif t in {"WHOLE", "SPLIT"}:
            shape = t
        elif t == "REDUP":
            is_redup = True

    return lemma, type_tag, shape, is_redup


def _split_hfst_line(line: str):
    """
    hfst-lookup output is usually:
        surface \t analysis \t weight
    But sometimes whitespace separated. Handle both.
    """
    if "\t" in line:
        cols = line.split("\t")
        if len(cols) >= 2:
            return cols[0].strip(), cols[1].strip()
    # fallback
    parts = line.split()
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    return None, None


def hfst_analyze_sentence(sentence: str, logger):
    """
    Run HFST on the whole sentence.
    Return list[dict] of detected liheci analyses.
    """
    if not os.path.exists(HFST_FST_PATH):
        msg = f"HFST FST file not found: {HFST_FST_PATH}"
        print("[Error]", msg, file=sys.stderr)
        logger.error(msg)
        return []

    cmd = [HFST_LOOKUP_BIN, HFST_FST_PATH]
    logger.info(f"Running HFST for sentence: {sentence}")
    logger.info(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            input=sentence + "\n",
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        msg = f"hfst-lookup not found: {HFST_LOOKUP_BIN}"
        print("[Error]", msg, file=sys.stderr)
        logger.error(msg)
        return []

    out = result.stdout
    err = result.stderr.strip()

    if err:
        logger.warning(f"HFST STDERR: {err}")

    logger.info("HFST RAW OUTPUT:\n" + out)

    parsed = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            continue

        surface, analysis = _split_hfst_line(line)
        if not surface or not analysis:
            continue

        # Only keep analyses that mark Lemma (your recognizer convention)
        if "+Lemma" not in analysis:
            continue

        lemma, type_tag, shape, is_redup = parse_hfst_analysis(analysis)
        parsed.append({
            "raw": analysis,
            "lemma": lemma,
            "type_tag": type_tag,
            "shape": shape,
            "is_redup": is_redup,
        })

    # dedup by raw
    unique = {item["raw"]: item for item in parsed}
    parsed_unique = list(unique.values())

    logger.info(f"Parsed {len(parsed_unique)} liheci analyses for this sentence.")
    for item in parsed_unique:
        logger.info(f"  - {item}")

    return parsed_unique


# ======================= 读 TSV 测试集 =======================

def load_test_cases_tsv(path: str, logger):
    """
    Returns list of dict:
        {
          sent_id: str,
          gold_stem: str,
          gold_label: bool,
          sentence: str
        }
    """
    cases = []
    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip("\n")
            if not line.strip():
                continue
            if line.lstrip().startswith("#"):
                continue

            # TSV columns
            cols = [c.strip() for c in line.split("\t")]

            # skip header-like lines
            if cols and cols[0] == "sent_id":
                continue

            if len(cols) != 4:
                logger.warning(f"Skipping malformed TSV line (need 4 cols): {raw_line!r}")
                continue

            sent_id, gold_stem, gold_label_str, sentence = cols
            gold_label = gold_label_str.strip().lower() == "true"

            cases.append({
                "sent_id": sent_id,
                "gold_stem": gold_stem,
                "gold_label": gold_label,
                "sentence": sentence,
            })
    return cases


# ======================= 主流程 =======================

def run_export():
    logger = setup_logging()
    os.makedirs(os.path.dirname(OUTPUT_TSV), exist_ok=True)
    os.makedirs(os.path.dirname(EVAL_TSV), exist_ok=True)

    print(f"[Init] Using HFST binary: {HFST_LOOKUP_BIN}")
    print(f"[Init] Using FST file:    {HFST_FST_PATH}")
    print(f"[Init] Output TSV:        {OUTPUT_TSV}")
    print(f"[Init] Eval TSV:          {EVAL_TSV}")
    print(f"[Init] Log file:          {LOG_FILE}")

    logger.info("=== Liheci HFST Exporter started ===")
    logger.info(f"HFST binary: {HFST_LOOKUP_BIN}")
    logger.info(f"FST file:    {HFST_FST_PATH}")
    logger.info(f"Test file:   {TEST_FILE}")
    logger.info(f"Output TSV:  {OUTPUT_TSV}")
    logger.info(f"Eval TSV:    {EVAL_TSV}")

    if not os.path.exists(TEST_FILE):
        msg = f"Test file not found: {TEST_FILE}"
        print("[Error]", msg, file=sys.stderr)
        logger.error(msg)
        sys.exit(1)

    cases = load_test_cases_tsv(TEST_FILE, logger)
    if not cases:
        print("[Warn] Loaded 0 cases from test file. Check formatting / delimiter / path.")
        logger.warning("Loaded 0 cases from test file.")
        return

    # Group by sent_id; one sent_id should map to one sentence
    grouped = defaultdict(list)
    sent_id_to_sentence = {}

    for c in cases:
        sid = c["sent_id"]
        s = c["sentence"]
        if sid in sent_id_to_sentence and sent_id_to_sentence[sid] != s:
            # If you ever have this, your test file is inconsistent
            logger.warning(f"sent_id {sid} has multiple different sentences! Using the first one.")
        sent_id_to_sentence.setdefault(sid, s)
        grouped[sid].append(c)

    # Cache HFST results by sent_id
    cache = {}  # sent_id -> {"analyses": [...], "lemmas": set([...])}

    # Prepare outputs
    with open(OUTPUT_TSV, "w", encoding="utf-8", newline="") as fout_anal, \
         open(EVAL_TSV, "w", encoding="utf-8", newline="") as fout_eval:

        w_anal = csv.writer(fout_anal, delimiter="\t")
        w_eval = csv.writer(fout_eval, delimiter="\t")

        # analyses export header (per sentence per analysis)
        w_anal.writerow([
            "sent_id",
            "sentence",
            "lemma",
            "type_tag",
            "shape",
            "is_redup",
            "raw_analysis",
        ])

        # eval header (per gold row)
        w_eval.writerow([
            "sent_id",
            "gold_stem",
            "gold_label",
            "hit",
            "sentence",
            "detected_lemmas",
            "num_analyses",
        ])

        # metrics counters on gold rows
        TP = FP = TN = FN = 0
        total_sent_ids = 0
        sent_ids_with_hits = 0
        total_exported_analyses = 0

        for sid, rows in grouped.items():
            sentence = sent_id_to_sentence[sid]
            total_sent_ids += 1

            # Run HFST once per sent_id
            analyses = hfst_analyze_sentence(sentence, logger)
            lemmas = set(a["lemma"] for a in analyses)

            cache[sid] = {"analyses": analyses, "lemmas": lemmas}

            if analyses:
                sent_ids_with_hits += 1

            # Export analyses (per sentence)
            for a in analyses:
                w_anal.writerow([
                    sid,
                    sentence,
                    a["lemma"],
                    a["type_tag"],
                    a["shape"],
                    a["is_redup"],
                    a["raw"],
                ])
            total_exported_analyses += len(analyses)

            # Evaluate each gold row (multiple gold_stem per sentence allowed)
            for r in rows:
                gold_stem = r["gold_stem"]
                gold_label = r["gold_label"]
                hit = gold_stem in lemmas

                # update confusion matrix
                if gold_label and hit:
                    TP += 1
                elif gold_label and not hit:
                    FN += 1
                elif (not gold_label) and hit:
                    FP += 1
                else:
                    TN += 1

                w_eval.writerow([
                    sid,
                    gold_stem,
                    gold_label,
                    hit,
                    sentence,
                    ",".join(sorted(lemmas)),
                    len(analyses),
                ])

    # Print summary
    def safe_div(a, b):
        return (a / b) if b else 0.0

    precision = safe_div(TP, TP + FP)
    recall = safe_div(TP, TP + FN)
    f1 = safe_div(2 * precision * recall, precision + recall)

    print("\n[Done]")
    print(f"  Sent_ids processed: {total_sent_ids}")
    print(f"  Sent_ids with at least one detected liheci: {sent_ids_with_hits}")
    print(f"  Total exported analyses: {total_exported_analyses}")
    print(f"  Gold-row metrics: TP={TP} FP={FP} TN={TN} FN={FN}")
    print(f"  Precision={precision:.4f} Recall={recall:.4f} F1={f1:.4f}")
    print(f"  Output analyses TSV: {OUTPUT_TSV}")
    print(f"  Output eval TSV:     {EVAL_TSV}")
    print(f"  Log file:            {LOG_FILE}")

    logger.info("=== Liheci HFST Exporter finished ===")
    logger.info(f"Sent_ids processed: {total_sent_ids}")
    logger.info(f"Sent_ids with hits: {sent_ids_with_hits}")
    logger.info(f"Total exported analyses: {total_exported_analyses}")
    logger.info(f"Gold-row metrics: TP={TP} FP={FP} TN={TN} FN={FN}")
    logger.info(f"Precision={precision:.6f} Recall={recall:.6f} F1={f1:.6f}")


if __name__ == "__main__":
    run_export()
