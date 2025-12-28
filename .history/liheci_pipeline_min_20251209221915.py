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

    print(f"[Init] Loaded {len(lemma_meta)} lemmas from lexicon.")
    return lemma_meta


# 2. 极简句子分析：只做字符串匹配
def analyze_sentence_min(sentence: str, lemma_meta: dict):
    """
    返回：所有 lemma 中，字符串出现在 sentence 里的那些。
    完全不用 HFST / HanLP，只为了确认 pipeline 没问题。
    """
    detected = []
    for lemma in lemma_meta.keys():
        if lemma and lemma in sentence:
            detected.append(lemma)
    return sorted(set(detected))


# 3. 跑测试集
def run_test_suite_min(lemma_meta):
    print(f"[Run] Processing {TEST_FILE} (minimal version)...")
    total = 0
    passed = 0

    try:
        fin = open(TEST_FILE, "r", encoding="utf-8")
    except Exception as e:
        print(f"[Error] Cannot open test file '{TEST_FILE}': {e}")
        return

    with fin, open(REPORT_FILE, "w", encoding="utf-8") as fout:
        fout.write("TEST REPORT | Liheci Minimal Analyzer\n")
        fout.write("======================================\n\n")
        fout.flush()

        for line in fin:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 3:
                continue

            target_lemma, sentence, expect_flag = parts
            expect_true = expect_flag.lower() == "true"

            total += 1

            detected_lemmas = analyze_sentence_min(sentence, lemma_meta)
            actual_detected = (target_lemma in detected_lemmas)
            status = "PASS" if actual_detected == expect_true else "FAIL"

            # 写文件 + flush 让 tail -f 马上能看到
            fout.write("-" * 50 + "\n")
            fout.write(f"Target Lemma: [{target_lemma}]\n")
            fout.write(f"Sentence: {sentence}\n")
            fout.write(f"Detected Lemmas: {detected_lemmas}\n")
            fout.write(f"Expected: {expect_true} | Actual: {actual_detected} | Status: {status}\n\n")
            fout.flush()

            # 终端也打印，确认没卡死
            print(f"[Case {total}] {status} | target={target_lemma} | "
                  f"expected={expect_true} | actual={actual_detected}")

            if status == "PASS":
                passed += 1

        fout.write("\n" + "=" * 50 + "\n")
        if total > 0:
            acc = passed / total * 100.0
            fout.write(f"SUMMARY: {passed}/{total} passed ({acc:.2f}%)\n")
        else:
            fout.write("SUMMARY: No valid test cases found.\n")
        fout.flush()

    print(f"[Done] Minimal test suite finished. {passed}/{total} passed.")
    print(f"[Info] See report file: {REPORT_FILE}")


def main():
    lemma_meta = load_lexicon(LEXICON_CSV)
    run_test_suite_min(lemma_meta)


if __name__ == "__main__":
    main()
