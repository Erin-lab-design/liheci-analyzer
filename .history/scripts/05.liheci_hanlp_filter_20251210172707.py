#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Liheci + HanLP filter on top of HFST outputs.

Reads:
  - data/liheci_lexicon.csv
  - outputs/liheci_hfst_outputs.tsv

Does:
  - For each HFST analysis (lemma, type, shape, is_redup, sentence):
      * Run HanLP segmentation + POS (with caching per sentence)
      * If is_redup=True      -> 直接相信是 REDUP 类型，记录 POS，打上 category=REDUP
      * elif shape=WHOLE      -> 检查整词是否出现在某个 token 中，并看 POS 是否符合类型要求
      * elif shape=SPLIT      -> 用 lexicon 的 head / tail 在分词结果里找 head/tail token，
                                再根据 POS 和类型做一个简单的合法性判断
  - Export:
      outputs/liheci_pos_filtered.tsv

Columns:
  case_id, gold_stem, gold_label, lemma, type_tag, shape, is_redup,
  sentence, tokens, pos_tags,
  category,          # WHOLE / SPLIT / REDUP
  is_valid,          # 我们根据 POS 规则的判定（True/False）
  pattern_type,      # same_token / two_tokens / none (for SPLIT)
  head_token_indices,
  tail_token_indices,
  reason             # 简短文字说明，方便后面 error analysis

NOTE:
  - POS 约束现在是一个比较保守的 heuristics，你可以根据需要在 WHOLE_ALLOWED_POS 和
    SPLIT_POS_RULES 里随时调参。
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

import hanlp


# =========================
# 路径 & 日志
# =========================

THIS_DIR = Path(__file__).resolve().parent      # scripts/
BASE_DIR = THIS_DIR.parent                      # project root

DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "outputs"
LOG_DIR = OUT_DIR / "logs"

LEXICON_CSV = DATA_DIR / "liheci_lexicon.csv"
HFST_TSV = OUT_DIR / "liheci_hfst_outputs.tsv"
OUT_TSV = OUT_DIR / "liheci_pos_filtered.tsv"
LOG_FILE = LOG_DIR / "liheci_hanlp_filter.log"

OUT_DIR.mkdir(exist_ok=True, parents=True)
LOG_DIR.mkdir(exist_ok=True, parents=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# =========================
# POS 规则配置（先给一套可调的 heuristics）
# =========================

VERB_TAGS = {"VV", "VC", "VE"}          # 动词
NOUN_TAGS = {"NN", "NR", "NT"}          # 名词
ADJ_TAGS = {"VA", "JJ"}                 # 形容词 / 形容词性动词

# WHOLE 形式时，允许 lemma 所在 token 的 POS
# None 表示“不做 POS 限制，全都过”
WHOLE_ALLOWED_POS: Dict[str, Any] = {
    "Verb-Object": VERB_TAGS | NOUN_TAGS | ADJ_TAGS,
    "PseudoV-O": VERB_TAGS | NOUN_TAGS | ADJ_TAGS,
    "Modifier-Head": NOUN_TAGS | ADJ_TAGS,
    "SimplexWord": NOUN_TAGS | ADJ_TAGS,
}

# =========================
# 1. 载入 lexicon
# =========================

def load_lexicon(path: Path) -> Dict[str, Dict[str, str]]:
    """
    读取 data/liheci_lexicon.csv
    需要至少有列：Lemma, A, B, Type
    """
    lemma_meta: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf-8") as fin:
        reader = csv.DictReader(fin)
        for row in reader:
            lemma = row.get("Lemma", "").strip()
            if not lemma:
                continue
            head = row.get("A", "").strip()
            tail = row.get("B", "").strip()
            ltype = row.get("Type", "").strip()
            lemma_meta[lemma] = {
                "head": head,
                "tail": tail,
                "type": ltype,
            }
    logger.info("Loaded %d lemmas from lexicon: %s", len(lemma_meta), path)
    return lemma_meta


# =========================
# 2. 载入 HFST 输出
# =========================

def load_hfst_outputs(path: Path) -> List[Dict[str, Any]]:
    """
    读取 outputs/liheci_hfst_outputs.tsv

    Expect columns (9):
      case_id, gold_stem, gold_label, sentence,
      lemma, type_tag, shape, is_redup, raw_analysis
    """
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fin:
        reader = csv.reader(fin, delimiter="\t")
        header = next(reader, None)
        if header is None:
            raise RuntimeError("HFST outputs TSV is empty")

        for row in reader:
            if not row or len(row) < 9:
                continue
            case_id_str, gold_stem, gold_label_str, sentence, lemma, type_tag, shape, is_redup_str, raw = row
            try:
                case_id = int(case_id_str)
            except ValueError:
                continue

            gold_label = gold_label_str.strip().lower() == "true"
            is_redup = is_redup_str.strip().lower() == "true"

            rows.append({
                "case_id": case_id,
                "gold_stem": gold_stem.strip(),
                "gold_label": gold_label,
                "sentence": sentence.strip(),
                "lemma": lemma.strip(),
                "type_tag": type_tag.strip(),
                "shape": shape.strip(),   # e.g. WHOLE / SPLIT
                "is_redup": is_redup,
                "raw": raw.strip(),
            })

    logger.info("Loaded %d HFST analyses from %s", len(rows), path)
    return rows


# =========================
# 3. HanLP 初始化（带 cache）
# =========================

def init_hanlp():
    logger.info("Loading HanLP models...")
    tokenizer = hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH)
    tagger = hanlp.load(hanlp.pretrained.pos.CTB9_POS_ELECTRA_SMALL)
    logger.info("HanLP models ready.")
    return tokenizer, tagger


