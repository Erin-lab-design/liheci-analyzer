#!/usr/bin/env python3
"""
Generate XFST script for recognizing valid reduplication patterns.

This script generates an XFST file that ONLY recognizes lemmas with RedupPattern='AAB'.
Used in Stage 2 to validate reduplication detected in Stage 1.

Strategy:
- Only include lemmas with RedupPattern='AAB' in CSV
- Generate REDUP transducers for these lemmas only
- Patterns: H H T, H 一 H T, H 了 H T
"""

import csv
import subprocess
from pathlib import Path


def chars_with_space(s: str) -> str:
    """Return string with spaces between each character for XFST."""
    s = (s or "").strip()
    if not s:
        return ""
    return " ".join(list(s))


def read_csv_lexicon(csv_path):
    """
    Read lexicon CSV and return only lemmas with AAB reduplication pattern.
    
    Returns:
        list of dict: Each dict contains lexicon entry fields
    """
    lemmas = []
    
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lemma = row.get('Lemma', '')
            if lemma:
                lemma = lemma.strip()
            redup_pattern = row.get('RedupPattern', '')
            if redup_pattern:
                redup_pattern = redup_pattern.strip()
            
            # Skip comments and empty rows
            if not lemma or lemma.startswith('#'):
                continue
            
            # Only include lemmas with AAB pattern
            if redup_pattern == 'AAB':
                lemmas.append(row)
    
    print(f"Found {len(lemmas)} lemmas with AAB reduplication pattern")
    return lemmas


def generate_xfst_script(lemmas, output_path):
    """
    Generate XFST script for reduplication recognition.
    
    Args:
        lemmas: List of lemma dicts with AAB pattern
        output_path: Path to write XFST script
    """
    lines = []
    
    # Header
    lines.append("! ============================================================")
    lines.append("! XFST Script for Liheci Reduplication Recognition (Stage 2)")
    lines.append("! Auto-generated - DO NOT EDIT MANUALLY")
    lines.append("! ============================================================")
    lines.append("")
    
    # No need to define ChineseChar - XFST handles all Unicode by default
    # Just define reduplication markers
    lines.append("! Reduplication markers and any character wildcard")
    lines.append("define RedupMarker [ 一 | 了 ] ;")
    lines.append("define AnyChar ? ;")
    lines.append("")
    
    # Generate transducers for each lemma
    transducer_names = []
    
    for i, entry in enumerate(lemmas, start=1):
        lemma = entry['Lemma']
        a_char = entry['A']
        b_char = entry['B']
        type_tag = entry['Type']
        
        # Use chars_with_space to properly format Chinese characters
        head_chars = chars_with_space(a_char)
        tail_chars = chars_with_space(b_char)
        
        # Lemma ID
        lemma_id = f"L{i:03d}"
        
        lines.append(f"! {i}. {lemma} ({a_char}+{b_char})")
        
        # Define reduplication patterns
        # Pattern 1: A A B (e.g., 看看书)
        redup_pat1_name = f"{lemma_id}RedupAAB"
        lines.append(f"define {redup_pat1_name} ?* {head_chars} {head_chars} {tail_chars} ?* ;")
        
        # Pattern 2: A 一 A B (e.g., 看一看书)
        redup_pat2_name = f"{lemma_id}RedupAYiAB"
        lines.append(f"define {redup_pat2_name} ?* {head_chars} 一 {head_chars} {tail_chars} ?* ;")
        
        # Pattern 3: A 了 A B (e.g., 看了看书)
        redup_pat3_name = f"{lemma_id}RedupALeAB"
        lines.append(f"define {redup_pat3_name} ?* {head_chars} 了 {head_chars} {tail_chars} ?* ;")
        
        # Combine patterns
        combined_pat = f"{lemma_id}RedupPat"
        lines.append(f"define {combined_pat} {redup_pat1_name} | {redup_pat2_name} | {redup_pat3_name} ;")
        
        # Create transducer with morphological analysis including Head and Tail
        trans_name = f"{lemma_id}Redup"
        upper = f"{lemma}+Lemma+{type_tag}+REDUP+Head:{a_char}+Tail:{b_char}"
        lines.append(f'define {trans_name} "{upper}" : {combined_pat} ;')
        lines.append("")
        
        transducer_names.append(trans_name)
    
    # Combine all transducers
    lines.append("! Combine all reduplication transducers")
    combined = " | ".join(transducer_names)
    lines.append(f"define LiheciRedupRecognizer {combined} ;")
    lines.append("")
    
    # Compile to FST
    lines.append("! Compile and save")
    lines.append("regex LiheciRedupRecognizer ;")
    lines.append("save stack liheci_redup.generator.hfst")
    lines.append("invert net")
    lines.append("save stack liheci_redup.analyser.hfst")
    lines.append("quit")
    lines.append("")
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"Generated XFST script: {output_path}")
    print(f"  Total lemmas: {len(lemmas)}")
    print(f"  Total transducers: {len(transducer_names)}")


def main():
    # Paths
    base_dir = Path(__file__).parent.parent
    csv_path = base_dir / "data" / "liheci_lexicon.csv"
    output_path = base_dir / "scripts" / "hfst_files" / "liheci_redup.xfst"
    
    # Read lexicon (only AAB lemmas)
    lemmas = read_csv_lexicon(csv_path)
    
    # Generate XFST script
    generate_xfst_script(lemmas, output_path)
    
    # Compile XFST to HFST
    xfst_file = output_path.name
    print(f"\n[...] Compiling {xfst_file} with hfst-xfst...")
    result = subprocess.run(
        ["hfst-xfst", "-F", xfst_file],
        cwd=output_path.parent,
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print(f"[OK] Compiled to liheci_redup.analyser.hfst and liheci_redup.generator.hfst")
    else:
        print(f"[ERROR] Compilation failed:")
        print(result.stderr)


if __name__ == "__main__":
    main()
