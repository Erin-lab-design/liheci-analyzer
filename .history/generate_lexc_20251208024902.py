import pandas as pd
import sys
import io

OUTPUT_FILE = "liheci.lexc"

# ... (初始化和符号收集，保持不变)
all_symbols = [
    "+V/O", "+V_VV", "+V_MOD", "+V_PSEUDO", "+T_NN", "+T_MOD", 
    "^SEP", "+Masc", "+Fem", "+Neut", "+Sg", "+Pl", "+Du", "+Subj", "+Norm"
]
vocab_ids = []
# ... (加载 CSV 和收集 vocab_ids 保持不变) ...

try:
    df = pd.read_csv("liheci_lexicon.csv", sep=None, engine='python')
    df.columns = [c.strip() for c in df.columns]
except Exception as e:
    print(f"❌ Error loading CSV: {e}")
    sys.exit(1)

for index, row in df.iterrows():
    vocab_id = f"@V{index+1}@" 
    vocab_ids.append(vocab_id)
all_symbols.extend(vocab_ids)


# ============================================================
# 2. FST 头部定义 (修复换行符问题)
# ============================================================
# 注意: 去掉了 header 字符串中的 \n 
lexc_header = f"""
!!! liheci.lexc - MORPHOLOGICAL LEXICON !!!

Multichar_Symbols 
    {' '.join(all_symbols)}
! ------------------------------------------------------------------
"""

# ============================================================
# 3. 核心生成逻辑 (修复 Lexicon 块定义)
# ============================================================
# 我们将 LEXICON Root 块定义为连续的字符串
lexc_root = "LEXICON Root\n"
lexc_split_path = "LEXICON SplitPath\n"
lexc_whole_path = "LEXICON WholePath\n"
lexc_split_end = "LEXICON SplitEnd\n"
lexc_split_end_sep = "LEXICON SplitEndSep\n"
lexc_end = "LEXICON End\n    +V/O:0 # ;\n"


for index, row in df.iterrows():
    # ... (词条生成逻辑保持不变)
    lemma = str(row.get('Lemma', '')).strip()
    head = str(row.get('A', '')).strip()
    tail = str(row.get('B', '')).strip()
    l_type = str(row.get('Type', ''))
    
    vocab_id = f"@V{index+1}@" 
    
    is_pseudo = "Pseudo" in l_type or "Simplex" in l_type
    is_mod = "Modifier" in l_type
    
    head_tag = "+V_VV"
    if is_mod:
        head_tag = "+V_MOD" 
    elif is_pseudo:
        head_tag = "+V_PSEUDO"

    lexc_root += f'    {vocab_id}:0 SplitPath ;\n' 
    lexc_root += f'    {vocab_id}:0 WholePath ;\n' 
    
    lexc_split_path += f'    {head} {head_tag} SplitEndSep ;\n'
    
    lexc_whole_path += f'    {lemma} +V/O End ;\n'

    if index == 0:
        lexc_split_end_sep += f'    ^SEP SplitEnd ;\n'
    
    tail_tag = "+T_NN" 
    lexc_split_end += f'    {tail} {tail_tag} End ;\n'


# 4. 组装最终内容 (移除分隔换行，确保 Lexicon 块紧密相连)
full_content = (
    lexc_header + 
    lexc_root +
    lexc_split_path +
    lexc_whole_path +
    lexc_split_end_sep +
    lexc_split_end +
    lexc_end
)

# 5. 写入文件
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(full_content)
print(f"✅ Generated {OUTPUT_FILE}. Now attempt compilation.")