#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3: Insertion Analysis with WFST
- Annotates insertion components using HFST
- Classifies insertion types
- Detects errors (MISSING_DE, PP_POS, INVALID_PRONOUN)
- Assigns confidence scores based on tag coverage
- Validates pronoun + DE constraints from lexicon
- Validates PP position constraints from lexicon
"""

import subprocess
import re
import csv
import pandas as pd
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
HFST_LOOKUP = BASE_DIR.parent / 'hfst-3.16.2' / 'hfst' / 'bin' / 'hfst-lookup.exe'
ANNOTATOR_HFST = BASE_DIR / 'hfst_files' / 'liheci_insertion_annotator.hfst'
INPUT_TSV = BASE_DIR.parent / 'outputs' / 'liheci_hfst_outputs.tsv'
OUTPUT_TSV = BASE_DIR.parent / 'outputs' / 'liheci_insertion_analysis.tsv'
LEXICON_CSV = BASE_DIR.parent / 'data' / 'liheci_lexicon.csv'

# ============================================================
# Confidence Threshold
# ============================================================
CONFIDENCE_THRESHOLD = 0.3  # 低于此阈值的结果将被过滤掉


def load_lexicon_rules():
    """
    Load pronoun and PP rules from lexicon CSV
    Returns:
        - PRON_POSS_REQUIRED: set of lemmas where pronoun needs 的
        - PRON_POSS_PREFERRED: set of lemmas where 的 is preferred
        - PRON_OBJ_OK: set of lemmas where bare pronoun is OK
        - NO_DIRECT_NP: set of lemmas that don't allow pronoun insertion
        - NO_PP_INSERT_WORDS: set of lemmas where PP should be external
    """
    pron_poss_required = set()
    pron_poss_preferred = set()
    pron_obj_ok = set()
    no_direct_np = set()
    no_pp_insert_words = set()
    
    if not LEXICON_CSV.exists():
        print(f"Warning: Lexicon CSV not found: {LEXICON_CSV}")
        return pron_poss_required, pron_poss_preferred, pron_obj_ok, no_direct_np, no_pp_insert_words
    
    with open(LEXICON_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lemma = row.get('Lemma', '').strip()
            if not lemma or lemma.startswith('#'):
                continue
            
            pron_rule = row.get('PronounInsertion', '').strip()
            pp_rule = row.get('PPRequirement', '').strip()
            
            # Parse PronounInsertion column
            if pron_rule == 'PRON_POSS_REQUIRED':
                pron_poss_required.add(lemma)
            elif pron_rule == 'PRON_POSS_PREFERRED':
                pron_poss_preferred.add(lemma)
            elif pron_rule == 'PRON_OBJ_OK':
                pron_obj_ok.add(lemma)
            elif pron_rule == 'NO_DIRECT_NP':
                no_direct_np.add(lemma)
            
            # Parse PPRequirement column for NO_DIRECT_NP
            if 'INT:NO_DIRECT_NP' in pp_rule:
                no_pp_insert_words.add(lemma)
    
    print(f"Loaded lexicon rules:")
    print(f"  PRON_POSS_REQUIRED: {len(pron_poss_required)} lemmas")
    print(f"  PRON_POSS_PREFERRED: {len(pron_poss_preferred)} lemmas")
    print(f"  PRON_OBJ_OK: {len(pron_obj_ok)} lemmas")
    print(f"  NO_DIRECT_NP: {len(no_direct_np)} lemmas")
    print(f"  NO_PP_INSERT_WORDS: {len(no_pp_insert_words)} lemmas")
    
    return pron_poss_required, pron_poss_preferred, pron_obj_ok, no_direct_np, no_pp_insert_words


def call_hfst_annotator(sentence):
    """
    Call HFST annotator and return annotated sentence
    """
    result = subprocess.run(
        [str(HFST_LOOKUP), str(ANNOTATOR_HFST)],
        input=sentence.encode('utf-8'),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL
    )
    
    output = result.stdout.decode('utf-8').strip()
    lines = output.split('\n')
    for line in lines:
        if '\t' in line:
            parts = line.split('\t')
            if len(parts) >= 2:
                return parts[1]  # Return annotated sentence
    
    return sentence  # If annotation fails, return original


def extract_tags(annotated_text, start_marker='<HEAD>', end_marker='<TAIL>'):
    """
    Extract tags between markers from annotated text
    Returns: (insertion_text, tags_list, has_de)
    Note: has_de is used internally for validation, not output
    """
    # Extract content between <HEAD>...<TAIL>
    match = re.search(rf'{re.escape(start_marker)}(.*?){re.escape(end_marker)}', annotated_text)
    if not match:
        return '', [], False
    
    insertion = match.group(1)
    
    # Parse tags in format: char:TAG+
    tags = []
    has_de = False
    
    # Match all char:TAG+ patterns
    pattern = r'(.):([A-Z]+)\+'
    for m in re.finditer(pattern, insertion):
        char = m.group(1)
        tag = m.group(2)
        tags.append((char, tag))
        if tag == 'DE':
            has_de = True
    
    return insertion, tags, has_de


def extract_before_head_tags(annotated_text, head_marker='<HEAD>'):
    """
    Extract tags before <HEAD> marker (for detecting prepositional phrases in WHOLE forms)
    Returns recent tags before HEAD
    """
    head_pos = annotated_text.find(head_marker)
    if head_pos == -1:
        return []
    
    before_text = annotated_text[:head_pos]
    
    # Extract tags from last 50 chars (enough to detect "跟他", "和我", etc.)
    recent_text = before_text[-50:] if len(before_text) > 50 else before_text
    
    tags = []
    pattern = r'(.):([A-Z]+)\+'
    for m in re.finditer(pattern, recent_text):
        char = m.group(1)
        tag = m.group(2)
        tags.append((char, tag))
    
    return tags


def classify_insertion(tags):
    """
    Classify insertion type based on tags
    Returns: type_name
    """
    tag_set = {tag for _, tag in tags}
    
    # ASPECT + NUM + CLF
    if 'ASPECT' in tag_set and 'NUM' in tag_set and 'CLF' in tag_set:
        return 'ASPECT_QUANT'
    
    # ASPECT only
    if 'ASPECT' in tag_set:
        return 'ASPECT'
    
    # NUM + CLF
    if 'NUM' in tag_set and 'CLF' in tag_set:
        return 'QUANTIFIER'
    
    # CLF only
    if 'CLF' in tag_set:
        return 'QUANTIFIER'
    
    # PRO + DE
    if 'PRO' in tag_set and 'DE' in tag_set:
        return 'PRONOUN_DE'
    
    # PRO only
    if 'PRO' in tag_set:
        return 'PRONOUN'
    
    # MOD + DE
    if 'MOD' in tag_set and 'DE' in tag_set:
        return 'MODIFIER_DE'
    
    # MOD only
    if 'MOD' in tag_set:
        return 'MODIFIER'
    
    # RES
    if 'RES' in tag_set:
        return 'RESULTATIVE'
    
    # No recognized tags
    if not tags:
        return 'EMPTY'
    
    return 'UNKNOWN'


def check_whole_ext_pp(before_tags):
    """
    Check if WHOLE form has external prepositional phrase (PREP + PRO)
    """
    if len(before_tags) < 2:
        return False
    
    # Check if PREP is followed by PRO in recent tags
    for i in range(len(before_tags) - 1):
        if before_tags[i][1] == 'PREP' and before_tags[i+1][1] == 'PRO':
            return True
    
    return False


def format_tagged_insertion(tags):
    """
    Format tagged insertion as: char:TAG+char:TAG+...
    """
    if not tags:
        return ''
    
    return '+'.join([f'{char}:{tag}' for char, tag in tags])


def calculate_coverage(insertion_text, tags):
    """
    Calculate tag coverage ratio: tagged_chars / total_chars
    Returns confidence score between 0.0 and 1.0
    """
    # Remove tag markers from insertion_text to get clean text
    clean_text = re.sub(r':[A-Z]+\+', '', insertion_text)
    
    if len(clean_text) == 0:
        return 0.0
    
    # Count tagged characters
    tagged_count = len(tags)
    total_count = len(clean_text)
    
    return tagged_count / total_count


def main():
    print("="*60)
    print("Stage 3: Insertion Analysis with WFST")
    print("="*60)
    
    # Load lexicon rules from CSV
    print("\nLoading lexicon rules...")
    PRON_POSS_REQUIRED, PRON_POSS_PREFERRED, PRON_OBJ_OK, NO_DIRECT_NP, NO_PP_INSERT_WORDS = load_lexicon_rules()
    
    # Read Stage 2 output
    df = pd.read_csv(INPUT_TSV, sep='\t')
    print(f"\nRead {len(df)} rows")
    
    results = []
    
    for idx, row in df.iterrows():
        sent_id = row['sent_id']
        lemma = row['lemma']
        shape = row['shape']
        head = row['head']
        tail = row['tail']
        sentence = row['sentence']
        
        # Skip REDUP (no insertion analysis)
        if shape == 'REDUP':
            results.append({
                **row.to_dict(),
                'insertion': '',
                'insertion_tagged': '',
                'insertion_type': 'REDUP_SKIP',
                'detected_error': None,
                'confidence_score': 1.0
            })
            continue
        
        # Insert <HEAD> and <TAIL> markers
        head_pos = sentence.find(head)
        tail_pos = sentence.find(tail, head_pos + len(head))
        
        if head_pos == -1 or tail_pos == -1:
            print(f"Warning: Cannot locate head/tail for {lemma}")
            continue
        
        marked_sentence = (
            sentence[:head_pos + len(head)] + 
            '<HEAD>' + 
            sentence[head_pos + len(head):tail_pos] + 
            '<TAIL>' + 
            sentence[tail_pos:]
        )
        
        # Call HFST annotator
        annotated = call_hfst_annotator(marked_sentence)
        
        # Extract insertion tags
        insertion_text, tags, has_de = extract_tags(annotated)
        insertion_tagged = format_tagged_insertion(tags)
        
        # Classify insertion type and calculate confidence
        if shape == 'SPLIT':
            ins_type = classify_insertion(tags)
            
            # Calculate base confidence from tag coverage
            confidence = calculate_coverage(insertion_text, tags)
            
            # Get tag set for checking
            tag_set = {tag for _, tag in tags}
            has_pronoun = 'PRO' in tag_set
            has_prep = 'PREP' in tag_set
            
            detected_error = None
            
            # ============================================================
            # Rule 1: Pronoun + DE Validation (Complete Rules)
            # ============================================================
            if has_pronoun:
                # 1a. PRON_POSS_REQUIRED: 代词后必须有"的"
                if lemma in PRON_POSS_REQUIRED:
                    if not has_de:
                        detected_error = 'MISSING_REQUIRED_DE'
                        confidence = 0.0  # Strict reject
                
                # 1b. PRON_POSS_PREFERRED: 代词后建议有"的"
                elif lemma in PRON_POSS_PREFERRED:
                    if not has_de:
                        detected_error = 'MISSING_PREFERRED_DE'
                        confidence *= 0.7  # Penalty but not reject
                
                # 1c. PRON_OBJ_OK: 代词可做直接宾语，不需要"的"
                elif lemma in PRON_OBJ_OK:
                    pass  # No penalty, direct object is OK
                
                # 1d. NO_DIRECT_NP: 不允许代词直接插入
                elif lemma in NO_DIRECT_NP:
                    detected_error = 'INVALID_PRONOUN_INSERTION'
                    confidence = 0.0  # Strict reject - should use external PP
            
            # ============================================================
            # Rule 2: PP Position Validation
            # ============================================================
            # PP in insertion is invalid for certain words (should be external)
            if has_prep and lemma in NO_PP_INSERT_WORDS:
                detected_error = 'PP_IN_INSERTION'
                confidence = 0.0  # Strict reject (changed from *= 0.2)
            
            # Note: REQUIRE_DE_WORDS (PRON_POSS_REQUIRED) only applies when
            # a pronoun is present (handled in Rule 1a above).
            # Cases like "开了一个玩笑" (quantifier without pronoun) are valid.
        
        elif shape == 'WHOLE':
            # Check for external prepositional phrase
            before_tags = extract_before_head_tags(annotated)
            if check_whole_ext_pp(before_tags):
                ins_type = 'EXT_PP'
                confidence = 0.8
            else:
                ins_type = 'EMPTY'
                confidence = 0.5
            
            detected_error = None
        
        else:
            ins_type = 'UNKNOWN'
            confidence = 0.5
            detected_error = None
        
        results.append({
            **row.to_dict(),
            'insertion': insertion_text.replace('<HEAD>', '').replace('<TAIL>', '').replace('+', '').replace(':', ''),
            'insertion_tagged': insertion_tagged,
            'insertion_type': ins_type,
            'detected_error': detected_error,
            'confidence_score': confidence
        })
        
        if idx < 10:  # Print first 10 examples
            print(f"\n[{sent_id}] {lemma} ({shape})")
            print(f"  Insertion: {insertion_text}")
            print(f"  Tagged: {insertion_tagged}")
            print(f"  Type: {ins_type}")
            print(f"  Detected Error: {detected_error}")
            print(f"  Confidence: {confidence:.2f}")
    
    # Save results
    result_df = pd.DataFrame(results)
    
    # Filter by confidence threshold
    original_count = len(result_df)
    result_df = result_df[result_df['confidence_score'] >= CONFIDENCE_THRESHOLD]
    filtered_count = original_count - len(result_df)
    
    result_df.to_csv(OUTPUT_TSV, sep='\t', index=False)
    print(f"\n✓ Results saved to: {OUTPUT_TSV}")
    print(f"  Original: {original_count} rows")
    print(f"  Filtered (confidence < {CONFIDENCE_THRESHOLD}): {filtered_count} rows")
    print(f"  Final: {len(result_df)} rows")
    
    # Statistics
    print(f"\nInsertion type distribution:")
    print(result_df['insertion_type'].value_counts())
    
    print(f"\nError type distribution:")
    print(result_df['detected_error'].value_counts())
    
    print(f"\nAverage confidence: {result_df['confidence_score'].mean():.2f}")


if __name__ == '__main__':
    main()
