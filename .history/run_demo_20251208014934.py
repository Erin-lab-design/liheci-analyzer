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
