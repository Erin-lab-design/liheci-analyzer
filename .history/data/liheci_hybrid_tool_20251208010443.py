import hanlp
import pandas as pd
import subprocess
import os
import sys

# ==============================================================================
# 配置与初始化
# ==============================================================================
INPUT_CSV = "liheci_lexicon.csv"
TEST_FILE = "test_sentences.txt"
OUTPUT_REPORT = "test_report_hybrid.txt"
HFST_PATH = "/Users/mac/liheci_project/fst/middle.hfst" # FST 文件名 (假设和脚本在同一目录，或者你手动指定绝对路径)

# --- FST 关键字与符号定义 (与 middle_grammar.xfst 保持同步) ---
FST_KEYWORDS = set([
    "了", "着", "过", "的", "之", "完", "好", "到", "见", "错", "坏", "死", "透", "上", "下", "起", "出", "回", "开", 
    "得", "不", "个", "次", "顿", "把", "天", "年", "回", "场", "根", "面", "句", "通", "声", "瓶", "支", "首", 
    "张", "口", "大", "小", "点", "节", "些", "位", "辈", "手", "阵", "段", "会儿", "分钟", "小时", "半天",
    "一", "二", "两", "三", "四", "五", "六", "七", "八", "九", "十", "百", "千", "万",
    "他", "你", "我", "她", "它", "谁", "自己", "大家", "人家",
    "都", "也", "又", "还", "在", "从", "对", "向", "往", "跟", "和", "与", "被", "把", "给", "让", 
    "吗", "呢", "吧", "啊", "，", "。", "？", "！", "很", "非常", "太", "特", "特别", "挺"
])

# --- HanLP 模型加载 ---
try:
    print("正在加载 HanLP 模型，这可能需要一次下载...")
    tokenizer = hanlp.load(hanlp.pretrained.mtl.UD_ONTONOTES_TOK_POS_LEM_FEA_NER_SRL_DEP_SDP_CON_XLMR_BASE)
    print("HanLP 模型加载完成。")
except Exception as e:
    print(f"❌ HanLP 加载失败: {e}")
    sys.exit(1)

# --- 辅助函数：FST 输入归一化 ---
def normalize_text_for_fst(text):
    """将非 FST 知识库中的字替换为安全占位符 '某'。"""
    chars = []
    for char in text:
        if char in FST_KEYWORDS:
            chars.append(char)
        else:
            chars.append("某") 
    return "".join(chars)

