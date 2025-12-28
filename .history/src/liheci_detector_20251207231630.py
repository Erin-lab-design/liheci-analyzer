import hanlp
import subprocess
import os

# ==============================================================================
# 1. 初始化模型 (Global Initialization)
# ==============================================================================
# 加载 HanLP 模型 (只加载一次，节省时间)
# 使用 PKU 标准，比较稳健
print("正在加载 HanLP 模型，请稍候...")
tokenizer = hanlp.load(hanlp.pretrained.mtl.UD_ONTONOTES_TOK_POS_LEM_FEA_NER_SRL_DEP_SDP_CON_XLMR_BASE)
print("HanLP 模型加载完成。")

# ==============================================================================
# 2. FST 验证工具 (Helper Function)
# ==============================================================================
def validate_middle_field(text, fst_binary_path):
    """
    调用 HFST 二进制文件验证中间文本是否合法。
    
    Args:
        text (str): 提取出来的中间域文本 (e.g. "了个热水")
        fst_binary_path (str): .hfst 文件的绝对路径
        
    Returns:
        bool: True if valid, False if rejected
    """
    # 规则1: 如果中间是空的 (e.g. "吃饭", "睡觉")，直接合法
    if not text: 
        return True

    # 规则2: 检查 FST 文件是否存在
    if not os.path.exists(fst_binary_path):
        print(f"Error: FST file not found at {fst_binary_path}")
        return False

    try:
        # 调用 hfst-lookup (静默模式 -q)
        # 输入: text -> 标准输入 (stdin)
        # 输出: result -> 标准输出 (stdout)
        process = subprocess.Popen(
            ['hfst-lookup', '-q', fst_binary_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=text)
        
        # hfst-lookup 的输出判定逻辑：
        # 失败情况 1: 输出中包含 "+?" (表示输入未被 FST 接受)
        # 失败情况 2: 输出中包含 "inf" (无限权重，通常意味着失败)
        # 失败情况 3: 没有任何输出
        if "+?" in stdout or "inf" in stdout or not stdout.strip():
            return False
            
        # 如果有正常输出且没有错误标记，说明匹配成功
        return True

    except Exception as e:
        print(f"HFST Runtime Error: {e}")
        return False

# ==============================================================================
# 3. 核心检测逻辑 (Main Logic)
# ==============================================================================
def check_liheci_smart(sentence, target_A, target_B, hfst_path):
    """
    智能离合词检测主函数
    包含：Token扫描 -> 形态学提取 -> 重叠词检查 -> FST验证
    
    Args:
        sentence (str): 待检测句子
        target_A (str): 离合词前半部分 (e.g. "洗")
        target_B (str): 离合词后半部分 (e.g. "澡")
        hfst_path (str): FST 模型路径
        
    Returns:
        tuple: (Is_Detected (bool), Reason (str))
    """
    
    # 1. 运行分词
    doc = tokenizer(sentence)
    tokens = doc['tok/pku']
    
    # 2. 寻找 A 和 B 的宿主 Token (Host Token)
    # 比如 "我洗了个热水澡" -> Tokens: ["我", "洗", "了", "个", "热水澡"]
    # A="洗" 在 token[1] ("洗")
    # B="澡" 在 token[4] ("热水澡")
    a_indices = [i for i, t in enumerate(tokens) if target_A in t]
    b_indices = [i for i, t in enumerate(tokens) if target_B in t]
    
    # 双重循环寻找匹配对 (A 必须在 B 前面)
    for i_a in a_indices:
        for i_b in b_indices:
            if i_b < i_a: continue 
            
            # --- [Step 3: 形态学提取 (Morphology Extraction)] ---
            # 这是处理 "热水澡" 被分在一起的关键步骤
            
            token_a_str = tokens[i_a]
            token_b_str = tokens[i_b]
            
            # Part 1: A 的后缀 (Suffix of A)
            # 如果 token 是 "吃完", A="吃", Suffix="完"
            parts_a = token_a_str.split(target_A, 1)
            suffix_a = parts_a[1] if len(parts_a) > 1 else ""
            
            # Part 2: B 的前缀 (Prefix of B)
            # 如果 token 是 "热水澡", B="澡", Prefix="热水"
            parts_b = token_b_str.split(target_B, 1)
            prefix_b = parts_b[0] if len(parts_b) > 0 else ""
            
            # Part 3: 中间的完整 Tokens
            middle_tokens = tokens[i_a+1 : i_b]
            middle_str = "".join(middle_tokens)
            
            # 组装最终的 Middle Field
            full_middle_field = suffix_a + middle_str + prefix_b
            
            # --- [Step 4: 快速检查 - 重叠词 (Reduplication)] ---
            # 处理 "散散步" (A=散, Middle=散) 或 "高高兴兴" (Middle=高兴)
            if full_middle_field == target_A:
                return True, f"[Reduplication AAB] Pattern: {token_a_str}...{token_b_str}"
            
            # --- [Step 5: 深度检查 - HFST 验证] ---
            # 将提取出的纯净中间域扔给 FST
            is_valid = validate_middle_field(full_middle_field, hfst_path)
            
            if is_valid:
                return True, f"[FST Validated] Insert: [{full_middle_field}]"
            else:
                # 如果你想调试，可以把这里改为 print，但在最终报告里只要 return False
                # print(f"DEBUG: Rejected middle field: {full_middle_field}")
                pass
            
    return False, "No valid structure found"