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
print("  Liheci Project - Python FST Engine")
print("  (Replaces broken binary compilation)")
print("="*60)

# ==========================================
# 1. 初始化 (加载词典并构建 FST 规则)
# ==========================================
print(f"[Init] Loading Lexicon from {INPUT_CSV}...")
try:
    df = pd.read_csv(INPUT_CSV, sep=None, engine='python')
    df.columns = [c.strip() for c in df.columns] 
except:
    print(f"Error: 找不到 {INPUT_CSV}")
    exit()

# 内存中的 FST 路径库
fst_whole_path = {} 
fst_split_rules = [] 

for idx, row in df.iterrows():
    lemma = row['Lemma']
    head = row['A']
    tail = row['B']
    l_type = str(row.get('Type', ''))
    
    # 逻辑判断：类型分类
    is_pseudo = "Pseudo" in l_type or "Simplex" in l_type
    is_mod = "Modifier" in l_type
    is_standard = not (is_pseudo or is_mod)

    # ----------------------------------------------------
    # Path 1: WholePath (融合态逻辑)
    # ----------------------------------------------------
    # 基础形式
    fst_whole_path[lemma] = lemma
    
    # [Smart Reduplication Logic]
    # 只有标准 VO 词，FST 才生成 AAB 路径
    if is_standard:
        fst_whole_path[f"{head}{head}{tail}"] = lemma        # AAB (见见面)
        fst_whole_path[f"{head}{head}{tail}{tail}"] = lemma  # AABB
        fst_whole_path[f"{head}一{head}{tail}"] = lemma      # A一AB
    
    # ----------------------------------------------------
    # Path 2: SplitPath (离散态逻辑)
    # ----------------------------------------------------
    # [Tag Constraint Logic]
    if is_pseudo:
        head_tags = ['VV', 'VA', 'NN'] # 幽默: 比较宽容
    elif is_mod:
        head_tags = ['NN', 'AD', 'JJ', 'VV'] # 小便/暂停: 允许名/形/动
    else:
        head_tags = ['VV'] # 吃饭/帮忙: 严格要求动词 (杀掉 丐帮/NN)

    fst_split_rules.append({
        'lemma': lemma,
        'head': head,
        'tail': tail,
        'type': l_type,
        'allowed_head_tags': head_tags
    })

# ==========================================
# 2. 初始化 HanLP
# ==========================================
print("[Init] Loading HanLP Models...")
tokenizer = hanlp.load(hanlp.pretrained.tok.COARSE_ELECTRA_SMALL_ZH)
tagger = hanlp.load(hanlp.pretrained.pos.CTB9_POS_ELECTRA_SMALL)

# ==========================================
# 3. 核心分析引擎 (FST 运行时)
# ==========================================
def analyze_sentence(text, target_lemma, file_handle):
    # 1. HanLP 分词
    words = tokenizer(text)
    tags = tagger(words)
    
    hanlp_output = " ".join([f"{w}/{t}" for w, t in zip(words, tags)])
    file_handle.write(f"   [HanLP Input]: {hanlp_output}\n")

    found = False
    
    # --- 尝试走 WholePath ---
    for word in words:
        if word in fst_whole_path:
            matched_lemma = fst_whole_path[word]
            if matched_lemma == target_lemma:
                file_handle.write(f"   ✅ [FST Match]: Path=WholeEntry (Fused)\n")
                file_handle.write(f"      - Token:     {word}\n")
                found = True
                break
    
    # --- 尝试走 SplitPath ---
    if not found:
        for rule in fst_split_rules:
            if rule['lemma'] != target_lemma: continue
            
            head = rule['head']
            tail = rule['tail']
            allowed_tags = rule['allowed_head_tags']
            
            for i, (word, tag) in enumerate(zip(words, tags)):
                
                # Head 匹配逻辑 (包含正则逻辑: startswith)
                is_head_match = False
                # 精确匹配
                if word == head or word == f"{head}{head}": 
                    is_head_match = True
                # 动补结构匹配 (仅限 VV, 且非 Pseudo)
                elif tag == 'VV' and word.startswith(head) and "Pseudo" not in rule['type']:
                    is_head_match = True # 允许 "吃完" 匹配 "吃"
                
                if is_head_match:
                    # [Constraint Check] Tag 必须符合类型要求
                    if tag not in allowed_tags: 
                        continue

                    # 扫描 Tail
                    window_end = min(len(words), i + 10)
                    for j in range(i + 1, window_end):
                        scan_word = words[j]
                        scan_tag = tags[j]
                        
                        # Tail 匹配逻辑 (包含正则逻辑: endswith)
                        is_tail_match = False
                        if scan_word == tail: is_tail_match = True
                        # 允许 Tail 包含修饰 (如 "热水澡" 包含 "澡")
                        elif scan_tag in ['NN', 'VV'] and scan_word.endswith(tail):
                            is_tail_match = True
                        
                        if is_tail_match:
                            middle_tokens = words[i+1:j]
                            middle_content = "".join(middle_tokens)
                            
                            # 0:0 紧邻检测
                            if len(middle_tokens) == 0:
                                file_handle.write(f"   ✅ [FST Match]: Path=SplitEntry (Zero Insertion)\n")
                                file_handle.write(f"      - Structure: {word} + {scan_word}\n")
                                found = True
                                break
                                
                            # MiddleField 基础过滤
                            if "，" in middle_content or "。" in middle_content: continue
                            
                            # 防止 "大便" 匹配 "大便宜" (便宜长度2 > 便长度1)
                            if len(scan_word) > len(tail) and rule['lemma'] == "大便" and not scan_word.endswith("便"):
                                continue

                            file_handle.write(f"   ✅ [FST Match]: Path=SplitEntry (With Insertion)\n")
                            file_handle.write(f"      - Structure: {word} ... {scan_word}\n")
                            file_handle.write(f"      - Inserted:  [{middle_content}]\n")
                            found = True
                            break 
                    if found: break
            if found: break

    if not found:
        file_handle.write(f"   ❌ [FST Reject]: No valid path found.\n")
    
    return found

# ==========================================
# 4. 执行测试
# ==========================================
def run_test_suite():
    print(f"[Run] Processing {TEST_FILE}...")
    total = 0; passed = 0
    
    with open(TEST_FILE, "r", encoding="utf-8") as f_in, \
         open(OUTPUT_REPORT, "w", encoding="utf-8") as f_out:
        
        f_out.write("TEST REPORT | Python FST Engine (HanLP)\n")
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