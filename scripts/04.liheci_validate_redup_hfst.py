#!/usr/bin/env python3
"""
Stage 2: Validate reduplication using HFST REDUP recognizer.

Strategy:
1. Read Stage 1 output (liheci_hfst_outputs.tsv)
2. Identify sentences with both WHOLE and SPLIT for same lemma (potential redup)
3. Run these sentences through REDUP HFST
4. If REDUP HFST recognizes it → valid redup, keep as REDUP
5. If REDUP HFST doesn't recognize it → invalid redup, remove from output
6. Write updated output with deduplicated and filtered results
"""

import csv
import logging
import subprocess
from pathlib import Path
from collections import defaultdict


def setup_logging():
    """Configure logging."""
    log_file = Path(__file__).parent.parent / "outputs" / "liheci_redup_validation.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        encoding="utf-8",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8', mode='w'),
            logging.StreamHandler()
        ]
    )


def run_hfst_redup_on_sentence(sentence, hfst_path):
    """
    Run HFST REDUP recognizer on a sentence.
    
    Returns:
        list of str: Analysis strings if reduplication found, empty list otherwise
    """
    try:
        result = subprocess.run(
            [str(hfst_path), str(Path(__file__).parent / "liheci_redup.analyser.hfst")],
            input=sentence,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=5
        )
        
        lines = result.stdout.strip().split('\n')
        analyses = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith('>'):
                continue
            # Parse TAB-separated output: input\tanalysis\tweight
            parts = line.split('\t')
            if len(parts) >= 2:
                analysis = parts[1].strip()
                # Skip lines with "+?" (no match)
                if analysis and not analysis.endswith('+?'):
                    analyses.append(analysis)
        
        return analyses
    
    except Exception as e:
        logging.warning(f"HFST error for sentence '{sentence[:30]}...': {e}")
        return []


def validate_reduplication(stage1_output, stage2_output, hfst_path):
    """
    Validate reduplication patterns from Stage 1 using HFST REDUP recognizer.
    """
    # Read Stage 1 output and deduplicate
    rows = []
    seen_keys = set()
    all_keys = 0
    
    logging.info("Reading Stage 1 output...")
    with open(stage1_output, encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter='\t')
        header = reader.fieldnames
        
        for row in reader:
            all_keys += 1
            # Deduplicate by (sent_id, lemma, shape)
            key = (row['sent_id'], row['lemma'], row['shape'])
            if key not in seen_keys:
                seen_keys.add(key)
                rows.append(row)
    
    logging.info(f"  Read {all_keys} rows, {len(rows)} unique after dedup")
    logging.info(f"  Duplicates removed: {all_keys - len(rows)}")
    
    # Group by (sent_id, lemma) to find potential reduplication
    groups = defaultdict(list)
    for row in rows:
        key = (row['sent_id'], row['lemma'])
        groups[key].append(row)
    
    # Identify potential reduplication (both WHOLE and SPLIT present)
    potential_redup_sentences = {}  # sent_id -> sentence
    potential_redup_keys = set()
    
    for (sent_id, lemma), group_rows in groups.items():
        shapes = {row['shape'] for row in group_rows}
        if 'WHOLE' in shapes and 'SPLIT' in shapes:
            potential_redup_keys.add((sent_id, lemma))
            potential_redup_sentences[sent_id] = group_rows[0]['sentence']
    
    logging.info(f"\nIdentified {len(potential_redup_keys)} potential reduplication patterns")
    
    # Validate using HFST REDUP
    logging.info("\nValidating reduplication with HFST...")
    valid_redup = set()  # (sent_id, lemma) that are valid
    
    for sent_id, sentence in potential_redup_sentences.items():
        analyses = run_hfst_redup_on_sentence(sentence, hfst_path)
        
        if analyses:
            # Extract lemmas from analyses
            for analysis in analyses:
                # analysis format: "lemma+Lemma+Type+REDUP"
                if '+REDUP' in analysis:
                    lemma = analysis.split('+')[0]
                    valid_redup.add((sent_id, lemma))
                    logging.info(f"  ✓ Valid REDUP: sent_id={sent_id}, lemma={lemma}, sentence='{sentence[:40]}...'")
    
    logging.info(f"\nValid reduplication found: {len(valid_redup)}")
    
    # Build final output
    final_rows = []
    stats = {
        'original': all_keys,
        'dedup': len(rows),
        'potential_redup_total': sum(len(groups[k]) for k in potential_redup_keys),
        'valid_redup': len(valid_redup),
        'invalid_redup_filtered': 0,
        'non_redup': 0
    }
    
    for (sent_id, lemma), group_rows in groups.items():
        shapes = {row['shape'] for row in group_rows}
        is_potential_redup = 'WHOLE' in shapes and 'SPLIT' in shapes
        
        if is_potential_redup:
            if (sent_id, lemma) in valid_redup:
                # Valid reduplication - keep one entry as REDUP
                for row in group_rows:
                    if row['shape'] == 'SPLIT':
                        row['shape'] = 'REDUP'
                        row['is_redup'] = 'True'
                        final_rows.append(row)
                        break
            else:
                # Invalid reduplication - filter out
                stats['invalid_redup_filtered'] += len(group_rows)
                logging.info(f"  ✗ Filtered invalid REDUP: sent_id={sent_id}, lemma={lemma}")
        else:
            # Not reduplication - keep as is
            stats['non_redup'] += len(group_rows)
            final_rows.extend(group_rows)
    
    # Write output
    with open(stage2_output, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header, delimiter='\t')
        writer.writeheader()
        writer.writerows(final_rows)
    
    # Report
    logging.info("\n" + "=" * 60)
    logging.info("Stage 2 Validation Results:")
    logging.info(f"  Original rows: {stats['original']}")
    logging.info(f"  After deduplication: {stats['dedup']}")
    logging.info(f"  Potential reduplication patterns: {stats['potential_redup_total']} rows")
    logging.info(f"    Valid reduplication kept: {stats['valid_redup']} lemmas")
    logging.info(f"    Invalid reduplication filtered: {stats['invalid_redup_filtered']} rows")
    logging.info(f"  Non-reduplication kept: {stats['non_redup']} rows")
    logging.info(f"  Total output rows: {len(final_rows)}")
    logging.info(f"\nOutput written to: {stage2_output}")
    logging.info("=" * 60)


def main():
    setup_logging()
    
    # Paths
    base_dir = Path(__file__).parent.parent
    stage1_output = base_dir / "outputs" / "liheci_hfst_outputs.tsv"
    stage2_output = base_dir / "outputs" / "liheci_hfst_outputs_filtered.tsv"
    hfst_path = base_dir / "hfst-3.16.2" / "hfst" / "bin" / "hfst-lookup.exe"
    
    # Validate
    validate_reduplication(stage1_output, stage2_output, hfst_path)


if __name__ == "__main__":
    main()
