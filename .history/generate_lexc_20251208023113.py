import pandas as pd
import sys
import io

OUTPUT_FILE = "liheci.lexc"

# ============================================================
# 1. FST 头部定义
# ============================================================
lexc_header = """
!!! liheci.lexc - MORPHOLOGICAL LEXICON !!!
! 此文件定义连体词的词汇、词根、形态标签和抽象结构。
! 句法约束和插入逻辑在 liheci.xfst 中处理。

! Multichar Symbols: 
! +V/O: 表示这是一个连体词分析
! ^SEP: 抽象地标记 A 和 B 之间的分离点（插入槽）
! @Vxx@: 具体的词汇 ID，用于在转换层中验证 A-B 关联。

Multichar_Symbols 
    +V/O 
    ^SEP 
    +Masc +Fem +Neut +Sg +Pl +Du +Subj +Norm
    ! 具体的词汇ID将由脚本生成
"""

# ============================================================
# 2. 从 CSV 加载数据
# ============================================================
try:
    # 假设 liheci_lexicon.csv 在当前目录下
    df = pd.read_csv("liheci_lexicon.csv", sep=None, engine='python')
    df.columns = [c.strip() for c in df.columns]
    print(f"✅ Loaded {len(df)} entries.")
except Exception as e:
    print(f"❌ Error loading CSV: {e}")
    sys.exit(1)

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
    
    # 为每个连体词生成唯一的词汇ID标签
    vocab_id = f"@V{index+1}@" 
    
    is_pseudo = "Pseudo" in l_type or "Simplex" in l_type
    is_mod = "Modifier" in l_type
    
    # --- 写入 Root (入口) ---
    lexc_root += f'    < {vocab_id} > SplitPath ;\n'
    lexc_root += f'    < {vocab_id} > WholePath ;\n'
    
    # --- A. SplitPath (离散形态：高分实现的关键) ---
    
    # 1. 定义词汇层切分： A_head 字符 + 形态标签 + 分隔符
    # 2. **词性约束抽象化**：将词性要求编码为 Flag Diacritics 留给 .xfst 处理。
    # 词汇形式 : 词根形式 + 抽象标签 -> 下一个词典
    
    head_tag = "+V_VV"
    if is_mod:
        head_tag = "+V_MOD" # 允许 NN, AD, JJ, VV
    elif is_pseudo:
        head_tag = "+V_PSEUDO" # 允许 VV, VA, NN

    # FST 词汇层：A 字符 + A的形态要求 -> 分隔槽
    # 示例: 睡:+V_VV SplitEndSep ; 
    lexc_split_path += f'    {head}:{head} {head_tag} SplitEndSep ;\n'
    
    # --- B. WholePath (融合形态) ---
    # 示例: 睡觉:+V/O End ; 
    lexc_whole_path += f'    {lemma}:{lemma} +V/O End ;\n'

    # --- C. 分隔槽和 B_Tail 定义 ---
    
    # 1. Separator (分隔符)： A 后面跟着一个抽象的分隔符 ^SEP
    # SplitEndSep -> ^SEP SplitEnd
    lexc_split_end_sep += f'    ^SEP:^SEP SplitEnd ;\n'
    
    # 2. Tail 定义：分隔符后面跟着 B_tail 字符 + B的形态要求
    # 示例: SplitEnd -> 觉:+T_NN End ;
    tail_tag = "+T_NN" # 假设 Tail 默认为 NN，更复杂的应在 .xfst 中用规则触发。
    lexc_split_end += f'    {tail}:{tail} {tail_tag} End ;\n'

# 4. 组装最终内容
full_content = (
    lexc_header + "\n" +
    lexc_root + "\n" +
    lexc_split_path + "\n" +
    lexc_whole_path + "\n" +
    lexc_split_end_sep + "\n" +
    lexc_split_end + "\n" +
    lexc_end
)

# 5. 写入文件
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(full_content)
print(f"✅ Generated {OUTPUT_FILE}. Now proceed to liheci.xfst for rule implementation.")