class HanLPWrapper:
    def __init__(self):
        self.tokenizer, self.tagger = init_hanlp()
        self.cache: Dict[str, Tuple[List[str], List[str]]] = {}

    def tokenize_pos(self, sentence: str) -> Tuple[List[str], List[str]]:
        if sentence in self.cache:
            return self.cache[sentence]
        tokens = self.tokenizer(sentence)
        tags = self.tagger(tokens)
        self.cache[sentence] = (tokens, tags)
        return tokens, tags


# =========================
# 4. 判定函数
# =========================

def check_whole(
    lemma: str,
    type_tag: str,
    tokens: List[str],
    tags: List[str],
) -> Tuple[bool, str, List[int]]:
    """
    WHOLE 形式：
      - 至少有一个 token 含有 lemma 字符串
      - 如果配置了 POS 限制，则这个 token 的 POS 必须在允许集合里
    """
    indices = [i for i, w in enumerate(tokens) if lemma and lemma in w]
    if not indices:
        return False, "lemma_not_found_in_tokens", []

    allowed = WHOLE_ALLOWED_POS.get(type_tag)
    if allowed is None:
        # 不做 POS 限制
        return True, "no_pos_constraint_for_type", indices

    for i in indices:
        if tags[i] in allowed:
            return True, "pos_ok", indices

    return False, "pos_mismatch_all_candidates", indices


def find_head_tail_positions(
    head: str,
    tail: str,
    tokens: List[str],
) -> Tuple[List[int], List[int]]:
    head_idx: List[int] = []
    tail_idx: List[int] = []
    for i, w in enumerate(tokens):
        if head and head in w:
            head_idx.append(i)
        if tail and tail in w:
            tail_idx.append(i)
    return head_idx, tail_idx


