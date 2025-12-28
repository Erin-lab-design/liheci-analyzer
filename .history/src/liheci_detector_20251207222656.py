import hanlp
import subprocess
import os

# 初始化 HanLP (只加载一次)
tokenizer = hanlp.load(hanlp.pretrained.mtl.CLOSE_TOK_POS_NER_SRP_PAX_S_PKU_ZH)

def validate_with_hfst(middle_text, hfst_path):
    """
    将提取出来的中间文本传给 FST 进行验证
    """
    # 如果中间为空，说明是紧密结合 (e.g. 吃饭)，也是合法的
    if not middle_text:
        return True
        
    try:
        # 调用命令行工具 hfst-lookup
        # 输入: middle_text, 模型: hfst_path
        process = subprocess.Popen(
            ['hfst-lookup', '-q', hfst_path], # -q quiet mode
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 发送字符串给 FST
        stdout, stderr = process.communicate(input=middle_text)
        
        # hfst-lookup 的输出格式通常是: "input_string\tanalysis\tweight"
        # 如果匹配失败，analysis 通常是 input_string + "+?" 或者根本没有输出
        # 我们检查输出中是否包含 "+?" (表示未识别) 
        # 或者直接看是否有有效输出，这取决于你的 hfst-lookup 版本行为
        
        if "+?" in stdout or "inf" in stdout: 
            return False
        
        # 如果有输出且没有错误标记，通常意味着 Match Success
        # 更严谨的检查：看输出是否非空
        if stdout.strip():
            return True
            
        return False
        
    except Exception as e:
        print(f"FST Error: {e}")
        return False

def check_liheci_smart(sentence, target_A, target_B, hfst_path):
    """
    主检测函数
    """
    doc = tokenizer(sentence)
    tokens = doc['tok/pku']
    
    # 寻找 A 和 B 的宿主 Token
    a_indices = [i for i, t in enumerate(tokens) if target_A in t]
    b_indices = [i for i, t in enumerate(tokens) if target_B in t]
    
    for i_a in a_indices:
        for i_b in b_indices:
            if i_b < i_a: continue 
            
            # --- 核心提取逻辑 (Morphology Extraction) ---
            token_a_str = tokens[i_a]
            token_b_str = tokens[i_b]
            
            # 1. 提取 A 的后缀
            parts_a = token_a_str.split(target_A, 1)
            suffix_a = parts_a[1] if len(parts_a) > 1 else ""
            
            # 2. 提取 B 的前缀
            parts_b = token_b_str.split(target_B, 1)
            prefix_b = parts_b[0] if len(parts_b) > 0 else ""
            
            # 3. 提取中间 Tokens
            middle_tokens = tokens[i_a+1 : i_b]
            middle_str = "".join(middle_tokens)
            
            # 4. 组装 Middle Field
            full_middle_field = suffix_a + middle_str + prefix_b
            
            # --- 重叠词特判 (散散步) ---
            if full_middle_field == target_A:
                return True, f"Reduplication: {full_middle_field}"

            # --- FST 校验 ---
            # 必须传入编译好的 .hfst 文件的绝对路径
            is_valid = validate_with_hfst(full_middle_field, hfst_path)
            
            if is_valid:
                return True, f"Insertion: [{full_middle_field}]"
            
    return False, "No valid structure"