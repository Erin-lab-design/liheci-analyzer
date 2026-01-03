 #!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 4: POS-based Validation using HanLP

Reads:
  - outputs/liheci_insertion_analysis.tsv (from Stage 3)
  - data/liheci_lexicon.csv

Does:
  - For each row, use HanLP to tokenize and POS-tag the sentence
  - Find the HEAD and TAIL tokens in HanLP output
  - Validate HEAD/TAIL POS against type-specific rules:
      * Verb-Object: HEAD=VV (97%), TAIL=NN (77%) or VV (20% for WHOLE/REDUP)
      * Modifier-Head: HEAD∈{VA,VV,AD,NN}, TAIL∈{VA,VV,NN}
      * PseudoV-O: HEAD=VV, TAIL=NN
      * SimplexWord: HEAD=VV, TAIL∈{NN,VV}
  - Reject rows where TAIL POS ∈ {AD, P, CS, CC} (functional words)

Outputs:
  - outputs/liheci_pos_validated.tsv (filtered results)
  - outputs/liheci_pos_rejected.tsv (rejected rows with reasons)

Based on POS_ANALYSIS.md rules.
"""

import csv
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

import hanlp

# =========================
# Paths & Logging
# =========================

THIS_DIR = Path(__file__).resolve().parent
BASE_DIR = THIS_DIR.parent

DATA_DIR = BASE_DIR / "data"
OUT_DIR = BASE_DIR / "outputs"
LOG_DIR = OUT_DIR / "logs"

INPUT_TSV = OUT_DIR / "liheci_insertion_analysis.tsv"
LEXICON_CSV = DATA_DIR / "liheci_lexicon.csv"
OUTPUT_TSV = OUT_DIR / "liheci_pos_validated.tsv"
REJECTED_TSV = OUT_DIR / "liheci_pos_rejected.tsv"
LOG_FILE = LOG_DIR / "stage4_pos_validation.log"

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
# POS Validation Rules (from POS_ANALYSIS.md)
# =========================

# POS tag sets
VERB_TAGS = {"VV", "VC", "VE"}          # 动词
NOUN_TAGS = {"NN", "NR", "NT"}          # 名词
ADJ_TAGS = {"VA", "JJ"}                 # 形容词/形容词性动词
FUNC_TAGS = {"AD", "P", "CS", "CC"}     # 功能词 (副词、介词、连词) - TAIL不应有这些

# HEAD allowed POS by type (STRICT rules)
# Note: For Verb-Object, HEAD should be VV (97%). The 2.1% NN in data are tagging errors.
# We should NOT accept NN as HEAD for Verb-Object - that would allow false positives like "丐帮"
HEAD_ALLOWED_POS = {
    "Verb-Object": VERB_TAGS,                  # VV only (strict) - reject NN as HEAD
    "Pseudo V-O": VERB_TAGS,                   # VV only
    "Modifier-Head": VERB_TAGS | ADJ_TAGS | {"AD"},  # VV, VA, AD (not NN as HEAD)
    "SimplexWord": VERB_TAGS,                  # VV only
}

# TAIL allowed POS by type
# Note: VV is allowed for WHOLE/REDUP forms
TAIL_ALLOWED_POS = {
    "Verb-Object": NOUN_TAGS | VERB_TAGS | {"M", "VA"},  # NN (77%), VV (20%), M, VA
    "PseudoV-O": NOUN_TAGS | VERB_TAGS,       # NN (83%)
    "Modifier-Head": NOUN_TAGS | ADJ_TAGS | VERB_TAGS,  # NN, VA, VV
    "SimplexWord": NOUN_TAGS | VERB_TAGS,     # NN (67%), VV (33%)
}

# TAIL blacklist - these POS should NEVER be TAIL (functional words)
TAIL_BLACKLIST = {"AD", "P", "CS", "CC", "DT", "DEG", "DEC", "AS", "SP"}

# =========================
# Load Lexicon
# =========================

def load_lexicon(path: Path) -> Dict[str, Dict[str, str]]:
    """Load lexicon to get head/tail characters for each lemma"""
    lemma_meta: Dict[str, Dict[str, str]] = {}
    with path.open("r", encoding="utf-8") as fin:
        reader = csv.DictReader(fin)
        for row in reader:
            lemma = (row.get("Lemma") or "").strip()
            if not lemma:
                continue
            head = (row.get("A") or "").strip()
            tail = (row.get("B") or "").strip()
            ltype = (row.get("Type") or "").strip()
            lemma_meta[lemma] = {
                "head": head,
                "tail": tail,
                "type": ltype,
            }
    logger.info("Loaded %d lemmas from lexicon: %s", len(lemma_meta), path)
    return lemma_meta

# =========================
# HanLP Wrapper with Cache
# =========================

class HanLPWrapper:
    def __init__(self):
        logger.info("Loading HanLP models...")
        self.tokenizer = hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH)
        self.tagger = hanlp.load(hanlp.pretrained.pos.CTB9_POS_ELECTRA_SMALL)
        logger.info("HanLP models ready.")
        self.cache: Dict[str, Tuple[List[str], List[str]]] = {}

    def tokenize_pos(self, sentence: str) -> Tuple[List[str], List[str]]:
        if sentence in self.cache:
            return self.cache[sentence]
        tokens = self.tokenizer(sentence)
        tags = self.tagger(tokens)
        self.cache[sentence] = (tokens, tags)
        return tokens, tags

# =========================
# Find HEAD/TAIL in HanLP tokens
# =========================

def find_char_in_tokens(
    char: str, 
    tokens: List[str], 
    tags: List[str],
    start_from: int = 0
) -> Optional[Tuple[int, str]]:
    """
    Find which token contains the character.
    Returns (token_index, pos_tag) or None if not found.
    """
    for i in range(start_from, len(tokens)):
        if char in tokens[i]:
            return (i, tags[i])
    return None

def find_head_tail_pos(
    head_char: str,
    tail_char: str,
    tokens: List[str],
    tags: List[str]
) -> Tuple[Optional[Tuple[int, str]], Optional[Tuple[int, str]], str]:
    """
    Find HEAD and TAIL positions and their POS tags.
    Returns: (head_info, tail_info, pattern)
    - head_info: (token_idx, pos_tag) or None
    - tail_info: (token_idx, pos_tag) or None  
    - pattern: "same_token" | "separate_tokens" | "not_found"
    """
    head_info = find_char_in_tokens(head_char, tokens, tags)
    if head_info is None:
        return None, None, "head_not_found"
    
    head_idx, head_pos = head_info
    
    # Check if tail is in the same token
    if tail_char in tokens[head_idx]:
        # Same token - check order within token
        token = tokens[head_idx]
        head_pos_in_token = token.find(head_char)
        tail_pos_in_token = token.rfind(tail_char)
        if head_pos_in_token <= tail_pos_in_token:
            return head_info, (head_idx, tags[head_idx]), "same_token"
    
    # Look for tail after head
    tail_info = find_char_in_tokens(tail_char, tokens, tags, start_from=head_idx)
    if tail_info is None:
        return head_info, None, "tail_not_found"
    
    tail_idx, tail_pos = tail_info
    if tail_idx == head_idx:
        return head_info, tail_info, "same_token"
    else:
        return head_info, tail_info, "separate_tokens"

# =========================
# POS Validation Logic
# =========================

def validate_pos(
    type_tag: str,
    shape: str,
    head_pos: Optional[str],
    tail_pos: Optional[str]
) -> Tuple[bool, str]:
    """
    Validate HEAD/TAIL POS against type-specific rules.
    Returns: (is_valid, reason)
    """
    # If we couldn't find POS, we can't validate - pass with warning
    if head_pos is None or tail_pos is None:
        return True, "pos_not_determined"
    
    # Rule 1: TAIL blacklist check (most important)
    # These are functional words that should NEVER be TAIL
    if tail_pos in TAIL_BLACKLIST:
        return False, f"tail_pos_blacklisted:{tail_pos}"
    
    # Rule 2: Type-specific HEAD validation (STRICT - reject if mismatch)
    head_allowed = HEAD_ALLOWED_POS.get(type_tag)
    if head_allowed and head_pos not in head_allowed:
        # HEAD POS mismatch is a hard reject - likely false positive
        # e.g., "丐帮" with 帮/NN is NOT a valid Verb-Object liheci
        return False, f"head_pos_invalid:{head_pos}"
    
    # Rule 3: Type-specific TAIL validation
    tail_allowed = TAIL_ALLOWED_POS.get(type_tag)
    if tail_allowed and tail_pos not in tail_allowed:
        # For WHOLE/REDUP, VV is more acceptable
        if shape in ("WHOLE", "REDUP") and tail_pos in VERB_TAGS:
            pass  # OK for WHOLE/REDUP
        else:
            return False, f"tail_pos_invalid:{tail_pos}"
    
    # Rule 4: Special case - Modifier-Head should have VA marker
    if type_tag == "Modifier-Head":
        # VA in either HEAD or TAIL is a good sign
        if head_pos not in ADJ_TAGS and tail_pos not in ADJ_TAGS:
            # Not necessarily wrong, just less confident
            pass
    
    return True, "pos_valid"

# =========================
# Main Processing
# =========================

def main():
    logger.info("=== Stage 4: POS Validation starts ===")
    
    # Load lexicon
    lemma_meta = load_lexicon(LEXICON_CSV)
    
    # Initialize HanLP
    hanlp_wrapper = HanLPWrapper()
    
    # Read input TSV
    input_rows = []
    with open(INPUT_TSV, "r", encoding="utf-8") as fin:
        reader = csv.DictReader(fin, delimiter="\t")
        fieldnames = reader.fieldnames
        for row in reader:
            input_rows.append(row)
    
    logger.info("Loaded %d rows from %s", len(input_rows), INPUT_TSV)
    
    # Process each row
    validated_rows = []
    rejected_rows = []
    
    stats = {
        "total": 0,
        "validated": 0,
        "rejected": 0,
        "rejection_reasons": {}
    }
    
    for row in input_rows:
        stats["total"] += 1
        
        sent_id = row.get("sent_id", "")
        sentence = row.get("sentence", "")
        lemma = row.get("lemma", "")
        type_tag = row.get("type_tag", "")
        shape = row.get("shape", "")
        head_char = row.get("head", "")
        tail_char = row.get("tail", "")
        
        # Get confidence score from Stage 3
        try:
            confidence_score = float(row.get("confidence_score", 0))
        except (ValueError, TypeError):
            confidence_score = 0.0
        
        # Get HanLP tokenization and POS
        tokens, tags = hanlp_wrapper.tokenize_pos(sentence)
        
        # Find HEAD and TAIL positions
        head_info, tail_info, pattern = find_head_tail_pos(
            head_char, tail_char, tokens, tags
        )
        
        head_pos = head_info[1] if head_info else None
        tail_pos = tail_info[1] if tail_info else None
        head_idx = head_info[0] if head_info else None
        tail_idx = tail_info[0] if tail_info else None
        
        # Validate POS
        is_valid, reason = validate_pos(type_tag, shape, head_pos, tail_pos)
        
        # Override: if confidence_score > 0.55, accept even if POS mismatch
        if not is_valid and confidence_score > 0.55:
            is_valid = True
            reason = f"pos_override_by_confidence:{confidence_score:.2f};original:{reason}"
        
        # Add POS info to row - combine tokens and tags for readability
        tokens_with_pos = " ".join(f"{tok}/{tag}" for tok, tag in zip(tokens, tags))
        row["tokens_pos"] = tokens_with_pos
        row["head_token_idx"] = str(head_idx) if head_idx is not None else ""
        row["tail_token_idx"] = str(tail_idx) if tail_idx is not None else ""
        row["head_pos"] = head_pos or ""
        row["tail_pos"] = tail_pos or ""
        row["pos_pattern"] = pattern
        row["pos_validation"] = reason
        
        if is_valid:
            validated_rows.append(row)
            stats["validated"] += 1
        else:
            rejected_rows.append(row)
            stats["rejected"] += 1
            # Track rejection reasons
            base_reason = reason.split(":")[0] if ":" in reason else reason
            stats["rejection_reasons"][base_reason] = stats["rejection_reasons"].get(base_reason, 0) + 1
    
    # Prepare output fieldnames
    output_fieldnames = list(fieldnames) + [
        "tokens_pos", "head_token_idx", "tail_token_idx",
        "head_pos", "tail_pos", "pos_pattern", "pos_validation"
    ]
    
    # Write validated rows
    with open(OUTPUT_TSV, "w", encoding="utf-8", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=output_fieldnames, delimiter="\t")
        writer.writeheader()
        for row in validated_rows:
            writer.writerow(row)
    
    # Write rejected rows
    with open(REJECTED_TSV, "w", encoding="utf-8", newline="") as fout:
        writer = csv.DictWriter(fout, fieldnames=output_fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rejected_rows:
            writer.writerow(row)
    
    # Log summary
    logger.info("=== Stage 4: POS Validation complete ===")
    logger.info("Total rows processed: %d", stats["total"])
    logger.info("Validated (passed):   %d", stats["validated"])
    logger.info("Rejected (failed):    %d", stats["rejected"])
    logger.info("")
    logger.info("Rejection reasons breakdown:")
    for reason, count in sorted(stats["rejection_reasons"].items(), key=lambda x: -x[1]):
        logger.info("  %s: %d", reason, count)
    logger.info("")
    logger.info("Output files:")
    logger.info("  Validated: %s", OUTPUT_TSV)
    logger.info("  Rejected:  %s", REJECTED_TSV)


if __name__ == "__main__":
    main()
