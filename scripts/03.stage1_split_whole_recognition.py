#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Liheci HFST Exporter

功能：
- 读取 test_sentences.txt （格式：stem | Sentence | True/False）
- 对“句子”部分调用 liheci_split.analyser.hfst 做句子级分析
- 解析 HFST 输出中的：
    - lemma
    - type_tag (Verb-Object / PseudoV-O / Modifier-Head / SimplexWord)
    - shape (WHOLE / SPLIT)
    - is_redup (是否带 REDUP)
- 只对 “至少识别出一个离合词” 的句子写入 TSV 输出文件
- 同时把详细信息写入 log 文件，方便后续调试和溯源
"""

import os
import sys
import csv
import subprocess
import logging

# ======================= 配置 =======================

TEST_FILE = "data/test_sentences.txt"

# HFST 可执行文件
HFST_LOOKUP_BIN = os.environ.get("HFST_LOOKUP_BIN", "hfst-lookup")

# 句子级分析器
HFST_FST_PATH = os.environ.get("LIHECI_SPLIT_FST", "scripts/hfst_files/liheci_split.analyser.hfst")

# 只保留识别出离合词的句子的结构化输出
OUTPUT_TSV = "outputs/liheci_hfst_outputs.tsv"

# 详细 log
LOG_FILE = "outputs/liheci_hfst_run.log"

# Timeout setting (seconds)
HFST_TIMEOUT = 30


# ======================= 日志配置 =======================

def setup_logging():
    logging.basicConfig(
        filename=LOG_FILE,
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )
    logger = logging.getLogger(__name__)
    return logger


# ======================= HFST 调用 & 解析 =======================

def parse_hfst_analysis(analysis: str):
    """
    输入例子: "睡觉+Lemma+Verb-Object+SPLIT"
            "散步+Lemma+Verb-Object+SPLIT+REDUP"
    返回:
        lemma, type_tag, shape
    """
    parts = analysis.split("+")
    lemma = parts[0]
    tags = parts[1:]

    type_tag = None
    shape = None

    for t in tags:
        if t in {"Verb-Object", "PseudoV-O", "Modifier-Head",
                 "Simplex", "SimplexWord", "Simplex-Word"}:
            type_tag = t
        elif t in {"WHOLE", "SPLIT"}:
            shape = t

    return lemma, type_tag, shape


def hfst_analyze_sentence(sentence: str, logger):
    """
    Use liheci_split.analyser.hfst to analyze a sentence.
    Returns a list of analysis dicts.
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
            encoding='utf-8',
            check=False,
            timeout=HFST_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        msg = f"HFST lookup timeout after {HFST_TIMEOUT}s"
        print("[Error]", msg, file=sys.stderr)
        logger.error(msg)
        return []
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
        if not line or line.startswith(">"):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        surface = parts[0]
        analysis = parts[1]

        if "+Lemma" not in analysis:
            continue

        lemma, type_tag, shape = parse_hfst_analysis(analysis)

        parsed.append({
            "raw": analysis,
            "lemma": lemma,
            "type_tag": type_tag,
            "shape": shape,
        })

    # Deduplicate by raw analysis
    unique_by_raw = {}
    for item in parsed:
        unique_by_raw[item["raw"]] = item
    parsed_unique = list(unique_by_raw.values())

    logger.info(f"Parsed {len(parsed_unique)} liheci analyses.")
    for item in parsed_unique:
        logger.info(f"  - {item}")

    return parsed_unique

    return parsed_unique


# ======================= 主流程：读 test_sentences.txt =======================

def run_export():
    logger = setup_logging()
    print(f"[Init] Using HFST binary: {HFST_LOOKUP_BIN}")
    print(f"[Init] Using FST file:    {HFST_FST_PATH}")
    print(f"[Init] Output TSV:        {OUTPUT_TSV}")
    print(f"[Init] Log file:          {LOG_FILE}")

    logger.info("=== Liheci HFST Exporter started ===")
    logger.info(f"HFST binary: {HFST_LOOKUP_BIN}")
    logger.info(f"FST file:    {HFST_FST_PATH}")
    logger.info(f"Test file:   {TEST_FILE}")
    logger.info(f"Output TSV:  {OUTPUT_TSV}")

    try:
        fin = open(TEST_FILE, "r", encoding="utf-8")
    except OSError as e:
        msg = f"Cannot open test file '{TEST_FILE}': {e}"
        print("[Error]", msg, file=sys.stderr)
        logger.error(msg)
        sys.exit(1)

    # 准备 TSV 输出
    fout = open(OUTPUT_TSV, "w", encoding="utf-8", newline="")
    writer = csv.writer(fout, delimiter="\t")

    # 写 header
    writer.writerow([
        "sent_id",
        "gold_stem",
        "gold_label",
        "error_type",
        "sentence",
        "lemma",
        "type_tag",
        "shape",
        "hfst_analysis",
    ])

    total_cases = 0
    cases_with_hits = 0
    total_analyses = 0

    for raw_line in fin:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = [p.strip() for p in line.split("\t")]
        
        # 跳过表头行
        if parts[0] == "sent_id":
            continue
            
        if len(parts) != 4:
            logger.warning(f"Skipping malformed line: {raw_line!r}")
            continue

        sent_id, gold_stem, gold_label_str, sentence = parts
        gold_label = gold_label_str.lower() == "true"
        
        # Extract error_type tag from sentence if present (only for False cases)
        error_type = ""
        if not gold_label and sentence.startswith("["):
            end_bracket = sentence.find("]")
            if end_bracket != -1:
                error_type = sentence[1:end_bracket]
                sentence = sentence[end_bracket + 1:].strip()

        total_cases += 1

        print("\n" + "=" * 60)
        print(f"[Case {sent_id}]")
        print(f"Gold stem   : [{gold_stem}]")
        print(f"Sentence    : {sentence}")
        print(f"Gold label  : {gold_label}")
        if error_type:
            print(f"Error type  : [{error_type}]")

        logger.info("=" * 60)
        logger.info(f"Case {sent_id}: stem=[{gold_stem}], gold_label={gold_label}")
        logger.info(f"Sentence: {sentence}")

        analyses = hfst_analyze_sentence(sentence, logger)

        if not analyses:
            print("[HFST] No liheci detected.")
            logger.info("No liheci detected for this sentence.")
            continue

        # 至少有一个离合词
        cases_with_hits += 1
        total_analyses += len(analyses)

        # 打印到终端
        print("[HFST Analyses]:", [a["raw"] for a in analyses])
        print("[Detected Lemmas]:", sorted(set(a["lemma"] for a in analyses)))

        # 写入 TSV：每个 analysis 一行
        for a in analyses:
            writer.writerow([
                sent_id,
                gold_stem,
                gold_label,
                error_type,
                sentence,
                a["lemma"],
                a["type_tag"],
                a["shape"],
                a["raw"],
            ])

    fin.close()
    fout.close()

    print("\n[Done] Processed", total_cases, "cases.")
    print("       Cases with at least one liheci:", cases_with_hits)
    print("       Total liheci analyses exported:", total_analyses)
    print("       Output TSV:", OUTPUT_TSV)
    print("       Log file  :", LOG_FILE)

    logger.info("=== Liheci HFST Exporter finished ===")
    logger.info(f"Total cases: {total_cases}")
    logger.info(f"Cases with hits: {cases_with_hits}")
    logger.info(f"Total analyses exported: {total_analyses}")


if __name__ == "__main__":
    run_export()
