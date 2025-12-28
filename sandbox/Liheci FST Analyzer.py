import hanlp
import pandas as pd
import sys
import io

INPUT_CSV = "liheci_lexicon.csv"
TEST_FILE = "test_sentences.txt"
OUTPUT_REPORT = "test_report_analyzer.txt" # Changed output file name

print("="*60)
print("  Liheci Project - FST Analyzer (Blind Mode)")
print("="*60)

# ==========================================
# 1. Config and Initialization
# ==========================================
print(f"[Init] Loading Lexicon from {INPUT_CSV}...")
try:
    # Use index_col=False to prevent first column from being used as index
    df = pd.read_csv(INPUT_CSV, sep=None, engine='python', index_col=False)
    df.columns = [c.strip() for c in df.columns] 
except Exception as e:
    print(f"Error: 找不到 {INPUT_CSV}. Error: {e}")
    exit()

# like WholePath and SplitPath in Lexc
fst_whole_path = {} 
fst_split_rules = [] 

for idx, row in df.iterrows():
    # Ensure columns exist before accessing them
    if 'Lemma' not in row or 'A' not in row or 'B' not in row:
        print(f"Warning: Skipping row {idx} due to missing required columns (Lemma, A, B).")
        continue

    lemma = row['Lemma']
    head = row['A']
    tail = row['B']
    l_type = str(row.get('Type', ''))
    
    # --- to sumulate WholePath (fused) ---
    # Key: surface form, Value: lemma
    fst_whole_path[lemma] = lemma
    fst_whole_path[f"{head}{head}{tail}"] = lemma        # AAB
    fst_whole_path[f"{head}一{head}{tail}"] = lemma      # A一AB
    
    # --- to sumulate SplitPath (discrete) Tag constraints ---
    # this aligns with the constraints in lexc definitions
    if "Pseudo" in l_type or "Simplex" in l_type:
        head_tags = ['VV', 'VA', 'NN']
    elif "Modifier" in l_type:
        head_tags = ['NN', 'AD', 'JJ']
    else:
        head_tags = ['VV']

    fst_split_rules.append({
        'lemma': lemma,
        'head': head,
        'tail': tail,
        'type': l_type,
        'allowed_head_tags': head_tags
    })

print("[Init] Loading HanLP Models...")
# HanLP models are only loaded once
tokenizer = hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH)
tagger = hanlp.load(hanlp.pretrained.pos.CTB9_POS_ELECTRA_SMALL)

# ==========================================
# 2. Core Analysis Engine (Blind Mode)
# The function now finds ALL matching Liheci analyses in the sentence
# ==========================================
def analyze_sentence(text, file_handle):
    """Analyzes a sentence and returns all detected Liheci analyses (lemmas)."""
    
    # 1. HanLP Pipeline
    words = tokenizer(text)
    tags = tagger(words)
    
    hanlp_output = " ".join([f"{w}/{t}" for w, t in zip(words, tags)])
    file_handle.write(f"   [HanLP Input]: {hanlp_output}\n")

    detected_analyses = []
    
    # --- PATH 1: WholeEntry (Check Fused Tokens) ---
    # Iterate through words in the sentence
    for word in words:
        if word in fst_whole_path:
            matched_lemma = fst_whole_path[word]
            if matched_lemma not in detected_analyses:
                detected_analyses.append(matched_lemma)
                file_handle.write(f"   ✅ [FST Found]: Lemma=[{matched_lemma}] Path=WholeEntry (Token: {word})\n")
    
    # --- PATH 2: SplitEntry (Check Split Tokens with possible insertions) ---
    # Iterate through all defined rules and try to match them in the sentence
    for rule in fst_split_rules:
        lemma = rule['lemma']
        head = rule['head']
        tail = rule['tail']
        allowed_tags = rule['allowed_head_tags']
        
        # Check if we already found this lemma via a WholeEntry path
        if lemma in detected_analyses:
            continue
            
        for i, (word, tag) in enumerate(zip(words, tags)):
            
            # Head match (Head component must be a token detected by HanLP)
            is_head_match = (word == head) or (word == f"{head}{head}")
            
            if is_head_match:
                
                # Tag Constraint Check (crucial for disambiguation)
                if tag not in allowed_tags:
                    continue

                # Scan for Tail in a limited window
                window_end = min(len(words), i + 10) # Look up to 10 tokens ahead
                for j in range(i + 1, window_end):
                    scan_word = words[j]
                    
                    # Tail Match (Tail component must be a token detected by HanLP)
                    if scan_word == tail or scan_word.endswith(tail):
                        
                        middle_tokens = words[i+1:j]
                        middle_content = "".join(middle_tokens)
                        
                        # Apply Filters/Constraints (Simulated Replace Rules/Grammar)
                        if "，" in middle_content or "。" in middle_content: 
                            continue # Don't allow punctuation insertion
                        if len(middle_tokens) == 0:
                            # 0:0 Zero Insertion (Adjacent)
                            file_handle.write(f"   ✅ [FST Found]: Lemma=[{lemma}] Path=SplitEntry (Zero Insertion: {word} + {scan_word})\n")
                            if lemma not in detected_analyses: detected_analyses.append(lemma)
                            break
                        
                        # With Insertion
                        file_handle.write(f"   ✅ [FST Found]: Lemma=[{lemma}] Path=SplitEntry (Insertion: {word} ... {scan_word} | Inserted: [{middle_content}])\n")
                        if lemma not in detected_analyses: detected_analyses.append(lemma)
                        break 
                if lemma in detected_analyses: break
            
    # Always return the list of all unique detected Liheci lemmas
    return detected_analyses

# ==========================================
# 3. Test Suite Runner
# ==========================================
def run_test_suite():
    print(f"[Run] Processing {TEST_FILE}...")
    total = 0; passed = 0
    
    with open(TEST_FILE, "r", encoding="utf-8") as f_in, \
         open(OUTPUT_REPORT, "w", encoding="utf-8") as f_out:
        
        f_out.write("TEST REPORT | Python FST Analyzer (Blind Mode)\n")
        f_out.write("==================================================\n")

        lines = f_in.readlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"): continue
            
            # Structure: TargetLemma | Sentence | ExpectsTrue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 3: continue

            target_lemma = parts[0]
            sentence = parts[1]
            expect_true = (parts[2].lower() == "true")
            
            f_out.write(f"--------------------------------------------------\n")
            f_out.write(f"Target (for testing): [{target_lemma}]\n")
            f_out.write(f"Sentence:             {sentence}\n")
            
            # --- CORE CHANGE: Call analyze_sentence without target_lemma guidance ---
            detected_lemmas = analyze_sentence(sentence, f_out)
            
            # Check the analysis results against the expectation
            # 1. If we expected TRUE, check if the target_lemma is in the list of detected lemmas.
            # 2. If we expected FALSE, check if the target_lemma is NOT in the list (False Positive check).
            
            actual_detected = target_lemma in detected_lemmas
            status = "PASS" if actual_detected == expect_true else "FAIL"
            
            f_out.write(f"Detected Analyses:    {detected_lemmas if detected_lemmas else 'None'}\n")
            f_out.write(f"Expected:             {expect_true} | Actual Found: {actual_detected} | Status: {status}\n")
            
            if status == "PASS": passed += 1
            total += 1
            print(f"\rProcessed {total} cases...", end="")

        f_out.write(f"\n\nSUMMARY: {passed}/{total} Passed ({passed/total*100:.2f}%)")
    
    print(f"\n[Done] Check {OUTPUT_REPORT}")

if __name__ == "__main__":
    run_test_suite()