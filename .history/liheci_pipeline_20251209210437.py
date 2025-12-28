#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Liheci Project - HFST + HanLP Pipeline

功能：
  - 从 liheci_lexicon.csv 读取离合词表
  - 用 HFST (liheci_split.analyser.hfst) 在整句上检测 WHOLE / SPLIT / REDUP
  - 用 HanLP 做分词+POS，对每个候选 lemma 做 POS 过滤
  - 支持两种模式：
      1) 批量测试：读取 test_sentences.txt，输出 test_report_analyzer.txt
      2) 交互查询：python liheci_pipeline.py interactive
"""

import subprocess
import hanlp
import pandas as pd
import sys
from pathlib import Path

# ==============================
# 路径配置（按需要改）
# ==============================
INPUT_CSV = "liheci_lexicon.csv"
TEST_FILE = "test_sentences.txt"
OUTPUT_REPORT = "test_report_analyzer.txt"

# HFST 调用配置
# Puhti 上一般就是 "hfst-lookup"
# Mac 上可以改成你的绝对路径：
# HFST_BIN = "/Users/mac/Downloads/hfst-bin-mac-64/hfst-lookup"
HFST_BIN = "hfst-lookup"
HFST_SPLIT = "liheci_split.analyser.hfst"


print("=" * 60)
print("  Liheci Project - HFST + HanLP Analyzer (Blind Mode)")
print("=" * 60)


# ==========================================
# 1. 读 Lexicon CSV
# ==========================================
print(f"[Init] Loading Lexicon from {INPUT_CSV}...")

try:
    df = pd.read_csv(INPUT_CSV, sep=None, engine='python', index_col=False)
    df.columns = [c.strip() for c in df.columns]
except Exception as e:
    print(f"Error: 找不到 {INPUT_CSV}. Error: {e}")
    sys.exit(1)

# 建一个按照 lemma 快速索引的 dict
LEXICON = {}
for idx, row in df.iterrows():
    lemma = str(row.get("Lemma", "")).strip()
    if not lemma:
        continue
    LEXICON[lemma] = {
        "A": str(row.get("A", "")).strip(),
        "B": str(row.get("B", "")).strip(),
        "Type": str(row.get("Type", "")).strip(),  # Verb-Object, Pseudo V-O, ...
    }

# POS 限制表：用 CSV 的 Type 名字（你可以按需要微调）
TYPE2_ALLOWED_TAGS = {
    "Verb-Object": ["VV"],
    "Pseudo V-O": ["VV", "VA", "NN"],
    "Modifier-Head": ["NN", "AD", "JJ"],
    "Simplex Word": ["VV", "JJ", "NN"],  # heuristic, 随便给个宽一点的
}


# ==========================================
# 2. HanLP 初始化
# ==========================================
print("[Init] Loading HanLP Models...")
tokenizer = hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH)
tagger = hanlp.load(hanlp.pretrained.pos.CTB9_POS_ELECTRA_SMALL)


# ==========================================
# 3. HFST 调用：句子 → 分析标签列表
# ==========================================
def run_hfst_split(sentence: str):
    """
    调 hfst-lookup liheci_split.analyser.hfst
    返回这一句里所有 HFST 给出的分析标签（去重后的 list[str]）。

    形如：
        "散心+Lemma+Verb-Object+SPLIT+REDUP"
        "谈恋爱+Lemma+Verb-Object+WHOLE"
    """
    try:
        p = subprocess.Popen(
            [HFST_BIN, HFST_SPLIT],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        print(f"[ERROR] 无法找到 HFST_BIN 可执行文件：{HFST_BIN}")
        sys.exit(1)

    out, err = p.communicate(sentence + "\n")

    analyses = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith(">"):
            continue
        # 去掉前面的 "> "
        line = line.lstrip("> ").strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        surface = parts[0].strip()
        ana = parts[1].strip()
        if ana.endswith("+?"):
            # 未知分析
            continue
        analyses.append(ana)

    # 去重
    return sorted(set(analyses))


def parse_hfst_analysis_tag(tag: str):
    """
    把 HFST 的标签字符串解析成 structured dict。

    输入:  "散心+Lemma+Verb-Object+SPLIT+REDUP"
    输出:  {
        "lemma": "散心",
        "hf_type": "Verb-Object",     # FST 里的类型标签
        "flags": {"Lemma", "SPLIT", "REDUP"},
    }
    """
    parts = tag.split("+")
    lemma = parts[0]
    flags = set(parts[1:])

    # 找出其中哪个是 Type（这里简单按 CSV 的类型关键词匹配）
    hf_type = None
    for t in ["Verb-Object", "PseudoV-O", "Pseudo V-O", "Modifier-Head", "SimplexWord", "Simplex Word"]:
        if t in flags:
            hf_type = t
            break

    return {
        "lemma": lemma,
        "hf_type": hf_type,
        "flags": flags,
        "raw": tag,
    }


def normalize_type_for_csv(hf_type: str):
    """
    把 FST 里的 type 标签（无空格版本）映射回 CSV 里的 Type 形式。
    """
    if hf_type is None:
        return None
    mapping = {
        "Verb-Object": "Verb-Object",
        "PseudoV-O": "Pseudo V-O",
        "Pseudo V-O": "Pseudo V-O",
        "Modifier-Head": "Modifier-Head",
        "SimplexWord": "Simplex Word",
        "Simplex Word": "Simplex Word",
    }
    return mapping.get(hf_type, hf_type)


# ==========================================
# 4. 句子级分析核心（HFST + HanLP）
# ==========================================
def analyze_sentence(text: str, file_handle=None):
    """
    核心分析函数：
      - 输入：原始句子文本 text
      - 输出：满足 POS 过滤的 lemma 列表（不含标签，只是 ['散心','谈恋爱',...]）

    注意：这里完全不知道 target_lemma，
          所以可以安全用于盲测。
    """

    # 1) 调 HFST，获取所有候选分析标签
    hfst_tags = run_hfst_split(text)
    parsed = [parse_hfst_analysis_tag(t) for t in hfst_tags]

    if file_handle is not None:
        file_handle.write(f"   [HFST Raw Analyses]: {hfst_tags if hfst_tags else 'None'}\n")

    if not parsed:
        if file_handle is not None:
            file_handle.write("   [Info] HFST 未检测到任何离合词候选。\n")
        return []

    # 2) HanLP 分词 + POS
    words = tokenizer(text)
    tags = tagger(words)

    if file_handle is not None:
        hanlp_output = " ".join(f"{w}/{t}" for w, t in zip(words, tags))
        file_handle.write(f"   [HanLP Input]: {hanlp_output}\n")

    # 把 HanLP token 信息打平，方便 debug
    token_info = list(zip(words, tags))

    # 3) 对每一个 HFST 候选做 POS 过滤
    accepted_lemmas = []

    for ana in parsed:
        lemma = ana["lemma"]
        hf_type = ana["hf_type"]
        flags = ana["flags"]

        # 用 CSV 里的类型为准（更可控）
        lex = LEXICON.get(lemma)
        if not lex:
            # CSV 里没有的 lemma，暂时扔掉也行
            if file_handle is not None:
                file_handle.write(f"   [Warn] Lemma=[{lemma}] 不在 CSV 词表中，跳过。\n")
            continue

        csv_type = lex["Type"]
        head_char = lex["A"]  # 比如 "散","谈","吃"

        # 拿到允许的 POS
        allowed_tags = TYPE2_ALLOWED_TAGS.get(csv_type, ["VV"])

        # 在 HanLP token 里找 head 字 + 合法 POS
        ok = False
        for w, pos in token_info:
            if head_char in w and pos in allowed_tags:
                ok = True
                break

        if not ok:
            if file_handle is not None:
                file_handle.write(
                    f"   [Filter] Lemma=[{lemma}] 被 POS 过滤掉 "
                    f"(Type={csv_type}, head={head_char}, allowed={allowed_tags}).\n"
                )
            continue

        # 通过 POS 过滤
        if file_handle is not None:
            form_flags = [f for f in ["WHOLE", "SPLIT", "REDUP"] if f in flags]
            form_str = "+".join(form_flags) if form_flags else "UNSPEC"
            file_handle.write(
                f"   ✅ [Accepted] Lemma=[{lemma}] "
                f"Type={csv_type} Forms={form_str} Raw={ana['raw']}\n"
            )

        if lemma not in accepted_lemmas:
            accepted_lemmas.append(lemma)

    return accepted_lemmas


# ==========================================
# 5. 测试套件（读取 test_sentences.txt）
# ==========================================
def run_test_suite():
    print(f"[Run] Processing {TEST_FILE}...")
    total = 0
    passed = 0

    with open(TEST_FILE, "r", encoding="utf-8") as f_in, \
            open(OUTPUT_REPORT, "w", encoding="utf-8") as f_out:

        f_out.write("TEST REPORT | HFST + HanLP Liheci Analyzer (Blind Mode)\n")
        f_out.write("=======================================================\n")

        for line in f_in:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 3:
                continue

            target_lemma = parts[0]
            sentence = parts[1]
            expect_true = (parts[2].lower() == "true")

            f_out.write("\n--------------------------------------------------\n")
            f_out.write(f"Target (for testing): [{target_lemma}]\n")
            f_out.write(f"Sentence:             {sentence}\n")

            # ★ 核心：analyze_sentence 完全不知道 target_lemma，只看 sentence
            detected_lemmas = analyze_sentence(sentence, f_out)

            # 评分逻辑：
            #   - expect_true=True 时，希望 target_lemma 出现在 detected_lemmas 里
            #   - expect_true=False 时，希望 target_lemma 不在 detected_lemmas 里
            actual_detected = target_lemma in detected_lemmas
            status = "PASS" if actual_detected == expect_true else "FAIL"

            f_out.write(f"Detected Lemmas:      {detected_lemmas if detected_lemmas else 'None'}\n")
            f_out.write(
                f"Expected:             {expect_true} | "
                f"Actual Found: {actual_detected} | Status: {status}\n"
            )

            total += 1
            if status == "PASS":
                passed += 1

            print(f"\rProcessed {total} cases...", end="")

        if total > 0:
            acc = passed / total * 100
        else:
            acc = 0.0
        f_out.write(f"\n\nSUMMARY: {passed}/{total} Passed ({acc:.2f}%)\n")

    print(f"\n[Done] Check {OUTPUT_REPORT}")


# ==========================================
# 6. 交互模式：现场输入句子查询
# ==========================================
def interactive_mode():
    print("\n[Interactive] 输入一句中文（空行退出）：")
    while True:
        try:
            s = input("> ").strip()
        except EOFError:
            break
        if not s:
            break

        # 只在终端打印结果，不写报告文件
        print(f"\n[Sentence] {s}")
        # 临时收集日志信息
        from io import StringIO
        buf = StringIO()
        lemmas = analyze_sentence(s, buf)

        print(buf.getvalue())
        print(f"[Final Accepted Lemmas]: {lemmas if lemmas else 'None'}")
        print("-" * 40)


# ==========================================
# 7. 主入口
# ==========================================
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].lower().startswith("inter"):
        # python liheci_pipeline.py interactive
        interactive_mode()
    else:
        # python liheci_pipeline.py
        run_test_suite()
