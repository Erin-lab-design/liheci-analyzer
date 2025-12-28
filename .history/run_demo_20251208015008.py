# run_demo.py
import hanlp
import pandas as pd   # 你可以保留，万一别处还用
import sys
import io
import hfst

from liheci_config import (
    load_lexicon,
    build_whole_path,
    build_split_rules,
    DEFAULT_INPUT_CSV,
)

# ==========================================
# 配置
# ==========================================
INPUT_CSV = DEFAULT_INPUT_CSV
TEST_FILE = "test_sentences.txt"
OUTPUT_REPORT = "test_report.txt"

print("="*60)
print("  Liheci Project - Python FST Engine + HFST Lexicon")
print("="*60)

# ==========================================
# 1. 初始化 (加载词典并构建 FST 规则)
# ==========================================
print(f"[Init] Loading Lexicon from {INPUT_CSV}...")

df = load_lexicon(INPUT_CSV)
fst_whole_path = build_whole_path(df)
fst_split_rules = build_split_rules(df)

# （可选）加载 HFST 词典，后面想用就用，不想用也不影响你当前逻辑
try:
    hfst_in = hfst.HfstInputStream("liheci_whole.hfst")
    whole_lex_fst = hfst_in.read()
    hfst_in.close()
    USE_HFST_WHOLE = True
    print("[Init] Loaded HFST lexicon: liheci_whole.hfst")
except Exception as e:
    USE_HFST_WHOLE = False
    whole_lex_fst = None
    print("[Warn] Cannot load liheci_whole.hfst, fall back to Python dict only.")

def analyze_sentence(text, target_lemma, file_handle):
    # 1. HanLP 分词
    words = tokenizer(text)
    tags = tagger(words)

    hanlp_output = " ".join([f"{w}/{t}" for w, t in zip(words, tags)])
    file_handle.write(f"   [HanLP Input]: {hanlp_output}\n")

    found = False

    # --- 尝试走 WholePath ---
    for word in words:
        # 如果 HFST 载入成功，就先用 FST 过滤一下：不是 liheci 形式的直接跳过
        if USE_HFST_WHOLE and whole_lex_fst is not None:
            try:
                analyses = whole_lex_fst.lookup(word)
            except Exception:
                analyses = []
            if not analyses:
                # FST 不接受这个词形，肯定不是我们表里的离合词形式
                continue

        # 接下来仍然用你原来的 dict 做 lemma 匹配
        if word in fst_whole_path:
            matched_lemma = fst_whole_path[word]
            if matched_lemma == target_lemma:
                file_handle.write(f"   ✅ [FST Match]: Path=WholeEntry (Fused)\n")
                file_handle.write(f"      - Token:     {word}\n")
                found = True
                break

    # --- SplitPath 部分完全不动你原来的代码 ---
    # （下面照你原来那段就好，我就不重复贴了）
