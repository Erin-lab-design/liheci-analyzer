#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evaluation Script for Liheci Analyzer
Computes Precision, Recall, Accuracy, F1 for:
1. Overall performance
2. By type category (Verb-Object+PseudoV-O, Modifier-Head+SimplexWord)
3. By shape (SPLIT, WHOLE, REDUP)
4. By error type in false positives
"""

import pandas as pd
from pathlib import Path
from collections import defaultdict

# Paths
BASE_DIR = Path(__file__).parent.parent
TEST_FILE = BASE_DIR / 'data' / 'test_sentences.txt'
RESULT_FILE = BASE_DIR / 'outputs' / 'liheci_pos_validated.tsv'
LEXICON_FILE = BASE_DIR / 'data' / 'liheci_lexicon.csv'
REPORT_FILE = BASE_DIR / 'outputs' / 'liheci_evaluation_report_by07.txt'

# Global output buffer for writing to file
output_lines = []


def log(text=""):
    """Print and also save to buffer for file output"""
    print(text)
    output_lines.append(text)

# Type groupings
TYPE_GROUPS = {
    'VO_Group': ['Verb-Object', 'PseudoV-O'],
    'MH_Group': ['Modifier-Head', 'SimplexWord']
}


def load_test_data():
    """Load test sentences with gold labels"""
    test_data = []
    with open(TEST_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('sent_id'):
                continue
            parts = line.split('\t')
            if len(parts) >= 4:
                sent_id = int(parts[0])
                gold_stem = parts[1]
                gold_label = parts[2] == 'True'
                # Extract error type if present
                error_type = None
                if '[' in parts[3] and ']' in parts[3]:
                    error_type = parts[3].split('[')[1].split(']')[0]
                test_data.append({
                    'sent_id': sent_id, 
                    'gold_stem': gold_stem, 
                    'gold_label': gold_label,
                    'error_type': error_type
                })
    return pd.DataFrame(test_data)


def load_lexicon():
    """Load lexicon to get type info for each lemma"""
    lexicon = pd.read_csv(LEXICON_FILE, encoding='utf-8')
    lemma_to_type = {}
    for _, row in lexicon.iterrows():
        lemma_to_type[row['Lemma']] = row['Type']
    return lemma_to_type


def compute_metrics(TP, FP, FN, TN):
    """Compute precision, recall, accuracy, F1"""
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / (TP + FN) if (TP + FN) > 0 else 0
    accuracy = (TP + TN) / (TP + TN + FP + FN) if (TP + TN + FP + FN) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    return {
        'TP': TP, 'FP': FP, 'FN': FN, 'TN': TN,
        'Precision': precision,
        'Recall': recall,
        'Accuracy': accuracy,
        'F1': f1
    }


def print_metrics(name, metrics):
    """Pretty print metrics"""
    log(f"\n{'='*60}")
    log(f"  {name}")
    log(f"{'='*60}")
    log(f"  Confusion Matrix:")
    log(f"    TP={metrics['TP']:3d}  FP={metrics['FP']:3d}")
    log(f"    FN={metrics['FN']:3d}  TN={metrics['TN']:3d}")
    log(f"  Metrics:")
    log(f"    Precision = {metrics['Precision']:.4f} ({metrics['Precision']*100:.2f}%)")
    log(f"    Recall    = {metrics['Recall']:.4f} ({metrics['Recall']*100:.2f}%)")
    log(f"    Accuracy  = {metrics['Accuracy']:.4f} ({metrics['Accuracy']*100:.2f}%)")
    log(f"    F1 Score  = {metrics['F1']:.4f} ({metrics['F1']*100:.2f}%)")


def get_type_group(type_tag):
    """Map type_tag to group"""
    for group_name, types in TYPE_GROUPS.items():
        if type_tag in types:
            return group_name
    return 'Unknown'


def main():
    log("="*60)
    log("  Liheci Analyzer Evaluation")
    log("="*60)
    
    # Load data
    test_df = load_test_data()
    result_df = pd.read_csv(RESULT_FILE, sep='\t')
    lemma_to_type = load_lexicon()
    
    # Add type info to test_df
    test_df['type_tag'] = test_df['gold_stem'].map(lemma_to_type)
    test_df['type_group'] = test_df['type_tag'].apply(get_type_group)
    
    # Create keys
    test_df['key'] = test_df.apply(lambda x: (x['sent_id'], x['gold_stem']), axis=1)
    result_df['key'] = result_df.apply(lambda x: (x['sent_id'], x['lemma']), axis=1)
    
    # Add type group to result_df
    result_df['type_group'] = result_df['type_tag'].apply(get_type_group)
    
    # === OVERALL METRICS ===
    test_true_keys = set(test_df[test_df['gold_label']==True]['key'])
    test_false_keys = set(test_df[test_df['gold_label']==False]['key'])
    result_keys = set(result_df['key'])
    
    TP = len(result_keys & test_true_keys)
    FP = len(result_keys & test_false_keys)
    FN = len(test_true_keys - result_keys)
    TN = len(test_false_keys - result_keys)
    
    overall_metrics = compute_metrics(TP, FP, FN, TN)
    print_metrics("OVERALL", overall_metrics)
    
    # === BY TYPE GROUP ===
    log("\n" + "="*60)
    log("  BY TYPE GROUP")
    log("="*60)
    
    for group_name in ['VO_Group', 'MH_Group']:
        # Filter test data by group
        group_test = test_df[test_df['type_group'] == group_name]
        group_true_keys = set(group_test[group_test['gold_label']==True]['key'])
        group_false_keys = set(group_test[group_test['gold_label']==False]['key'])
        
        # Filter result data by group
        group_result = result_df[result_df['type_group'] == group_name]
        group_result_keys = set(group_result['key'])
        
        TP = len(group_result_keys & group_true_keys)
        FP = len(group_result_keys & group_false_keys)
        FN = len(group_true_keys - group_result_keys)
        TN = len(group_false_keys - group_result_keys)
        
        types_in_group = TYPE_GROUPS[group_name]
        group_label = f"{group_name} ({', '.join(types_in_group)})"
        metrics = compute_metrics(TP, FP, FN, TN)
        print_metrics(group_label, metrics)
    
    # === BY SHAPE ===
    log("\n" + "="*60)
    log("  BY SHAPE")
    log("="*60)
    
    for shape in ['SPLIT', 'WHOLE', 'REDUP']:
        shape_result = result_df[result_df['shape'] == shape]
        shape_result_keys = set(shape_result['key'])
        
        TP = len(shape_result_keys & test_true_keys)
        FP = len(shape_result_keys & test_false_keys)
        # FN and TN are harder to define per-shape, so we only show TP/FP and Precision
        
        total = TP + FP
        precision = TP / total if total > 0 else 0
        
        log(f"\n  {shape}:")
        log(f"    Total output: {total}")
        log(f"    TP={TP}, FP={FP}")
        log(f"    Precision = {precision:.4f} ({precision*100:.2f}%)")
    
    # === FALSE POSITIVE ANALYSIS ===
    log("\n" + "="*60)
    log("  FALSE POSITIVE ANALYSIS")
    log("="*60)
    
    # Get  FP keys with their error types
    fp_keys = result_keys & test_false_keys
    fp_test_rows = test_df[test_df['key'].isin(fp_keys)]
    
    error_counts = fp_test_rows['error_type'].value_counts()
    log("\n  Error type distribution in FP:")
    for error_type, count in error_counts.items():
        log(f"    {error_type}: {count}")
    
    # === FALSE NEGATIVE ANALYSIS ===
    log("\n" + "="*60)
    log("  FALSE NEGATIVE ANALYSIS")
    log("="*60)
    
    fn_keys = test_true_keys - result_keys
    fn_test_rows = test_df[test_df['key'].isin(fn_keys)]
    
    if len(fn_test_rows) > 0:
        log(f"\n  Missed {len(fn_keys)} true positives:")
        for _, row in fn_test_rows.iterrows():
            log(f"    sent_id={row['sent_id']}, lemma={row['gold_stem']}")
    else:
        log("\n  No false negatives! All true positives were detected.")
    
    log("\n" + "="*60)
    log("  SUMMARY TABLE")
    log("="*60)
    log(f"\n  {'Category':<30} {'Precision':>10} {'Recall':>10} {'F1':>10}")
    log(f"  {'-'*60}")
    log(f"  {'OVERALL':<30} {overall_metrics['Precision']*100:>9.2f}% {overall_metrics['Recall']*100:>9.2f}% {overall_metrics['F1']*100:>9.2f}%")
    
    for group_name in ['VO_Group', 'MH_Group']:
        group_test = test_df[test_df['type_group'] == group_name]
        group_true_keys = set(group_test[group_test['gold_label']==True]['key'])
        group_false_keys = set(group_test[group_test['gold_label']==False]['key'])
        group_result = result_df[result_df['type_group'] == group_name]
        group_result_keys = set(group_result['key'])
        
        TP = len(group_result_keys & group_true_keys)
        FP = len(group_result_keys & group_false_keys)
        FN = len(group_true_keys - group_result_keys)
        TN = len(group_false_keys - group_result_keys)
        
        metrics = compute_metrics(TP, FP, FN, TN)
        types_str = '+'.join(TYPE_GROUPS[group_name])
        log(f"  {types_str:<30} {metrics['Precision']*100:>9.2f}% {metrics['Recall']*100:>9.2f}% {metrics['F1']*100:>9.2f}%")
    
    log(f"\n{'='*60}")
    log("  Evaluation Complete")
    log(f"{'='*60}")
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    print(f"\n[INFO] Report saved to: {REPORT_FILE}")


if __name__ == '__main__':
    main()
