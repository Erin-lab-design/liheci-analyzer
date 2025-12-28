#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Optimized version: limit (AnyChar)* to bounded repetition to avoid state explosion
"""

import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple

INPUT_CSV = "data/liheci_lexicon.csv"
OUTPUT_XFST = "liheci_recognizer.xfst"

EMIT_REASON_TAGS = True

def map_type_tag(type_str: str) -> str:
    t = (type_str or "").strip()
    return t.replace(" ", "") if t else "UnknownType"

def chars_with_space(s: str) -> str:
    s = (s or "").strip()
    return " ".join(list(s)) if s else ""

def xfst_seq(s: str) -> str:
    return chars_with_space(s)

def xfst_union_of_strings(items: List[str]) -> str:
    seqs = [xfst_seq(x) for x in items if (x or "").strip()]
    seqs = [x for x in seqs if x]
    if not seqs:
        return "[]"
    if len(seqs) == 1:
        return seqs[0]
    return "(" + " | ".join(seqs) + ")"

def parse_redup_pattern(val: str) -> Tuple[bool, bool]:
    v = (val or "").strip().upper()
    if not v:
        return (False, False)
    has_aab = "AAB" in v
    has_axab = "A_XAB" in v or "AXAB" in v
    return (has_aab, has_axab)

_EXT_PP_RE = re.compile(r"EXT:([A-Z_]+)\s*\(([^)]+)\)", re.IGNORECASE)

def parse_ext_pp(pp_req: str) -> List[Tuple[str, List[str]]]:
    s = (pp_req or "").strip()
    out: List[Tuple[str, List[str]]] = []
    for m in _EXT_PP_RE.finditer(s):
        pp_name = m.group(1).strip().upper()
        raw = m.group(2).strip()
        items = [x.strip() for x in raw.split("|") if x.strip()]
        if items:
            out.append((pp_name, items))
    return out

def emit_redup_transducers(lemma_id: int, chars: List[str], has_redup: bool):
    """
    Emit L###Redup transducer definition if has_redup is True.
    """
    lines = []
    if has_redup:
        # Redup pattern with limited AnyChar repetitions
        lines.append(f"define {lemma_id}RedupPat (AnyChar{{0,20}}) {lemma_id}RedupCore (AnyChar{{0,20}});")
        lines.append(f'define {lemma_id}Redup "{lemma}+Lemma+{typ}+REDUP" : {lemma_id}RedupPat;')
    else:
        lines.append(f"define {lemma_id}RedupCore [];")
        lines.append(f"define {lemma_id}RedupPat (AnyChar{{0,20}}) {lemma_id}RedupCore (AnyChar{{0,20}});")
    return lines

def emit_whole_transducers(lemma_id: int, chars: List[str], lemma: str, typ: str):
    """
    Emit L###Whole transducer definition.
    """
    lines = []
    # Whole pattern with limited AnyChar repetitions
    lines.append(f"define {lemma_id}WholePat (AnyChar{{0,20}}) {lemma_id}WholeCore (AnyChar{{0,20}});")
    return lines

def emit_split_transducers(
    lemma_id: int,
    chars: List[str],
    lemma: str,
    typ: str,
    trans: bool,
    pron_ins: bool,
    pp_req: bool,
):
    """
    Emit L###Split & L###SplitHint transducer definitions.
    """
    lines = []
    # Split pattern with limited AnyChar repetitions
    lines.append(f"define {lemma_id}SplitPat (AnyChar{{0,20}}) {lemma_id}SplitUnionCore (AnyChar{{0,20}});")
    
    # Define the main Split transducer
    lines.append(f'define {lemma_id}Split "{lemma}+Lemma+{typ}+SPLIT" : {lemma_id}SplitOnly;')
    
    # Define the SplitHint transducer with limited AnyChar repetitions
    lines.append(
        f'define {lemma_id}SplitHint "{lemma}+Lemma+{typ}+SPLIT+HINT" : '
        f"((AnyChar{{0,20}}) {lemma_id}SplitHintCore (AnyChar{{0,20}}));"
    )
    return lines

def main():
    input_path = Path(INPUT_CSV)
    if not input_path.exists():
        raise SystemExit(f"ERROR: cannot find {INPUT_CSV}")

    rows: List[Dict[str, str]] = []
    with input_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lemma = (row.get("Lemma") or "").strip()
            head = (row.get("A") or "").strip()
            tail = (row.get("B") or "").strip()
            if not lemma or not head or not tail:
                continue
            rows.append(row)

    lines: List[str] = []

    lines.append("! Auto-generated: optimized with bounded AnyChar repetition")
    lines.append("! Sentence-level Liheci WHOLE / SPLIT / REDUP recognizer")
    lines.append("")

    lines.append("! =======================")
    lines.append("! Global symbol classes")
    lines.append("! =======================")

    punct_syms = ["，", "。", "、", "！", "？", "：", "；", ",", ".", "!", "?", "…"]
    punct_union = " | ".join([f'"{p}"' for p in punct_syms])
    lines.append(f"define Punct   ({punct_union});")

    lines.append("define AnyChar ?;")
    lines.append("define LegalIns (AnyChar - Punct);")
    lines.append("")

    lines.append("define RedupMid (一 | 了);")
    lines.append("")

    lines.append("! Pronouns / possessive (char-level safe)")
    pronouns = [
        "我", "你", "他", "她", "它", "咱",
        "我们", "你们", "他们", "她们", "它们", "咱们",
        "大家", "人家", "谁", "自己",
    ]
    pron_union = xfst_union_of_strings(pronouns)
    lines.append(f"define Pronoun {pron_union};")
    lines.append("define PossMark 的;")
    lines.append("define PronPoss (Pronoun PossMark);")
    lines.append("")

    lines.append("! -----------------------")
    lines.append("! Insert hints")
    lines.append("! -----------------------")

    lines.append("define Aspect   (了 | 过 | 着);")
    lines.append("define NegPot   (不 了);")
    numerals = ["一", "二", "两", "三", "四", "五", "六", "七", "八", "九", "十", "几", "百", "半",
                "0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    lines.append(f"define Numeral  ({xfst_union_of_strings(numerals)});")
    demos = ["这", "那"]
    lines.append(f"define Demo     ({xfst_union_of_strings(demos)});")
    cls = ["个", "次", "回", "遍", "场", "顿", "口", "句", "声", "趟", "阵", "通", "番", "把",
           "根", "瓶", "条", "只", "支", "本", "辆", "杯", "碗", "件", "双", "张", "种", "块",
           "匹", "头", "份", "班", "手", "针", "斤", "首", "节"]
    lines.append(f"define CL ({xfst_union_of_strings(cls)});")
    lines.append("define NumCL ( ((Numeral)?) CL | Demo CL | Demo ((Numeral)?) CL );")
    time_units = ["年", "月", "天", "小时", "分钟", "会儿"]
    lines.append(f"define TimeUnit2 ({xfst_union_of_strings(time_units)});")
    lines.append("define NumTime ( Numeral ((个)?) TimeUnit2 | 半 个 月 | 半 天 | 一 整 天 | 一 辈 子 );")
    rescomp = ["完", "好", "住", "开", "掉", "成", "到", "来", "去"]
    lines.append(f"define ResultComp ({xfst_union_of_strings(rescomp)});")
    degree = ["下", "点"]
    lines.append(f"define Degree ({xfst_union_of_strings(degree)});")
    lines.append("define DeMark 的;")
    lines.append("define InsertHintCore (Aspect | NegPot | NumCL | NumTime | PronPoss | ResultComp | Degree | DeMark);")
    lines.append("")

    all_transducer_names: List[str] = []

    # OPTIMIZATION: Use bounded repetition instead of unbounded (AnyChar)*
    # Change (AnyChar)* to (AnyChar{0,20})* to limit state explosion
    bounded_anychar = "(AnyChar{0,20})*"

    for idx, row in enumerate(rows, start=1):
        lemma = (row.get("Lemma") or "").strip()
        head = (row.get("A") or "").strip()
        tail = (row.get("B") or "").strip()
        type_str = (row.get("Type") or "").strip()

        redup_pat_raw = (row.get("RedupPattern") or "").strip()
        transitivity = (row.get("Transitivity") or "").strip()
        pron_ins = (row.get("PronounInsertion") or "").strip().upper()
        pp_req = (row.get("PPRequirement") or "").strip()

        type_tag = map_type_tag(type_str)
        head_chars = chars_with_space(head)
        tail_chars = chars_with_space(tail)
        if not head_chars or not tail_chars:
            continue

        base = f"L{idx:03d}"

        whole_upper = f"{lemma}+Lemma+{type_tag}+WHOLE"
        split_upper = f"{lemma}+Lemma+{type_tag}+SPLIT"
        redup_upper = f"{lemma}+Lemma+{type_tag}+SPLIT+REDUP"

        lines.append(f"! === {lemma}  (Type={type_str}, Trans={transitivity}, PronIns={pron_ins}, PPReq={pp_req}) ===")

        whole_core = f"{base}WholeCore"
        split_hint_core = f"{base}SplitHintCore"
        split_pron_obj_core = f"{base}SplitPronObjCore"
        split_pron_poss_core = f"{base}SplitPronPossCore"
        split_union_core = f"{base}SplitUnionCore"

        lines.append(f"define {whole_core} {head_chars} {tail_chars};")
        lines.append(f"define {split_hint_core} {head_chars} (LegalIns)* InsertHintCore (LegalIns)* {tail_chars};")

        emit_pron_obj = pron_ins in {"PRON_OBJ_OK", "PRON_POSS_PREFERRED", "PRON_POSS_REQUIRED"} or "PRON_OBJ_OK" in pron_ins
        emit_pron_poss = pron_ins in {"PRON_POSS_PREFERRED", "PRON_POSS_REQUIRED"} or "PRON_POSS" in pron_ins

        if emit_pron_obj:
            lines.append(f"define {split_pron_obj_core} {head_chars} Pronoun (LegalIns)* {tail_chars};")
        else:
            lines.append(f"define {split_pron_obj_core} [];")

        if emit_pron_poss:
            lines.append(f"define {split_pron_poss_core} {head_chars} Pronoun PossMark (LegalIns)* {tail_chars};")
        else:
            lines.append(f"define {split_pron_poss_core} [];")

        lines.append(f"define {split_union_core} ({split_hint_core} | {split_pron_obj_core} | {split_pron_poss_core});")

        has_aab, has_axab = parse_redup_pattern(redup_pat_raw)
        redup_core = f"{base}RedupCore"
        if has_aab or has_axab:
            parts = []
            if has_aab:
                parts.append(f"{head_chars} {head_chars} {tail_chars}")
            if has_axab:
                parts.append(f"{head_chars} RedupMid {head_chars} {tail_chars}")
            lines.append(f"define {redup_core} (" + " | ".join(parts) + ");")
        else:
            lines.append(f"define {redup_core} [];")

        whole_pat = f"{base}WholePat"
        split_pat = f"{base}SplitPat"
        redup_pat_name = f"{base}RedupPat"

        # OPTIMIZATION: Use bounded_anychar instead of (AnyChar)*
        lines.append(f"define {redup_pat_name} {bounded_anychar} {redup_core} {bounded_anychar};")
        lines.append(f"define {whole_pat} {bounded_anychar} {whole_core} {bounded_anychar};")
        lines.append(f"define {split_pat} {bounded_anychar} {split_union_core} {bounded_anychar};")

        whole_only = f"{base}WholeOnly"
        split_only = f"{base}SplitOnly"
        if has_aab or has_axab:
            lines.append(f"define {whole_only} ({whole_pat} - {redup_pat_name});")
            lines.append(f"define {split_only} ({split_pat} - {redup_pat_name});")
        else:
            lines.append(f"define {whole_only} {whole_pat};")
            lines.append(f"define {split_only} {split_pat};")

        tr_names_for_this: List[str] = []

        whole_tr = f"{base}Whole"
        split_tr = f"{base}Split"
        lines.append(f'define {whole_tr} "{whole_upper}" : {whole_only};')
        lines.append(f'define {split_tr} "{split_upper}" : {split_only};')
        tr_names_for_this.extend([whole_tr, split_tr])

        if has_aab or has_axab:
            redup_tr = f"{base}Redup"
            lines.append(f'define {redup_tr} "{redup_upper}" : {redup_pat_name};')
            tr_names_for_this.append(redup_tr)

        if EMIT_REASON_TAGS:
            hint_tr = f"{base}SplitHint"
            lines.append(f'define {hint_tr} "{lemma}+Lemma+{type_tag}+SPLIT+HINT" : ({bounded_anychar} {split_hint_core} {bounded_anychar});')
            tr_names_for_this.append(hint_tr)

            if emit_pron_obj:
                pronobj_tr = f"{base}SplitPronObj"
                lines.append(f'define {pronobj_tr} "{lemma}+Lemma+{type_tag}+SPLIT+PRONOBJ" : ({bounded_anychar} {split_pron_obj_core} {bounded_anychar});')
                tr_names_for_this.append(pronobj_tr)

            if emit_pron_poss:
                pronposs_tr = f"{base}SplitPronPoss"
                lines.append(f'define {pronposs_tr} "{lemma}+Lemma+{type_tag}+SPLIT+PRONPOSS" : ({bounded_anychar} {split_pron_poss_core} {bounded_anychar});')
                tr_names_for_this.append(pronposs_tr)

            ext_specs = parse_ext_pp(pp_req)
            for k, (pp_name, preps) in enumerate(ext_specs, start=1):
                prep_set_name = f"{base}ExtPrep{k}"
                ext_pat = f"{base}ExtPat{k}"
                norm = pp_name.upper().replace("_PP", "").replace("PP", "")
                prep_union = xfst_union_of_strings(preps)
                lines.append(f"define {prep_set_name} {prep_union};")
                lines.append(f"define {ext_pat} {bounded_anychar} {prep_set_name} LegalIns (LegalIns)* ({whole_core} | {split_union_core}) {bounded_anychar};")
                ext_tr = f"{base}Ext{norm}"
                lines.append(f'define {ext_tr} "{lemma}+Lemma+{type_tag}+EXT+{norm}" : {ext_pat};')
                tr_names_for_this.append(ext_tr)

        lines.append("")
        all_transducer_names.extend(tr_names_for_this)

    # Union with grouping
    lines.append("! =======================")
    lines.append("! Union all lemma transducers (grouped to avoid state explosion)")
    lines.append("! =======================")
    
    chunk_size = 30
    groups = []
    
    if all_transducer_names:
        for i in range(0, len(all_transducer_names), chunk_size):
            chunk = all_transducer_names[i:i+chunk_size]
            group_name = f"group{i//chunk_size + 1}"
            lines.append(f"define {group_name} " + " | ".join(chunk) + " ;")
            groups.append(group_name)
    
    if groups:
        lines.append("regex " + " | ".join(groups) + " ;")
    else:
        lines.append("regex [] ;")
    
    lines.append("")
    lines.append("! Stack top is generator: Upper=tags, Lower=sentences")
    lines.append("save stack liheci_split.generator.hfst")
    lines.append("")
    lines.append("invert net")
    lines.append("save stack liheci_split.analyser.hfst")
    lines.append("")
    lines.append("quit")
    lines.append("")

    Path(OUTPUT_XFST).write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] generated {OUTPUT_XFST} with {len(rows)} lemmas")
    print(f"[INFO] Using bounded (AnyChar{{0,20}})* instead of (AnyChar)* to reduce state explosion")
    print(f"[INFO] Using {len(groups)} groups of ~{chunk_size} transducers each")

if __name__ == "__main__":
    main()