def check_split(
    lemma: str,
    type_tag: str,
    head: str,
    tail: str,
    tokens: List[str],
    tags: List[str],
) -> Tuple[bool, str, str, List[int], List[int]]:
    """
    SPLIT 形式：
      - 用 lexicon 的 head / tail 在分词结果中找 head / tail 所在 token
      - 允许：
          * head 和 tail 在同一个 token 中（same_token）：
              - 对 SimplexWord / Modifier-Head 等，类似 WHOLE 处理
          * head 和 tail 在两个不同 token 中（two_tokens）：
              - 对 Verb-Object / PseudoV-O 等，要求大致符合 V + N 模式
    返回：
      (is_valid, reason, pattern_type, head_idx_list, tail_idx_list)
    """
    # head/tail 缺失就直接 fallback WHOLE 判断
    if not head or not tail:
        is_ok, reason, idx = check_whole(lemma, type_tag, tokens, tags)
        return is_ok, f"no_head_or_tail_fallback_whole:{reason}", "fallback", idx, idx

    head_pos, tail_pos = find_head_tail_positions(head, tail, tokens)
    if not head_pos or not tail_pos:
        return False, "no_head_or_tail_token", "none", head_pos, tail_pos

    candidates: List[Tuple[str, int, int]] = []

    for hi in head_pos:
        for ti in tail_pos:
            if hi > ti:
                continue
            if hi == ti:
                # 同一个 token 内，看字符顺序是否合理（head 在前 tail 在后）
                w = tokens[hi]
                idx_h = w.find(head)
                idx_t = w.rfind(tail)
                if idx_h != -1 and idx_t != -1 and idx_h <= idx_t:
                    candidates.append(("same_token", hi, ti))
            else:
                candidates.append(("two_tokens", hi, ti))

    if not candidates:
        return False, "no_valid_head_tail_order", "none", head_pos, tail_pos

    # 对 SimplexWord: 更像是一个整体词，只是字符中间有花活，优先看 same_token
    if type_tag == "SimplexWord":
        for kind, hi, ti in candidates:
            if kind == "same_token":
                allowed = WHOLE_ALLOWED_POS.get(type_tag)
                if allowed is None or tags[hi] in allowed:
                    return True, "simplex_same_token_pos_ok", "same_token", [hi], [ti]
        # 没有 same_token 或 POS 不合格，就视为无效
        return False, "simplex_no_valid_same_token", "none", head_pos, tail_pos

    # 一般情况（Verb-Object / PseudoV-O / Modifier-Head 等）
    # 先试 two_tokens，再试 same_token 当 fallback
    for kind, hi, ti in candidates:
        if kind == "two_tokens":
            # Verb-Object / PseudoV-O：大致 V + N
            if type_tag in {"Verb-Object", "PseudoV-O"}:
                if tags[hi] in VERB_TAGS and tags[ti] in NOUN_TAGS:
                    return True, "split_two_tokens_V_then_N", "two_tokens", [hi], [ti]
            # Modifier-Head：大致 A + N
            elif type_tag == "Modifier-Head":
                if tags[hi] in (ADJ_TAGS | NOUN_TAGS) and tags[ti] in NOUN_TAGS:
                    return True, "split_two_tokens_A_or_N_then_N", "two_tokens", [hi], [ti]
            else:
                # 不认识的类型，先放过
                return True, "split_two_tokens_unknown_type_auto_ok", "two_tokens", [hi], [ti]

    # 如果 two_tokens 都没成功，再看 same_token，可以类比 WHOLE 的 POS 要求
    allowed = WHOLE_ALLOWED_POS.get(type_tag)
    for kind, hi, ti in candidates:
        if kind == "same_token":
            if allowed is None or tags[hi] in allowed:
                return True, "split_same_token_fallback_whole_pos", "same_token", [hi], [ti]

    return False, "split_candidates_all_failed_pos", "none", head_pos, tail_pos


# =========================
# 5. 主流程
# =========================