# --- 辅助函数：FST 验证调用 ---
def validate_middle_field(tagged_input, fst_binary_path):
    """调用 HFST 验证归一化后的带标签输入。"""
    if not tagged_input or ":" not in tagged_input: return True
    
    try:
        process = subprocess.Popen(
            ['hfst-lookup', '-q', fst_binary_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate(input=tagged_input + "\n")
        
        if "+?" in stdout or "inf" in stdout or not stdout.strip():
            return False
        return True

    except Exception as e:
        print(f"HFST Runtime Error: 请确保 hfst-lookup 在 PATH 中. Error: {e}")
        return False

# --- 辅助函数：词汇分流逻辑 (FST_Class Track Assignment) ---
def get_fst_class(lemma, l_type):
    """根据词条名和类型，返回 FST 验证赛道标签 (Loose, Object, Poss, Idiom)。"""
    # 类别优先级: Specific > Strict > Idiom/Simplex > Loose
    
    # [POSS] 强制领属
    if lemma in ["生气", "捣乱", "操心", "担心", "灰心", "动心", "死心", "伤心", "领情", "革命", "造反"]:
        return "POSS"
    
    # [OBJECT] 允许直宾
    if lemma in ["帮忙", "吃醋"]:
        return "OBJECT"
    
    # [IDIOM] 僵化/特殊结构 (重叠词、特殊动词)
    if lemma in ["见面", "散步", "把脉", "握手", "鞠躬", "敬礼", "出恭", "将军", "幽默", "滑稽", "慷慨", "小便", "大便", "军训", "体检", "同学", "暂停", "学习"]:
        return "IDIOM"
        
    # [LOOSE] 默认标准动宾
    return "LOOSE"


# ==============================================================================
# 3. 核心检测与评测循环
# ==============================================================================
def run_hybrid_detector():
    print(f"[Init] Loading Lexicon from {INPUT_CSV}...")
    try:
        df = pd.read_csv(INPUT_CSV, sep=None, engine='python')
        df.columns = [c.strip() for c in df.columns] 
    except:
        print(f"Error: 找不到 {INPUT_CSV}")
        return
        
    print(f"[Run] Processing {TEST_FILE}...")
    total = 0; passed = 0
    
    # 确保 FST 文件存在于当前目录
    if not os.path.exists(HFST_PATH):
        print(f"❌ 错误: 找不到 FST 文件 '{HFST_PATH}'。请先编译！")
        return

    with open(TEST_FILE, "r", encoding="utf-8") as f_in, \
         open(OUTPUT_REPORT, "w", encoding="utf-8") as f_out:
        
        # 写入报告头
        f_out.write("TEST REPORT | Hybrid FST & Python Engine\n")
        f_out.write("==================================================\n")
        f_out.write(f"{'Target':<6} | {'Status':<5} | {'Detected':<5} | {'Class':<8} | Reason\n")
        f_out.write("-" * 70 + "\n")

        # 缓存词典规则和分流类型
        rules_map = {row['Lemma']: {'A': row['A'], 'B': row['B'], 'Class': get_fst_class(row['Lemma'], row['Type'])} for idx, row in df.iterrows()}
        
        lines = f_in.readlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"): continue
            
            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 3: continue

            target_lemma = parts[0]
            sentence = parts[1]
            expect_true = (parts[2].lower() == "true")
            
            if target_lemma not in rules_map: continue # 跳过词典里没有的词
            
            rule = rules_map[target_lemma]
            char_a = rule['A']
            char_b = rule['B']
            fst_class = rule['Class'] # 获取 FST 赛道
            
            # --- 主检测流程 ---
            detected, reason = _perform_detection(sentence, char_a, char_b, fst_class, HFST_PATH)
            
            # --- 结果记录 ---
            status = "PASS" if detected == expect_true else "FAIL"
            
            if status == "PASS": passed += 1
            total += 1
            
            f_out.write(f"{target_lemma:<6} | {status:<5} | {str(detected):<5} | {fst_class:<8} | {reason}\n")
            
            if status == "FAIL":
                print(f"FAIL on {target_lemma}: {sentence} -> {reason}")
                
        f_out.write(f"\n\nSUMMARY: {passed}/{total} Passed ({passed/total*100:.2f}%)")
    
    print(f"\n[Done] Check {OUTPUT_REPORT}")
    print(f"Accuracy: {passed/total*100:.2f}%")

# --- 私有检测函数 (调用 FST 验证) ---
def _perform_detection(sentence, target_A, target_B, fst_class, hfst_path):
    """封装了 FST 检查的单句检测逻辑"""
    doc = tokenizer(sentence)
    tokens = doc.get('tok', doc.get('tok/fine', []))
    
    a_indices = [i for i, t in enumerate(tokens) if target_A in t]
    b_indices = [i for i, t in enumerate(tokens) if target_B in t]
    
    for i_a in a_indices:
        for i_b in b_indices:
            if i_b <= i_a: continue 
            
            # 提取 (Morphology Extraction - 弹性提取)
            token_a_str = tokens[i_a]; parts_a = token_a_str.split(target_A, 1)
            suffix_a = parts_a[1] if len(parts_a) > 1 else ""
            token_b_str = tokens[i_b]; parts_b = token_b_str.split(target_B, 1)
            prefix_b = parts_b[0] if len(parts_b) > 0 else ""
            middle_str = "".join(tokens[i_a+1 : i_b])
            full_middle_field = suffix_a + middle_str + prefix_b
            
            # 快速检查 (Reduplication / Zero Insertion)
            if not full_middle_field:
                return True, "Zero Insertion"
            if full_middle_field == target_A or full_middle_field == "一" + target_A:
                return True, f"Reduplication: {full_middle_field}"

            # FST 结构验证 (Validation)
            normalized_middle = normalize_text_for_fst(full_middle_field)
            fst_input_tagged = f"{fst_class}:{normalized_middle}"
            
            is_valid = validate_middle_field(fst_input_tagged, hfst_path)
            
            if is_valid:
                return True, f"FST Validated: [{full_middle_field}]"
            
    return False, "No valid structure found"

if __name__ == "__main__":
    run_hybrid_detector()