import pandas as pd
import sys

OUTPUT_FILE = "liheci.lexc"

# ============================================================
# 1. FST 头部
# ============================================================
lexc_header = """!!! liheci.lexc - REAL HFST LOGIC !!!
! 本文件包含正则语法和 Flag Diacritics。
! 逻辑完全由 HFST 引擎处理，Python 只负责生成这个定义文件。

Multichar_Symbols 
    @P.VO.START@ @R.VO.END@ 
    /VV /NN /AS /CD /PN /DEG /DEC /AD /VA /P /JJ /PU /NR /M /OD

LEXICON Root
    ! 入口：FST 同时尝试匹配 "离散路径" 和 "融合路径"
    < 0 > SplitPath ;
    < 0 > WholePath ;
"""

# ============================================================
# 2. 中间域 (使用 HFST 正则语法)
# ============================================================
lexc_middle = """
LEXICON MiddleField
    ! 允许插入常见的中间成分
    ! 语法 < ... > 是 HFST 的正则嵌入
    < ?* "/AS" >  MiddleField ;
    < ?* "/PN" >  MiddleField ;
    < ?* "/CD" >  MiddleField ;
    < ?* "/M" >   MiddleField ;
    < ?* "/JJ" >  MiddleField ;
    < ?* "/DEG" > MiddleField ;
    < ?* "/AD" >  MiddleField ;
    < ?* "/VV" >  MiddleField ; 
    < ?* "/NN" >  MiddleField ; 
    
    ! 0:0 允许 A和B 紧邻 (Zero Insertion)
    0:0     SuffixCheck ;
"""

try:
    df = pd.read_csv("liheci_lexicon.csv", sep=None, engine='python')
    df.columns = [c.strip() for c in df.columns]
    print(f"✅ Loaded {len(df)} entries.")
except Exception as e:
    print(f"❌ Error: {e}")
    exit()

# ============================================================
# 3. 核心生成逻辑
# ============================================================
lexc_split = "LEXICON SplitPath\n"
lexc_suffix = "LEXICON SuffixCheck\n"
lexc_whole = "LEXICON WholePath\n"

for index, row in df.iterrows():
    lemma = str(row.get('Lemma', '')).strip()
    head = str(row.get('A', '')).strip()
    tail = str(row.get('B', '')).strip()
    l_type = str(row.get('Type', ''))
    
    flag_p = f"@P.VO.{index}@"
    flag_r = f"@R.VO.{index}@"
    
    is_pseudo = "Pseudo" in l_type or "Simplex" in l_type
    is_mod = "Modifier" in l_type
    is_standard = not (is_pseudo or is_mod)

    # ----------------------------------------------------
    # Path A: SplitPath (离散态)
    # ----------------------------------------------------
    # 这里我们把逻辑写入 FST 文件：
    # 1. 必须包含 Head 字符
    # 2. 必须符合 Tag 约束
    
    if is_standard:
        # Standard VO: 必须是 /VV
        # 正则含义: 任意前缀 + Head字符 + 任意中缀 + /VV标签
        lexc_split += f'    < ?* "{head}" ?* "/VV" > {flag_p} MiddleField ; \n'
        
    elif is_mod:
        # Mod-Head: 允许 /NN, /AD, /JJ, /VV
        lexc_split += f'    < ?* "{head}" ?* "/NN" > {flag_p} MiddleField ; \n'
        lexc_split += f'    < ?* "{head}" ?* "/AD" > {flag_p} MiddleField ; \n'
        lexc_split += f'    < ?* "{head}" ?* "/JJ" > {flag_p} MiddleField ; \n'
        lexc_split += f'    < ?* "{head}" ?* "/VV" > {flag_p} MiddleField ; \n' 
        
    elif is_pseudo:
        # Pseudo: 允许 VV, VA, NN
        lexc_split += f'    < ?* "{head}" ?* "/VV" > {flag_p} MiddleField ; \n'
        lexc_split += f'    < ?* "{head}" ?* "/VA" > {flag_p} MiddleField ; \n'
        lexc_split += f'    < ?* "{head}" ?* "/NN" > {flag_p} MiddleField ; \n'

    # Tail 生成
    # 正则含义: 只要包含 Tail 字符，且 Tag 是 NN 或 VV 都可以
    lexc_suffix += f'    < ?* "{tail}" ?* "/NN" > {flag_r} End ; \n'
    lexc_suffix += f'    < ?* "{tail}" ?* "/VV" > {flag_r} End ; \n'
    if is_pseudo or is_mod:
        lexc_suffix += f'    < ?* "{tail}" ?* "/VA" > {flag_r} End ; \n'

    # ----------------------------------------------------
    # Path B: WholePath (融合态)
    # ----------------------------------------------------
    # 基础形式 (Lemma)
    lexc_whole += f'    <{lemma} "/VV"> End ; \n'
    lexc_whole += f'    <{lemma} "/NN"> End ; \n'
    
    # 重叠形式 (AAB) - 仅限 VO
    if is_standard:
        aab = f"{head}{head}{tail}"
        lexc_whole += f'    <{aab} "/VV"> End ; \n'
        lexc_whole += f'    <{aab} "/NN"> End ; \n'
        
        # AABB
        aabb = f"{head}{head}{tail}{tail}"
        lexc_whole += f'    <{aabb} "/VV"> End ; \n'
        
        # A一AB (如果 HanLP 没切开)
        a1ab = f"{head}一{head}{tail}"
        lexc_whole += f'    <{a1ab} "/VV"> End ; \n'

# 4. 组装
full_content = (
    lexc_header + "\n" +
    lexc_split + "\n" +
    lexc_middle + "\n" +
    lexc_suffix + "\n" +
    lexc_whole + "\n" +
    "LEXICON End\n    +Liheci:0 # ;\n"
)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(full_content)
print(f"✅ Generated {OUTPUT_FILE} (Logic encoded in FST Regex & Flags).")