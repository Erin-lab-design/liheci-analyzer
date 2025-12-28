#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Liheci Project – HFST + HanLP Analyzer (Blind Mode)

用法示例：

1) 跑测试集（默认）：
   python3 liheci_pipeline.py
   python3 liheci_pipeline.py --mode test

2) 现场测试（交互模式）：
   python3 liheci_pipeline.py --mode repl

环境要求：
- liheci_lexicon.csv      词表
- liheci_split.analyser.hfst  你前面编好的 HFST 分析器
- HanLP 已可用 (pip install hanlp)

可通过环境变量指定 HFST 路径：
- HFST_LOOKUP_BIN: hfst-lookup 可执行文件路径
- LIHECI_SPLIT_FST: liheci_split.analyser.hfst 路径
"""

import os
import sys
import subprocess
import argparse
import pandas as pd
import hanlp


# =========================
# 0. 全局配置
# =========================

LEXICON_CSV = "liheci_lexicon.csv"
TEST_FILE = "test_sentences.txt"
REPORT_FILE = "test_report_analyzer.txt"

# HFST 可执行文件 & FST 文件
HFST_LOOKUP_BIN = os.environ.get(
    "HFST_LOOKUP_BIN",
    "hfst-lookup"  # Puhti 上可以直接用这个；在 Mac 上可以 export HFST_LOOKUP_BIN=/Users/mac/Downloads/hfst-bin-mac-64/hfst-lookup
)

HFST_SPLIT_FST = os.environ.get(
    "LIHECI_SPLIT_FST",
    "liheci_split.analyser.hfst"
)


# =========================
# 1. 读取词典 & 建元信息表
# =========================

def load_lexicon(csv_path: str):
    print(f"[Init] Loading Lexicon from {csv_path}...")
    try:
        df = pd.read_csv(csv_path, sep=None, engine="python", index_col=False)
        df.columns = [c.strip() for c in df.columns]
    except Exception as e:
        print(f"[Error] Failed to load '{csv_path}': {e}")
        sys.exit(1)

    lemma_meta = {}

    for idx, row in df.iterrows():
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
            "raw_row": row.to_dict(),
        }

    print(f"[Init] Loaded {len(lemma_meta)} lemmas from lexicon.")
    return lemma_meta


# =========================
# 2. HanLP 初始化
# =========================

def init_hanlp():
    print("[Init] Loading HanLP Models...")
    tokenizer = hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH)
    tagger = hanlp.load(hanlp.pretrained.pos.CTB9_POS_ELECTRA_SMALL)
    return tokenizer, tagger


# =========================
# 3. HFST 调用 & 结果解析
# =========================

def run_hfst_split(sentence: str):
    """
    调用 HFST 分析器，返回该句中所有离合词分析标签列表（字符串形式）。
    例如：
        "散心+Lemma+Verb-Object+SPLIT+REDUP"
        "谈恋爱+Lemma+Verb-Object+WHOLE"
    """
    if not os.path.exists(HFST_SPLIT_FST):
        print(f"[Error] Cannot find HFST FST file: {HFST_SPLIT_FST}")
        return []

    try:
        proc = subprocess.Popen(
            [HFST_LOOKUP_BIN, HFST_SPLIT_FST],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    except FileNotFoundError:
        print(f"[Error] Cannot find hfst-lookup executable: {HFST_LOOKUP_BIN}")
        return []

    out, err = proc.communicate(sentence + "\n")

    analyses = []

    for line in out.splitlines():
        line = line.strip()
        if not line.startswith(">"):
            continue
        # 去掉 "> "
        content = line[1:].strip()
        if not content:
            continue
        # surface, analysis, weight
        parts = content.split()
        if len(parts) < 2:
            continue
        surface, analysis = parts[0], parts[1]
        # 只保留包含 +Lemma 的分析
        if "+Lemma" in analysis:
            analyses.append(analysis)

    # 去重且排序，方便阅读
    analyses = sorted(set(analyses))
    return analyses


def parse_hfst_analysis(analysis: str):
    """
    解析 HFST 分析标签。
    输入示例: "散心+Lemma+Verb-Object+SPLIT+REDUP"
    返回:
        lemma, type_str, shape, is_redup
        其中 type_str 来自标签里的 Type（如果有），否则为 None
        shape ∈ {"WHOLE", "SPLIT", None}
    """
    parts = analysis.split("+")
    lemma = parts[0]
    tags = parts[1:]

    type_str = None
    shape = None
    is_redup = False

    for t in tags:
        if t in {"Verb-Object", "PseudoV-O", "Modifier-Head", "Simplex", "SimplexWord", "Simplex-Word"}:
            type_str = t
        elif t in {"WHOLE", "SPLIT"}:
            shape = t
        elif t == "REDUP":
            is_redup = True

    return lemma, type_str, shape, is_redup


# =========================
# 4. 分析单句：HFST + HanLP
# =========================

def analyze_sentence(sentence: str,
                     lemma_meta: dict,
                     tokenizer,
                     tagger,
                     fout=None):
    """
    对单句做离合词分析：
    - 先用 HFST 找出所有可能的离合词（及 WHOLE/SPLIT/REDUP）
    - 再用 HanLP 做分词+POS，只做记录，不强行过滤
    返回：所有检测到的 lemma 列表（去重）
    """
    if fout is not None:
        fout.write(f"Sentence: {sentence}\n")

    # 1) HFST 分析
    hfst_raw = run_hfst_split(sentence)
    if fout is not None:
        fout.write(f"   [HFST Analyses]: {hfst_raw if hfst_raw else 'None'}\n")

    if not hfst_raw:
        if fout is not None:
            fout.write("   [Result]: No liheci detected by HFST.\n\n")
        return []

    # 2) HanLP 分词 & POS
    words = tokenizer(sentence)
    tags = tagger(words)
    if fout is not None:
        hanlp_str = " ".join(f"{w}/{t}" for w, t in zip(words, tags))
        fout.write(f"   [HanLP Tokens]: {hanlp_str}\n")

    # 3) 逐个 HFST 分析，结合 lexicon + HanLP 做一点轻量解释
    detected_lemmas = []

    for ana in hfst_raw:
        lemma, type_from_fst, shape, is_redup = parse_hfst_analysis(ana)
        meta = lemma_meta.get(lemma)

        # 词典中不存在（理论上不会），直接跳过
        if meta is None:
            if fout is not None:
                fout.write(f"   [Warn] Lemma [{lemma}] not in CSV lexicon, raw tag = {ana}\n")
            continue

        head = meta["head"]
        tail = meta["tail"]
        type_str = meta["type"]  # 用 CSV 的 Type 为准

        if lemma not in detected_lemmas:
            detected_lemmas.append(lemma)

        # 一点点对齐解释：看 HanLP 的 token 里 head/tail 出现情况
        head_pos_list = []
        tail_pos_list = []

        for w, t in zip(words, tags):
            if head and w.startswith(head):
                head_pos_list.append(f"{w}/{t}")
            if tail and (w == tail or w.endswith(tail)):
                tail_pos_list.append(f"{w}/{t}")

        if fout is not None:
            fout.write(f"   -> Lemma: {lemma} | Type: {type_str} | Shape: {shape or '-'}"
                       f"{' +REDUP' if is_redup else ''}\n")
            fout.write(f"      Head={head} tokens: {head_pos_list if head_pos_list else 'None'}\n")
            fout.write(f"      Tail={tail} tokens: {tail_pos_list if tail_pos_list else 'None'}\n")

    if fout is not None:
        fout.write(f"   [Detected Lemmas]: {detected_lemmas if detected_lemmas else 'None'}\n\n")

    return detected_lemmas


# =========================
# 5. 跑测试集：test_sentences.txt
# =========================

def run_test_suite(lemma_meta, tokenizer, tagger):
    print(f"[Run] Processing {TEST_FILE}...")
    total = 0
    passed = 0

    try:
        fin = open(TEST_FILE, "r", encoding="utf-8")
    except Exception as e:
        print(f"[Error] Cannot open test file '{TEST_FILE}': {e}")
        return

    with fin, open(REPORT_FILE, "w", encoding="utf-8") as fout:
        fout.write("TEST REPORT | Liheci HFST + HanLP Analyzer (Blind Mode)\n")
        fout.write("========================================================\n\n")

        for line in fin:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 3:
                continue

            target_lemma, sentence, expect_flag = parts
            expect_true = expect_flag.lower() == "true"

            fout.write("-" * 60 + "\n")
            fout.write(f"Target Lemma: [{target_lemma}]\n")

            detected_lemmas = analyze_sentence(
                sentence,
                lemma_meta,
                tokenizer,
                tagger,
                fout=fout
            )

            actual_detected = (target_lemma in detected_lemmas)
            status = "PASS" if actual_detected == expect_true else "FAIL"

            fout.write(f"Expected: {expect_true} | Actual: {actual_detected} | Status: {status}\n\n")

            total += 1
            if status == "PASS":
                passed += 1

            # 让终端有一点进度感
            print(f"\r[Run] Processed {total} cases...", end="")

        fout.write("\n")
        fout.write("=" * 60 + "\n")
        if total > 0:
            acc = passed / total * 100.0
            fout.write(f"SUMMARY: {passed}/{total} passed ({acc:.2f}%)\n")
        else:
            fout.write("SUMMARY: No valid test cases found.\n")

    print("\n[Done] Test suite finished. See report:", REPORT_FILE)


# =========================
# 6. 交互模式：现场输句子
# =========================

def repl_mode(lemma_meta, tokenizer, tagger):
    print("=" * 60)
    print("  Liheci Project – Interactive Mode")
    print("  输入一句中文（回车），我会给出 HFST + HanLP 分析")
    print("  输入空行或 Ctrl+C 结束")
    print("=" * 60)

    while True:
        try:
            s = input("\nSentence> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Exit] Bye~")
            break

        if not s:
            print("[Exit] Empty line, bye~")
            break

        # 直接把分析写到 stdout，而不是文件
        analyze_sentence(s, lemma_meta, tokenizer, tagger, fout=sys.stdout)


# =========================
# 7. main
# =========================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["test", "repl"],
        default="test",
        help="test: 跑 test_sentences.txt；repl: 交互模式现场输入句子"
    )
    args = parser.parse_args()

    lemma_meta = load_lexicon(LEXICON_CSV)
    tokenizer, tagger = init_hanlp()

    if args.mode == "test":
        run_test_suite(lemma_meta, tokenizer, tagger)
    else:
        repl_mode(lemma_meta, tokenizer, tagger)


if __name__ == "__main__":
    main()
