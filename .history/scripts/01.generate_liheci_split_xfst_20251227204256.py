#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generate_liheci_split_xfst_v3.py

从 data/liheci_lexicon.csv 自动生成：data/liheci_split.xfst

编译：
    hfst-xfst < data/liheci_split.xfst

生成：
    data/liheci_split.generator.hfst   (upper: lemma-tag → lower: 句子模式)
    data/liheci_split.analyser.hfst    (upper: 句子 → lower: lemma-tag)

输出标签示例：
    散心+Lemma+Verb-Object+WHOLE
    散心+Lemma+Verb-Object+SPLIT
    散心+Lemma+Verb-Object+SPLIT+REDUP

关键约束：
- SPLIT 插入语中：允许任意长度，但 **不允许任何标点符号**
- 一旦出现标点，就视为断开（后续你要做句法分析再处理）
"""

import csv
from pathlib import Path

INPUT_CSV = "data/liheci_lexicon.csv"
OUTPUT_XFST = "data/liheci_split.xfst"

OUTPUT_GENERATOR = "data/liheci_split.generator.hfst"
OUTPUT_ANALYSER = "data/liheci_split.analyser.hfst"

# 把 union 拆块，避免 regex 一行超长 & 也避免你之前那种“多行 regex 被当成多条命令”
UNION_CHUNK_SIZE = 40


def map_type_tag(type_str: str) -> str:
    """
    把 CSV 里的 Type 映射到 HFST 用的类型标签（无空格）。
    例：Verb-Object, Pseudo V-O, Modifier-Head, Simplex Word
    """
    t = (type_str or "").strip()
    if not t:
        return "UnknownType"
    return t.replace(" ", "")


def has_redup(notes: str) -> bool:
    """
    Notes 里含 'AAB' 就当作这个 lemma 支持重叠形式
    （比如 散散心(AAB)，握了一下手(AAB) 等）
    """
    return bool(notes) and ("AAB" in notes)


def chars_with_space(s: str) -> str:
    """把字符串拆成单字符并用空格隔开，供 xfst 正则使用。"""
    s = (s or "").strip()
    if not s:
        return ""
    return " ".join(list(s))


def chunked(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def main():
    input_path = Path(INPUT_CSV)
    if not i
