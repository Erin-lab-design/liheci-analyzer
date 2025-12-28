#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Liheci + HanLP readable report on top of liheci_pos_filtered.tsv

Reads:
  - data/liheci_lexicon.csv
  - outputs/liheci_pos_filtered.tsv

Produces:
  1) outputs/liheci_pos_summary.tsv
     One row per HFST analysis (case_id + lemma + shape).
  2) outputs/liheci_pos_summary.txt
     Human-readable blocks (for manual inspection).
"""

import csv
from pathlib import Path
from typing import Dict, Any, List

# -------------------------------------------------
# Paths
# -------------------------------------------------

THIS_DIR = Path(__file__).resolve().parent      # scripts/
BASE_DIR = THIS_DIR.parent                      # project root

DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "outputs"

LEXICON_CSV = DATA_DIR / "liheci_lexicon.csv"
POS_FILTERED_TSV = OUT_DIR / "liheci_pos_filtered.tsv"

SUMMARY_TSV = OUT_DIR / "liheci_pos_summary.tsv"
SUMMARY_TXT = OUT_DIR / "liheci_pos_summary.txt"


# -------------------------------------------------
# Helpers
# -------------------------------------------------

def parse_bool(s: str) -> bool:
    return str(s).strip().lower() == "true"


def load_lexicon(path: Path) -> Dict[str, Dict[str, str]]:
    """Load lexicon, keep only (Lemma, A=head, B=tail, Type)."""
    meta: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf-8") as fin:
        reader = csv.DictReader(fin)
        for row in reader:
            lemma = row.get("Lemma", "").strip()
            if not lemma:
                continue
            meta[lemma] = {
                "head": row.get("A", "").strip(),
                "tail": row.get("B", "").strip(),
                "type": row.get("Type", "").strip(),
            }
    return meta


def load_pos_filtered(path: Path) -> List[Dict[str, Any]]:
    """
    Load liheci_pos_filtered.tsv and convert:
      - booleans
      - indices
      - tokens / pos_tags into lists
    """
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fin:
        reader = csv.DictReader(fin, delimiter="\t")
        for row in reader:
            r: Dict[str, Any] = {
                "case_id": int(row["case_id"]),
                "gold_stem": row["gold_stem"].strip(),
                "gold_label": parse_bool(row["gold_label"]),
                "lemma": row["lemma"].strip(),
                "type_tag": row["type_tag"].strip(),
                "shape": row["shape"].strip(),
                "is_redup": parse_bool(row["is_redup"]),
                "sentence": row["sentence"].strip(),
                "category": row["category"].strip(),
                "is_valid": parse_bool(row["is_valid"]),
                "pattern_type": row["pattern_type"].strip(),
                "reason": row["reason"].strip(),
            }

            r["tokens"] = row["tokens"].split()
            r["pos_tags"] = row["pos_tags"].split()

            head_idx_str = row["head_token_indices"].strip()
            tail_idx_str = row["tail_token_indices"].strip()

            r["head_indices"] = (
                [int(x) for x in head_idx_str.split(",") if x] if head_idx_str else []
            )
            r["tail_indices"] = (
                [int(x) for x in tail_idx_str.split(",") if x] if tail_idx_str else []
            )

            rows.append(r)
    return rows


def tokens_with_pos(tokens: List[str], tags: List[str]) -> str:
    """Return string like: 今天/NT 妈妈/NN 做/VV ..."""
    return " ".join(f"{w}/{t}" for w, t in zip(tokens, tags))


def build_head_tail_insert_desc(
    lemma: str,
    lex_meta: Dict[str, str],
    tokens: List[str],
    tags: List[str],
    head_indices: List[int],
    tail_indices: List[int],
    pattern_type: str,
) -> Dict[str, str]:
    """
    Build readable descriptions for one analysis:
      - head_desc: token+POS+index+lex_head
      - tail_desc: token+POS+index+lex_tail
      - mode_desc: "Pattern: 做……饭 (two_tokens)"
      - insert_desc: "了/AS 一/CD 顿/M 丰盛/JJ 的/DEG" or comment.
    """
    head_char = lex_meta.get("head", "")
    tail_char = lex_meta.get("tail", "")

    head_desc = ""
    tail_desc = ""
    mode_desc = ""
    insert_desc = ""

    if not head_indices and not tail_indices:
        # No explicit token indices: still show lemma-level pattern
        if head_char and tail_char:
            mode_desc = f"Pattern: {head_char}……{tail_char} ({pattern_type or 'n/a'})"
        else:
            mode_desc = f"Pattern: {lemma} ({pattern_type or 'n/a'})"
        return {
            "head_desc": head_desc,
            "tail_desc": tail_desc,
            "mode_desc": mode_desc,
            "insert_desc": insert_desc,
        }

    hi = head_indices[0] if head_indices else tail_indices[0]
    ti = tail_indices[-1] if tail_indices else head_indices[-1]

    if hi < 0 or hi >= len(tokens) or ti < 0 or ti >= len(tokens):
        # Out-of-range safety
        if head_char and tail_char:
            mode_desc = f"Pattern: {head_char}……{tail_char} ({pattern_type or 'n/a'})"
        else:
            mode_desc = f"Pattern: {lemma} ({pattern_type or 'n/a'})"
        return {
            "head_desc": head_desc,
            "tail_desc": tail_desc,
            "mode_desc": mode_desc,
            "insert_desc": insert_desc,
        }

    head_tok, head_pos = tokens[hi], tags[hi]
    tail_tok, tail_pos = tokens[ti], tags[ti]

    head_desc = f"{head_tok}/{head_pos} (token#{hi+1}, lex_head={head_char or 'N/A'})"
    tail_desc = f"{tail_tok}/{tail_pos} (token#{ti+1}, lex_tail={tail_char or 'N/A'})"

    if head_char and tail_char:
        mode_desc = f"Pattern: {head_char}……{tail_char} ({pattern_type or 'n/a'})"
    else:
        mode_desc = f"Pattern: {lemma} ({pattern_type or 'n/a'})"

    if hi < ti:
        ins_tokens = tokens[hi+1:ti]
        ins_tags = tags[hi+1:ti]
        if ins_tokens:
            insert_desc = " ".join(f"{w}/{p}" for w, p in zip(ins_tokens, ins_tags))
        else:
            insert_desc = "(no insertion tokens)"
    elif hi == ti:
        insert_desc = "(inside one token; not separated)"
    else:
        insert_desc = "(head index after tail? check data)"

    return {
        "head_desc": head_desc,
        "tail_desc": tail_desc,
        "mode_desc": mode_desc,
        "insert_desc": insert_desc,
    }


def classify_status(
    gold_stem: str,
    gold_label: bool,
    lemma: str,
    is_valid: bool,
) -> str:
    """
    TP/FP/FN/TN for THIS lemma in THIS case.
    """
    expected_pos = (lemma == gold_stem and gold_label)
    pred_pos = is_valid

    if expected_pos and pred_pos:
        return "TP (hit target lemma)"
    elif expected_pos and not pred_pos:
        return "FN (missed target lemma)"
    elif (not expected_pos) and pred_pos:
        if gold_label:
            return f"FP (spurious lemma; gold target is {gold_stem})"
        else:
            return "FP (gold label=False but lemma accepted)"
    else:
        if gold_label:
            return f"TN (lemma ignored; gold target is {gold_stem})"
        else:
            return "TN (correctly ignored in negative case)"


# -------------------------------------------------
# Main
# -------------------------------------------------

def main():
    lexicon = load_lexicon(LEXICON_CSV)
    rows = load_pos_filtered(POS_FILTERED_TSV)

    # ---------- 1) TSV summary ----------
    with SUMMARY_TSV.open("w", encoding="utf-8", newline="") as f_tsv:
        writer = csv.writer(f_tsv, delimiter="\t")
        writer.writerow([
            "case_id",
            "gold_stem",
            "gold_label",
            "lemma",
            "type_tag",
            "shape",
            "is_redup",
            "category",
            "is_valid",
            "status",
            "sentence",
            "tokens_with_pos",
            "head_desc",
            "tail_desc",
            "pattern_desc",
            "insertion_desc",
            "pattern_type",
            "reason",
        ])

        for r in rows:
            lemma = r["lemma"]
            lex_meta = lexicon.get(lemma, {"head": "", "tail": "", "type": r["type_tag"]})

            ht = build_head_tail_insert_desc(
                lemma=lemma,
                lex_meta=lex_meta,
                tokens=r["tokens"],
                tags=r["pos_tags"],
                head_indices=r["head_indices"],
                tail_indices=r["tail_indices"],
                pattern_type=r["pattern_type"],
            )

            status = classify_status(
                gold_stem=r["gold_stem"],
                gold_label=r["gold_label"],
                lemma=lemma,
                is_valid=r["is_valid"],
            )

            writer.writerow([
                r["case_id"],
                r["gold_stem"],
                str(r["gold_label"]),
                lemma,
                r["type_tag"],
                r["shape"],
                str(r["is_redup"]),
                r["category"],
                str(r["is_valid"]),
                status,
                r["sentence"],
                tokens_with_pos(r["tokens"], r["pos_tags"]),
                ht["head_desc"],
                ht["tail_desc"],
                ht["mode_desc"],
                ht["insert_desc"],
                r["pattern_type"],
                r["reason"],
            ])

    # ---------- 2) TXT human-readable ----------
    with SUMMARY_TXT.open("w", encoding="utf-8") as f_txt:
        last_case = None
        for r in rows:
            lemma = r["lemma"]
            lex_meta = lexicon.get(lemma, {"head": "", "tail": "", "type": r["type_tag"]})

            ht = build_head_tail_insert_desc(
                lemma=lemma,
                lex_meta=lex_meta,
                tokens=r["tokens"],
                tags=r["pos_tags"],
                head_indices=r["head_indices"],
                tail_indices=r["tail_indices"],
                pattern_type=r["pattern_type"],
            )

            status = classify_status(
                gold_stem=r["gold_stem"],
                gold_label=r["gold_label"],
                lemma=lemma,
                is_valid=r["is_valid"],
            )

            if last_case != r["case_id"]:
                f_txt.write("=" * 60 + "\n")
            last_case = r["case_id"]

            f_txt.write(
                f"[Case {r['case_id']}] gold_stem={r['gold_stem']} "
                f"gold_label={r['gold_label']}\n"
            )
            f_txt.write(f"Sentence : {r['sentence']}\n")
            f_txt.write(f"TokensPOS: {tokens_with_pos(r['tokens'], r['pos_tags'])}\n\n")

            f_txt.write(
                "HFST lemma: "
                f"{lemma} | type={r['type_tag']} | shape={r['shape']} | "
                f"redup={r['is_redup']} | category={r['category']} | "
                f"pattern={r['pattern_type']}\n"
            )
            f_txt.write(
                f"Our decision : is_valid={r['is_valid']} | status={status}\n"
            )
            f_txt.write(f"Head : {ht['head_desc']}\n")
            f_txt.write(f"Tail : {ht['tail_desc']}\n")
            f_txt.write(f"{ht['mode_desc']}\n")

            if ht["insert_desc"]:
                f_txt.write(f"Insertion span : {ht['insert_desc']}\n")
            else:
                f_txt.write("Insertion span : (none or inside one token)\n")

            if r["reason"]:
                f_txt.write(f"Reason : {r['reason']}\n")
            f_txt.write("\n")

    print("Written:")
    print(" -", SUMMARY_TSV)
    print(" -", SUMMARY_TXT)


if __name__ == "__main__":
    main()
