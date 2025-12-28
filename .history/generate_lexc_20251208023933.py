import pandas as pd
import sys
import io

OUTPUT_FILE = "liheci.lexc"

# ============================================================
# 1. 初始化和符号收集
# ============================================================
all_symbols = [
    "+V/O", "+V_VV", "+V_MOD", "+V_PSEUDO", "+T_NN", "+T_MOD", 
    "^SEP", "+Masc", "+Fem", "+Neut", "+Sg", "+Pl", "+Du", "+Subj", "+Norm"
]
vocab_ids = []

try:
    df = pd.read_csv("liheci_lexicon.csv", sep=None, engine='python')
    df.columns = [c.strip() for c in df.columns]
    print(f"✅ Loaded {len(df)} entries.")
except Exception as e:
    print(f"❌ Error loading CSV: {e}")
    sys.exit(1)

# 收集所有词汇 ID
for index, row in df.iterrows():
    vocab_id = f"@V{index+1}@" 
    vocab_ids.append(vocab_id)
all_symbols.extend(vocab_ids)

# ============================================================
# 2. FST 头部定义
# ============================================================
lexc_header = f"""
!!! liheci.lexc - MORPHOLOGICAL LEXICON !!!

Multichar_Symbols 
    {' '.join(all_symbols)}
"""

# ============================================================
# 3. 核心生成逻辑
# ============================================================
lexc_root = "LEXICON Root\n"
lexc_split_path = "LEXICON SplitPath\n"
lexc_whole_path = "LEXICON WholePath\n"
lexc_end = "LEXICON End\n    +V/O:0 # ;\n"
lexc_split_end = "LEXICON SplitEnd\n"
lexc_split_end_sep = "LEXICON SplitEndSep\n"


for index, row in df.iterrows():
    lemma = str(row.get('Lemma', '')).strip()
    head = str(row.get('A', '')).strip()
    tail = str(row.get('B', '')).strip()
    l_type = str(row.get('Type', ''))
    
    vocab_id = f"@V{index+1}@" 
    
    is_pseudo = "Pseudo" in l_type or "Simplex" in l_type
    is_mod = "Modifier" in l_type
    
    # --- A. Root (入口) ---
    # FST 从 Root 词典开始，将抽象的 ID 加入到词汇路径上
    lexc_root += f'    {vocab_id}:0 SplitPath ;\n' 
    lexc_root += f'    {vocab_id}:0 WholePath ;\n' 
    
    # --- B. SplitPath (离散形态：高分实现的关键) ---
    
    head_tag = "+V_VV"
    if is_mod:
        head_tag = "+V_MOD" 
    elif is_pseudo:
        head_tag = "+V_PSEUDO"

    # FST 词汇层：Head 字符 + A的形态要求 -> 分隔槽
    # 示例: 睡:+V_VV SplitEndSep ; 
    lexc_split_path += f'    {head}:{head} {head_tag} SplitEndSep ;\n'
    
    # --- C. WholePath (融合形态) ---
    # 示例: 睡觉:+V/O End ; 
    lexc_whole_path += f'    {lemma}:{lemma} +V/O End ;\n'

    # --- D. 分隔槽和 B_Tail 定义 ---
    
    # Separator (分隔符)： A 后面跟着一个抽象的分隔符 ^SEP
    lexc_split_end_sep += f'    ^SEP:^SEP SplitEnd ;\n'
    
    # Tail 定义：分隔符后面跟着 B_tail 字符 + B的形态要求
    tail_tag = "+T_NN" 
    lexc_split_end += f'    {tail}:{tail} {tail_tag} End ;\n'

# 4. 组装最终内容
full_content = (
    lexc_header + "\n" +
    "LEXICON Root\n" + lexc_root + "\n" +
    "LEXICON SplitPath\n" + lexc_split_path + "\n" +
    "LEXICON WholePath\n" + lexc_whole_path + "\n" +
    "LEXICON SplitEndSep\n" + lexc_split_end_sep + "\n" +
    "LEXICON SplitEnd\n" + lexc_split_end + "\n" +
    lexc_end
)

# 5. 写入文件
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(full_content)
print(f"✅ Generated {OUTPUT_FILE}. Now compile with hfst-xfst.")