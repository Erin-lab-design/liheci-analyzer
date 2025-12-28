import hanlp
import subprocess
import os
import pandas as pd

# ==============================================================================
# 1. 初始化模型与 FST 知识库
# ==============================================================================
print("正在加载 HanLP 模型，请稍候...")
# 使用通用的多任务模型
tokenizer = hanlp.load(hanlp.pretrained.mtl.UD_ONTONOTES_TOK_POS_LEM_FEA_NER_SRL_DEP_SDP_CON_XLMR_BASE)
print("HanLP 模型加载完成。")

# FST 关键词白名单 (与 middle_grammar.xfst 保持同步)
FST_KEYWORDS = set([
    "了", "着", "过", "的", "之", "完", "好", "到", "见", "错", "坏", "死", "透", "上", "下", "起", "出", "回", "开", 
    "得", "不", "个", "次", "顿", "把", "天", "年", "回", "场", "根", "面", "句", "通", "声", "瓶", "支", "首", 
    "张", "口", "大", "小", "点", "节", "些", "位", "辈", "手", "阵", "段", "会儿", "分钟", "小时", "半天",
    "一", "二", "两", "三", "四", "五", "六", "七", "八", "九", "十", "百", "千", "万",
    "他", "你", "我", "她", "它", "谁", "自己", "大家", "人家",
    "都", "也", "又", "还", "在", "从", "对", "向", "往", "跟", "和", "与", "被", "把", "给", "让", 
    "吗", "呢", "吧", "啊", "，", "。", "？", "！", "很", "非常", "太", "特", "特别", "挺" # 程度副词也需要保留原字
])

def normalize_text_for_fst(text):
    """将非 FST 知识库中的字替换为安全占位符 '某'。"""
    chars = []
    for char in text:
        if char in FST_KEYWORDS:
            chars.append(char)
        else:
            chars.append("某") 
    return "".join(chars)

def validate_middle_field(tagged_input, fst_binary_path):
    """调用 HFST 验证归一化后的带标签输入。"""
    if not tagged_input or ":" not in tagged_input: return True # 空或无标签，默认放行
    
    try:
        process = subprocess.Popen(
            ['hfst-lookup', '-q', fst_binary_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 必须加换行符 \n
        stdout, stderr = process.communicate(input=tagged_input + "\n")
        
        if "+?" in stdout or "inf" in stdout or not stdout.strip():
            return False
        return True

    except Exception as e:
        print(f"HFST Error: {e}")
        return False

def check_liheci_smart(sentence, target_A, target_B, fst_class, hfst_path):
    """主检测函数，加入 FST 分流逻辑。"""
    
    # 1. 运行 HanLP 分词
    doc = tokenizer(sentence)
    tokens = doc.get('tok', doc.get('tok/fine', []))
    
    # 2. 锚定 (Anchoring)
    a_indices = [i for i, t in enumerate(tokens) if target_A in t]
    b_indices = [i for i, t in enumerate(tokens) if target_B in t]
    
    for i_a in a_indices:
        for i_b in b_indices:
            if i_b <= i_a: continue 
            
            # 3. 形态学提取 (Extraction)
            token_a_str = tokens[i_a]
            parts_a = token_a_str.split(target_A, 1)
            suffix_a = parts_a[1] if len(parts_a) > 1 else ""
            
            token_b_str = tokens[i_b]
            parts_b = token_b_str.split(target_B, 1)
            prefix_b = parts_b[0] if len(parts_b) > 0 else ""
            
            middle_str = "".join(tokens[i_a+1 : i_b])
            full_middle_field = suffix_a + middle_str + prefix_b
            
            # 4. 快速检查 (Reduplication / Zero Insertion)
            if not full_middle_field:
                return True, "Zero Insertion"
            if full_middle_field == target_A or full_middle_field == "一" + target_A:
                return True, f"Reduplication: {full_middle_field}"

            # 5. FST 结构验证 (Validation)
            normalized_middle = normalize_text_for_fst(full_middle_field)
            # 注入 Track 标签，例如: OBJECT:帮了他一个大
            fst_input_tagged = f"{fst_class}:{normalized_middle}"
            
            is_valid = validate_middle_field(fst_input_tagged, hfst_path)
            
            if is_valid:
                return True, f"FST Validated ({fst_class}): [{full_middle_field}]"
            
    return False, "No valid structure found"