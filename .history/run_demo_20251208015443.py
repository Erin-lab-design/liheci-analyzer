import hanlp
import pandas as pd
import sys
import io

# ==========================================
# 配置
# ==========================================
INPUT_CSV = "liheci_lexicon.csv"
TEST_FILE = "test_sentences.txt"
OUTPUT_REPORT = "test_report.txt"

print("="*60)
print("  Liheci Project - FST Simulator (Strict Tag Mode)")
print("="*60)

# ==========================================
# 1. 构建内存 FST (模拟 generate_lexc.py 的逻辑)
# ==========================================
print(f"[Init] Loading Lexicon from {INPUT_CSV}...")
try:
    df = pd.read_csv(INPUT_CSV, sep=None, engine='python')
    df.columns = [c.strip() for c in df.columns] 
except:
    print(f"Error: 找不到 {INPUT_CSV}")
    exit()

# 对应 Lexc 中的 WholePath 和 SplitPath
fst_whole_path = {} 
fst_split_rules = [] 

for idx, row in df.iterrows():
    lemma = row['Lemma']
    head = row['A']
    tail = row['B']
    l_type = str(row.get('Type', ''))
    
    # --- 模拟 WholePath (融合态) ---
    # 只要分词结果是这些，FST 就接受
    fst_whole_path[lemma] = lemma
    fst_whole_path[f"{head}{head}{tail}"] = lemma        # AAB
    fst_whole_path[f"{head}{head}{tail}{tail}"] = lemma  # AABB
    fst_whole_path[f"{head}一{head}{tail}"] = lemma      # A一AB
    
    # --- 模拟 SplitPath (离散态) Tag 约束 ---
    # 这对应 generate_lexc.py 里写的 if/elif 逻辑
    if "Pseudo" in l_type or "Simplex" in l_type:
        # Type B: 宽松
        head_tags = ['VV', 'VA', 'NN']
    elif "Modifier" in l_type:
        # Type C: 允许形容词/名词
        head_tags = ['NN', 'AD', 'JJ']
    else:
        # Type A: 严格动词 (杀掉 丐帮/NN)
        head_tags = ['VV']

    fst_split_rules.append({
        'lemma': lemma,
        'head': head,
        'tail': tail,
        'type': l_type,
        'allowed_head_tags': head_tags
    })

print("[Init] Loading HanLP Models...")
tokenizer = hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH)
tagger = hanlp.load(hanlp.pretrained.pos.CTB9_POS_ELECTRA_SMALL)

# ==========================================
# 2. 核心分析引擎
# ==========================================
def analyze_sentence(text, target_lemma, file_handle):
    # 1. HanLP 流水线
    words = tokenizer(text)
    tags = tagger(words)
    
    hanlp_output = " ".join([f"{w}/{t}" for w, t in zip(words, tags)])
    file_handle.write(f"   [HanLP Input]: {hanlp_output}\n")

    found = False
    
    # --- PATH 1: WholeEntry (检查融合态) ---
    for word in words:
        if word in fst_whole_path:
            matched_lemma = fst_whole_path[word]
            if matched_lemma == target_lemma:
                file_handle.write(f"   ✅ [FST Match]: Path=WholeEntry (Fused Token)\n")
                file_handle.write(f"      - Token:     {word}\n")
                found = True
                break
    
    # --- PATH 2: SplitEntry (检查离散态) ---
    if not found:
        for rule in fst_split_rules:
            if rule['lemma'] != target_lemma: continue
            
            head = rule['head']
            tail = rule['tail']
            allowed_tags = rule['allowed_head_tags']
            
            for i, (word, tag) in enumerate(zip(words, tags)):
                
                # Head 匹配 (包含 "见见" 这种 Head 重叠)
                is_head_match = (word == head) or (word == f"{head}{head}")
                
                if is_head_match:
                    # [关键] Tag Constraint Check
                    # 如果是 "帮/NN"，而 allowed_tags 是 ['VV']，这里直接 continue
                    if tag not in allowed_tags:
                        continue

                    # 扫描 Tail
                    window_end = min(len(words), i + 10)
                    for j in range(i + 1, window_end):
                        scan_word = words[j]
                        
                        # Tail 匹配
                        if scan_word == tail or scan_word.endswith(tail):
                            
                            middle_tokens = words[i+1:j]
                            middle_content = "".join(middle_tokens)
                            
                            # 0:0 Zero Insertion (紧邻)
                            if len(middle_tokens) == 0:
                                file_handle.write(f"   ✅ [FST Match]: Path=SplitEntry (Zero Insertion)\n")
                                file_handle.write(f"      - Sequence:  {word} + {scan_word}\n")
                                found = True
                                break
                                
                            # MiddleField 简单过滤 (标点)
                            if "，" in middle_content or "。" in middle_content: continue
                            
                            # 大便 vs 大便宜 (Tail 长度检查)
                            if len(scan_word) > len(tail) and rule['lemma'] == "大便": continue

                            file_handle.write(f"   ✅ [FST Match]: Path=SplitEntry (With Insertion)\n")
                            file_handle.write(f"      - Sequence:  {word} ... {scan_word}\n")
                            file_handle.write(f"      - Inserted:  [{middle_content}]\n")
                            found = True
                            break 
                    if found: break
            if found: break

    if not found:
        file_handle.write(f"   ❌ [FST Reject]: No valid path found.\n")
    
    return found

# ==========================================
# 3. 运行测试套件
# ==========================================
def run_test_suite():
    print(f"[Run] Processing {TEST_FILE}...")
    total = 0; passed = 0
    
    with open(TEST_FILE, "r", encoding="utf-8") as f_in, \
         open(OUTPUT_REPORT, "w", encoding="utf-8") as f_out:
        
        f_out.write("TEST REPORT | Python FST Simulator\n")
        f_out.write("==================================================\n")

        lines = f_in.readlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"): continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 3: continue

            target_lemma = parts[0]
            sentence = parts[1]
            expect_true = (parts[2].lower() == "true")
            
            f_out.write(f"--------------------------------------------------\n")
            f_out.write(f"Target:   [{target_lemma}]\n")
            f_out.write(f"Sentence: {sentence}\n")
            
            detected = analyze_sentence(sentence, target_lemma, f_out)
            
            status = "PASS" if detected == expect_true else "FAIL"
            f_out.write(f"Expected: {expect_true} | Actual: {detected} | Status: {status}\n")
            
            if status == "PASS": passed += 1
            total += 1
            print(f"\rProcessed {total} cases...", end="")

        f_out.write(f"\n\nSUMMARY: {passed}/{total} Passed ({passed/total*100:.2f}%)")
    
    print(f"\n[Done] Check {OUTPUT_REPORT}")

if __name__ == "__main__":
    run_test_suite()