def main():
    logger.info("=== Liheci HanLP filter starts ===")

    lemma_meta = load_lexicon(LEXICON_CSV)
    hfst_rows = load_hfst_outputs(HFST_TSV)
    hanlp_wrapper = HanLPWrapper()

    total = 0
    redup_count = 0
    valid_whole = 0
    valid_split = 0
    invalid_count = 0

    with OUT_TSV.open("w", encoding="utf-8", newline="") as fout:
        writer = csv.writer(fout, delimiter="\t")

        # 写表头
        writer.writerow([
            "case_id",
            "gold_stem",
            "gold_label",
            "lemma",
            "type_tag",
            "shape",
            "is_redup",
            "sentence",
            "tokens",
            "pos_tags",
            "category",          # WHOLE / SPLIT / REDUP
            "is_valid",
            "pattern_type",      # same_token / two_tokens / none / fallback
            "head_token_indices",
            "tail_token_indices",
            "reason",
        ])

        for row in hfst_rows:
            total += 1
            case_id = row["case_id"]
            gold_stem = row["gold_stem"]
            gold_label = row["gold_label"]
            sentence = row["sentence"]
            lemma = row["lemma"]
            type_tag = row["type_tag"]
            shape = row["shape"]
            is_redup = row["is_redup"]

            # HanLP 分词 + POS（带 cache）
            tokens, tags = hanlp_wrapper.tokenize_pos(sentence)
            tokens_str = " ".join(tokens)
            tags_str = " ".join(tags)

            meta = lemma_meta.get(lemma, {"head": "", "tail": "", "type": type_tag})
            head = meta.get("head", "")
            tail = meta.get("tail", "")

            category = None
            is_valid = False
            pattern_type = "none"
            head_idx_list: List[int] = []
            tail_idx_list: List[int] = []
            reason = ""

            if is_redup:
                category = "REDUP"
                pattern_type = "redup"

                # 1) 先用和 SPLIT 一样的逻辑找 head / tail token 索引
                head_idxs, tail_idxs, pattern_type2, reason2 = find_head_tail_indices(
                    lemma=lemma,
                    type_tag=type_tag,
                    tokens=tokens,
                    pos_tags=pos_tags,
                    lex_head=head_char,
                    lex_tail=tail_char,
                )

                # 如果找到了就用；没找到就留空
                head_token_indices = ",".join(str(i) for i in head_idxs) if head_idxs else ""
                tail_token_indices = ",".join(str(i) for i in tail_idxs) if tail_idxs else ""

                # 2) 决策：redup 我们本来就“信 HFST”
                is_valid = True
                reason = "redup_from_hfst"

                # pattern_type 你可以保持 "redup" 不变，或者
                # pattern_type = pattern_type2 if pattern_type2 else "redup"


            elif shape == "WHOLE":
                category = "WHOLE"
                is_valid, reason, indices = check_whole(
                    lemma=lemma,
                    type_tag=type_tag,
                    tokens=tokens,
                    tags=tags,
                )
                head_idx_list = indices
                tail_idx_list = indices
                if is_valid:
                    valid_whole += 1
                else:
                    invalid_count += 1

            elif shape == "SPLIT":
                category = "SPLIT"
                is_valid, reason, pattern_type, head_idx_list, tail_idx_list = check_split(
                    lemma=lemma,
                    type_tag=type_tag,
                    head=head,
                    tail=tail,
                    tokens=tokens,
                    tags=tags,
                )
                if is_valid:
                    valid_split += 1
                else:
                    invalid_count += 1

            else:
                # 理论上不会来这里：HFST 只给 WHOLE / SPLIT(+REDUP)
                category = "UNKNOWN_SHAPE"
                is_valid = False
                reason = f"unexpected_shape_{shape}"
                invalid_count += 1

            writer.writerow([
                case_id,
                gold_stem,
                str(gold_label),
                lemma,
                type_tag,
                shape,
                str(is_redup),
                sentence,
                tokens_str,
                tags_str,
                category,
                str(is_valid),
                pattern_type,
                ",".join(map(str, head_idx_list)) if head_idx_list else "",
                ",".join(map(str, tail_idx_list)) if tail_idx_list else "",
                reason,
            ])

    logger.info("=== Liheci HanLP filter finished ===")
    logger.info("Total HFST analyses      : %d", total)
    logger.info("REDUP analyses (trusted) : %d", redup_count)
    logger.info("Valid WHOLE by POS       : %d", valid_whole)
    logger.info("Valid SPLIT by POS       : %d", valid_split)
    logger.info("Invalid (filtered out)   : %d", invalid_count)
    logger.info("Output written to: %s", OUT_TSV)


if __name__ == "__main__":
    main()
