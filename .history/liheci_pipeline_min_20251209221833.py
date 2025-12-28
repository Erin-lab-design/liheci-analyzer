#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Liheci Project – Minimal Debug Version

- 不用 HanLP，不用 HFST
- 只加载 liheci_lexicon.csv 和 test_sentences.txt
- 规则：如果 lemma 字符串出现在 sentence 里，就算 “检测到”
- 在终端打印每个 case 的结果，同时写到 test_report_min.txt
"""

import sys
import pandas as pd

LEXICON_CSV = "liheci_lexicon.csv"
TEST_FILE = "test_sentences.txt"
REPORT_FILE = "test_report_min.txt"


# 1. 加载词典（和原版结构保持一致）
def load_lexicon(csv_path: str):
    print(f"[Init] Loading Lexicon from {csv_path}...")
    try:
        df = pd.read_csv(csv_path, sep=None, engine="python", index_col=False)
        df.columns = [c.strip() for c in df.columns]
    except Exception as e:
        print(f"[Error] Failed to load '{csv_path}': {e}")
        sys.exit(1)

    lemma_meta = {}

    for _, row in df.iterrows():
        if not {"Lemma", "A", "B", "Type"}.issubset(row.index):
            continue

        lemma = str(row["Lemma"]).strip()
        head = str(row["A"]).strip()
        tail = str(row["B"]).strip()
        ltype = str(row["Type"]).strip()

        lemma_meta[lemma] = {
            "head": head,
            "tail": tail,
            "type": ltype,
        }

    print(f"[Init] Loaded {len(
