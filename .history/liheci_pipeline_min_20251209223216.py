#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Liheci Project – Minimal HFST + CSV + HanLP Pipeline

对每个句子做三步：
1) 用 HFST 分析整句，找出所有带 +Lemma 的分析，抽出 lemma / Type / WHOLE 或 SPLIT 等信息
2) 在 liheci_lexicon.csv 里查这个 lemma，对应的 head / tail / type
3) 用 HanLP 分词 + 词性，打印整句的 token 序列，看看 head / tail 在哪里、POS 是什么

所有东西直接打印到终端，不写 report 文件，先确保逻辑和调用都 OK。
"""

import os
import sys
import subprocess
import argparse
import pandas as pd
import hanlp

# ========= 全局配置 =========

LEXICON_CSV = "liheci_lexicon.csv"
TEST_FILE = "test_sentences.txt"

HFST_LOOKUP_BIN = os.environ.get("HFST_LOOKUP_BIN", "hfst-lookup")
HFST_SPLIT_FST = os.environ.get("LIHECI_SPLIT_FST", "liheci_split.analyser.hfst")


# ========= 1. 读 CSV 词典 =========

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


# ========= 2. 初始化 HanLP =========

def init_hanlp():
    print("[Init] Loading HanLP models...")
    tokenizer = hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH)
    tagger = hanlp.load(hanlp.pretrained.pos.CTB9_POS_ELECTRA_SMALL)
    print("[Init] HanLP ready.")
    return tokenizer, tagger


# ========= 3. HFST 调用 & 解析 =========

def run_hfst_split(sentence: str):
    """对整句做 HFST 分析，返回所有带 +Lemma 的 analysis 字符串。"""

    if not os.path.exists(HFST_SPLIT_FST):
        print(f"[Error] HFST FST file not found: {HFST_SPLIT_FST}")
        return []

    # 这里加 -q，避免交互提示；如果你本地 hfst-lookup 需要 -i，就改成 ["-q", "-i", HFST_SPLIT_FST]
    cmd = [HFST_LOOKUP_BIN, "-q", HFST_SPLIT_FST]

    try:
        result = subprocess.run(
            cmd,
            input=sentence + "\n",
            capture_output=True,
            text=True,
            timeout=10.0,   # 防止像之前那样卡一个小时
        )
    except FileNotFoundError:
        print(f"[Error] hfst-lookup executable not found: {HFST_LOOKUP_BIN}")
        return []
    except subprocess.TimeoutExpired:
        print("[Error] HFST lookup timeout for sentence:")
        print("       ", sentence)
        return []

    out = result.stdout
    # 如果有 stderr，也顺便打一下
    if result.stderr.strip():
        print("[HFST STDERR]", result.stderr.strip())

    analyses = []
    for line in out.splitlines():
        line = line.strip()
        # 通常输出像：
        # > 句子
        # 句子     分析    权重
        if not line.startswith(">"):
            continue
        content = line[1:].strip()
        if not content:
            continue
        parts = content.split()
        if len(parts) < 2:
            continue
        _surface, analysis = parts[0], parts[1]
        if "+Lemma" in analysis:
            analyses.append(analysis)

    return sorted(set(analyses))


def parse_hfst_analysis(analysis: str):
    """
    输入: "散心+Lemma+Verb-Object+SPLIT+REDUP"
    输出: lemma, type_str, shape, is_redup
    """
    parts = analysis.split("+")
    lemma = parts[0]
    tags = parts[1:]

    type_str = None
    shape = None
    is_redup = False

    for t in tags:
        if t in {"Verb-Object", "PseudoV-O", "Modifier-Head",
                 "Simplex", "SimplexWord", "Simplex-Word"}:
            type_str = t
        elif t in {"WHOLE", "SPLIT"}:
            shape = t
        elif t == "REDUP":
            is_redup = True

    return lemma, type_str, shape, is_redup


# ========= 4. 单句分析：HFST + CSV + HanLP =========

def analyze_sentence(sentence: str, lemma_meta, tokenizer, tagger):
    print("\n" + "=" * 60)
    print("Sentence:", sentence)

    # 1) HFST
    hfst_analyses = run_hfst_split(sentence)
    print("[HFST Analyses]:", hfst_analyses if hfst_analyses else "None")

    detected_lemmas = []

    for ana in hfst_analyses:
        lemma, type_from_fst, shape, is_redup = parse_hfst_analysis(ana)
        meta = lemma_meta.get(lemma)

        if meta is None:
            print(f"  [Warn] Lemma [{lemma}] is not in CSV lexicon; raw tag = {ana}")
            continue

        if lemma not in detected_lemmas:
            detected_lemmas.append(lemma)

        head = meta["head"]
        tail = meta["tail"]
        type_csv = meta["type"]

        print(f"  -> Lemma: {lemma}")
        print(f"     CSV:   Type={type_csv}, head={head}, tail={tail}")
        print(f"     HFST:  Type={type_from_fst or '-'}, shape={shape or '-'}, REDUP={is_redup}")

    # 2) HanLP 分词 + POS
    words = tokenizer(sentence)
    tags = tagger(words)
    hanlp_str = " ".join(f"{w}/{t}" for w, t in zip(words, tags))
    print("[HanLP Tokens]:", hanlp_str)

    # 3) 把 head / tail 在分词里的出现也打印一下（方便你之后写规则）
    for lemma in detected_lemmas:
        meta = lemma_meta[lemma]
        head = meta["head"]
        tail = meta["tail"]
        head_pos_list = []
        tail_pos_list = []
        for w, t in zip(words, tags):
            if head and w.startswith(head):
                head_pos_list.append(f"{w}/{t}")
            if tail and (w == tail or w.endswith(tail)):
                tail_pos_list.append(f"{w}/{t}")
        print(f"  head={head} tokens:", head_pos_list if head_pos_list else "None")
        print(f"  tail={tail} tokens:", tail_pos_list if tail_pos_list else "None")

    print("[Detected Lemmas]:", detected_lemmas if detected_lemmas else "None")
    return detected_lemmas


# ========= 5. 跑测试集（只跑前 N 条，避免卡死） =========

def run_test(lemma_meta, tokenizer, tagger, max_cases=20):
    print(f"[Run] Processing {TEST_FILE} (HFST + CSV + HanLP, first {max_cases} cases)...")

    try:
        fin = open(TEST_FILE, "r", encoding="utf-8")
    except Exception as e:
        print(f"[Error] Cannot open test file '{TEST_FILE}': {e}")
        return

    total = 0
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
        print("\n>>>>>>>>  CASE", total, "<<<<<<<<")
        print(f"Target lemma = [{target_lemma}], Expect = {expect_true}")

        detected = analyze_sentence(sentence, lemma_meta, tokenizer, tagger)
        actual = (target_lemma in detected)
        print(f"[RESULT] Expected={expect_true} | Actual={actual}")

        if max_cases and total >= max_cases:
            break

    fin.close()
    print(f"\n[Done] Processed {total} cases.")


# ========= 6. main =========

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["test", "repl"], default="test")
    parser.add_argument("--max-cases", type=int, default=20,
                        help="只在 test 模式下使用，限制测试句子数")
    args = parser.parse_args()

    lemma_meta = load_lexicon(LEXICON_CSV)
    tokenizer, tagger = init_hanlp()

    if args.mode == "test":
        run_test(lemma_meta, tokenizer, tagger, max_cases=args.max_cases)
    else:
        # 简单交互模式：你随便打一两句看效果
        while True:
            try:
                s = input("\nSentence> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[Exit] Bye~")
                break
            if not s:
                print("[Exit] Empty line, bye~")
                break
            analyze_sentence(s, lemma_meta, tokenizer, tagger)


if __name__ == "__main__":
    main()
