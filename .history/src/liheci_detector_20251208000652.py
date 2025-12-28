import hanlp
import subprocess
import os

# ==============================================================================
# 1. 初始化模型
# ==============================================================================
print("正在加载 HanLP 模型，请稍候...")
# 加载通用模型
tokenizer = hanlp.load(hanlp.pretrained.mtl.UD_ONTONOTES_TOK_POS_LEM_FEA_NER_SRL_DEP_SDP_CON_XLMR_BASE)
print("HanLP 模型加载完成。")

# ==============================================================================
# 2. FST 关键词白名单 (The Knowledge Base)
# ==============================================================================
# 必须与 middle_grammar.xfst 里的定义保持完全一致！
# 只有这些字会原样传给 FST，其他的字都会变成 "_M_"
FST_KEYWORDS = set([
    # Asp
    "了", "着", "过",
    # De
    "的", "之",
    # Comp / Poten
    "完", "好", "到", "见", "错", "坏", "死", "透", "上", "下", "起", "出", "回", "开", "得", "不",
    # Cl (量词)
    "个", "次", "顿", "把", "天", "年", "回", "场", "根", "面", "句", "通", "声", "瓶", "支", "首", 
    "张", "口", "大", "小", "点", "节", "些", "位", "辈", "手", "阵", "段", "会儿", "分钟", "小时", "半天",
    # Num
    "一", "二", "两", "三", "四", "五", "六", "七", "八", "九", "十", "半", "几", "百", "千", "万",
    # Pron
    "他", "你", "我", "她", "它", "谁", "自己", "大家", "人家",
    # Forbidden (必须要保留原字，以便 FST 能够识别并拒绝它们)
    "都", "也", "又", "还", "在", "从", "对", "向", "往", "跟", "和", "与", "被", "把", "给", "让", 
    "吗", "呢", "吧", "啊", "，", "。", "？", "！"
])

def normalize_text_for_fst(text):
    """
    将未登录词转换为通用占位符 "_M_"
    输入: "洗了个热水澡" -> 中间: "了个热水"
    输出: "了" (Known) + "个" (Known) + "_M_" (Unknown) + "_M_" (Unknown) -> "了个_M__M_"
    """
    chars = []
    for char in text:
        if char in FST_KEYWORDS:
            chars.append(char)
        else:
            chars.append("_M_") # 将未知字归一化为 Modifier
    return "".join(chars)

# ==============================================================================
# 3. FST 验证工具
# ==============================================================================
def validate_middle_field(text, fst_binary_path):
    if not text: return True
    
    if not os.path.exists(fst_binary_path):
        print(f"Error: FST file missing: {fst_binary_path}")
        return False

    # [关键步骤] 1. 归一化输入
    normalized_input = normalize_text_for_fst(text)

    try:
        process = subprocess.Popen(
            ['hfst-lookup', '-q', fst_binary_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # [关键步骤] 2. 必须加换行符 \n，否则 hfst-lookup 会卡住或忽略
        stdout, stderr = process.communicate(input=normalized_input + "\n")
        
        # 调试信息：如果 FAIL 了，看看 FST 到底说了啥
        # print(f"DEBUG: Input='{normalized_input}' -> Output='{stdout.strip()}'")

        if "+?" in stdout or "inf" in stdout or not stdout.strip():
            return False
        return True

    except Exception as e:
        print(f"HFST Error: {e}")
        return False

# ==============================================================================
# 4. 核心检测逻辑
# ==============================================================================
def check_liheci_smart(sentence, target_A, target_B, hfst_path):
    doc = tokenizer(sentence)
    tokens = doc.get('tok', doc.get('tok/fine', []))
    
    a_indices = [i for i, t in enumerate(tokens) if target_A in t]
    b_indices = [i for i, t in enumerate(tokens) if target_B in t]
    
    for i_a in a_indices:
        for i_b in b_indices:
            if i_b < i_a: continue 
            
            token_a_str = tokens[i_a]
            token_b_str = tokens[i_b]
            
            # 形态学提取
            parts_a = token_a_str.split(target_A, 1)
            suffix_a = parts_a[1] if len(parts_a) > 1 else ""
            parts_b = token_b_str.split(target_B, 1)
            prefix_b = parts_b[0] if len(parts_b) > 0 else ""
            middle_tokens = tokens[i_a+1 : i_b]
            middle_str = "".join(middle_tokens)
            
            full_middle_field = suffix_a + middle_str + prefix_b
            
            # 重叠词检查
            if full_middle_field == target_A:
                return True, f"Reduplication: {full_middle_field}"

            # FST 验证
            is_valid = validate_middle_field(full_middle_field, hfst_path)
            
            if is_valid:
                return True, f"Insertion: [{full_middle_field}]"
            
    return False, "No valid structure found"