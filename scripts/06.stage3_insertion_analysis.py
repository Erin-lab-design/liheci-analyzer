#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stage 3: Insertion Analysis with WFST
- Annotates insertion components using HFST
- Classifies insertion types
- Detects errors (MISSING_DE, PP_POS)
- Assigns confidence scores based on tag coverage
"""

import subprocess
import re
import pandas as pd
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
HFST_LOOKUP = BASE_DIR.parent / 'hfst-3.16.2' / 'hfst' / 'bin' / 'hfst-lookup.exe'
ANNOTATOR_HFST = BASE_DIR / 'hfst_files' / 'liheci_insertion_annotator.hfst'
INPUT_TSV = BASE_DIR.parent / 'outputs' / 'liheci_hfst_outputs.tsv'
OUTPUT_TSV = BASE_DIR.parent / 'outputs' / 'liheci_insertion_analysis.tsv'

# Words that require "的" (de) in insertion (otherwise MISSING_DE error)
REQUIRE_DE_WORDS = {'捣乱', '丢脸', '造反', '革命'}

# Words that cannot have PP in insertion (prepositional phrase must be external)
NO_PP_INSERT_WORDS = {'道歉', '道谢', '拜年', '见面', '吵架', '打架', '打仗', '开玩笑'}


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
                'has_de': False,
                'error_type': None,
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
            
            # Check MISSING_DE error
            error_type = None
            if lemma in REQUIRE_DE_WORDS and not has_de:
                error_type = 'MISSING_DE'
                confidence *= 0.3  # Lower confidence
            
            # Check PP_POS error
            if lemma in NO_PP_INSERT_WORDS:
                # Check if PREP exists in insertion
                tag_set = {tag for _, tag in tags}
                if 'PREP' in tag_set:
                    error_type = 'PP_POS'
                    confidence *= 0.2
        
        elif shape == 'WHOLE':
            # Check for external prepositional phrase
            before_tags = extract_before_head_tags(annotated)
            if check_whole_ext_pp(before_tags):
                ins_type = 'EXT_PP'
                confidence = 0.8
            else:
                ins_type = 'EMPTY'
                confidence = 0.5
            
            error_type = None
        
        else:
            ins_type = 'UNKNOWN'
            confidence = 0.5
            error_type = None
        
        results.append({
            **row.to_dict(),
            'insertion': insertion_text.replace('<HEAD>', '').replace('<TAIL>', '').replace('+', '').replace(':', ''),
            'insertion_tagged': insertion_tagged,
            'insertion_type': ins_type,
            'has_de': has_de,
            'error_type': error_type,
            'confidence_score': confidence
        })
        
        if idx < 10:  # Print first 10 examples
            print(f"\n[{sent_id}] {lemma} ({shape})")
            print(f"  Insertion: {insertion_text}")
            print(f"  Tagged: {insertion_tagged}")
            print(f"  Type: {ins_type}")
            print(f"  Error: {error_type}")
            print(f"  Confidence: {confidence:.2f}")
    
    # Save results
    result_df = pd.DataFrame(results)
    result_df.to_csv(OUTPUT_TSV, sep='\t', index=False)
    print(f"\n✓ Results saved to: {OUTPUT_TSV}")
    
    # Statistics
    print(f"\nInsertion type distribution:")
    print(result_df['insertion_type'].value_counts())
    
    print(f"\nError type distribution:")
    print(result_df['error_type'].value_counts())
    
    print(f"\nAverage confidence: {result_df['confidence_score'].mean():.2f}")


if __name__ == '__main__':
    main()
