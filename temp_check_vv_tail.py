import re

# Read TSV
with open('outputs/liheci_pos_summary.tsv', 'r', encoding='utf-8') as f:
    lines = f.readlines()

header = lines[0].strip().split('\t')
lemma_idx = header.index('lemma')
type_idx = header.index('type_tag')
head_idx = header.index('head_desc')
tail_idx = header.index('tail_desc')
sentence_idx = header.index('sentence')
is_valid_idx = header.index('is_valid')
status_idx = header.index('status')
insertion_idx = header.index('insertion_desc')

# Find Verb-Object with TAIL=VV
vv_tail_cases = []

for line in lines[1:]:
    cols = line.strip().split('\t')
    if len(cols) <= max(lemma_idx, type_idx, head_idx, tail_idx, insertion_idx):
        continue
    
    lemma = cols[lemma_idx]
    liheci_type = cols[type_idx]
    head_desc = cols[head_idx]
    tail_desc = cols[tail_idx]
    sentence = cols[sentence_idx]
    is_valid = cols[is_valid_idx]
    status = cols[status_idx]
    insertion = cols[insertion_idx]
    
    if liheci_type != 'Verb-Object':
        continue
    
    # Extract TAIL POS
    tail_match = re.search(r'/([A-Z]+)', tail_desc)
    if tail_match and tail_match.group(1) == 'VV':
        vv_tail_cases.append({
            'lemma': lemma,
            'head': head_desc,
            'tail': tail_desc,
            'sentence': sentence,
            'is_valid': is_valid,
            'status': status,
            'insertion': insertion
        })

print(f'=== Verb-Object with TAIL=VV (Total: {len(vv_tail_cases)}) ===\n')

for i, case in enumerate(vv_tail_cases, 1):
    print(f'[{i}] {case["lemma"]}')
    print(f'    HEAD: {case["head"]}')
    print(f'    TAIL: {case["tail"]}')
    print(f'    Insertion: {case["insertion"]}')
    print(f'    Valid: {case["is_valid"]} | {case["status"]}')
    print(f'    Sentence: {case["sentence"]}')
    print()
