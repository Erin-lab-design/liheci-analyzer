import pandas as pd
import os

def assign_fst_class(input_filename="liheci_lexicon.csv", output_filename="liheci_lexicon_classed.csv"):
    """
    根据离合词的特点和PPT中的规则颗粒度，自动分配FST验证赛道 (FST_Class)。
    
    Args:
        input_filename (str): 原始 CSV 文件名。
        output_filename (str): 输出带标签的 CSV 文件名。
    """
    
    print(f"Loading data from {input_filename}...")
    
    # --- 1. 数据加载与清理 ---
    try:
        # 使用 engine='python' 处理不规则分隔符，并清理列名
        df = pd.read_csv(input_filename, sep=None, engine='python')
        df.columns = [c.strip() for c in df.columns]
    except FileNotFoundError:
        print(f"❌ 错误: 找不到文件 {input_filename}。请确保文件在当前目录下。")
        return
    except Exception as e:
        print(f"❌ 错误: 读取文件失败，可能分隔符问题。请检查CSV格式。Error: {e}")
        return

    # --- 2. 核心分类字典 (基于语言学约束) ---
    # 类别优先级: Specific > Strict > Idiom/Simplex > Loose
    
    # [A] 强制领属 (POSS): 必须 '的' + 宾语 (Pron + De)
    # 心理/抽象 VO 且常带代词
    POSS_LIST = ["生气", "捣乱", "操心", "担心", "灰心", "动心", "死心", "伤心", "领情", "革命", "造反"]

    # [B] 允许直宾 (OBJECT): 允许直插代词 (帮他忙)
    OBJECT_LIST = ["帮忙", "吃醋"] 

    # [C] 特殊/僵化习语 (IDIOM): 严格限制插入 (AAB, 数量词)
    IDIOM_LIST = ["见面", "散步", "把脉", "握手", "鞠躬", "敬礼", 
                   "出恭", "将军", "幽默", "滑稽", "慷慨", 
                   "小便", "大便", "军训", "体检", "同学", "暂停",
                   "学习"] # 学习, 鞠躬, 幽默等都属于非常特殊的结构

    # --- 3. 标签分配逻辑 ---
    
    # 初始化新列
    df['FST_Class'] = 'LOOSE'
    
    # 1. 分配 POSSESSIVE (最严格的规则)
    df.loc[df['Lemma'].isin(POSS_LIST), 'FST_Class'] = 'POSS'
    
    # 2. 分配 OBJECT (次严格的规则)
    df.loc[df['Lemma'].isin(OBJECT_LIST), 'FST_Class'] = 'OBJECT'
    
    # 3. 分配 IDIOM (特殊僵化结构)
    df.loc[df['Lemma'].isin(IDIOM_LIST), 'FST_Class'] = 'IDIOM'
    
    # 4. Simplex/Pseudo-VO 特例处理 (如果它们不在 Idiom 列表里)
    df.loc[df.apply(lambda row: row['Type'].strip() in ['Simplex Word', 'Pseudo V-O', 'Modifier-Head'] and row['FST_Class'] == 'LOOSE', axis=1), 'FST_Class'] = 'IDIOM'
    
    # 5. LOOSE (默认/剩下的标准 VO) - 默认值已是 LOOSE
    
    # --- 4. 导出结果 ---
    
    # 检查 'FST_Class' 列是否成功创建和填充
    if 'FST_Class' in df.columns:
        df.to_csv(output_filename, index=False)
        print(f"✅ 标签分配完成。")
        print(f"文件已保存为 {output_filename}。请在运行 main.py 时使用此新文件。")
        print("\n--- 分配结果摘要 ---")
        print(df['FST_Class'].value_counts())
    else:
        print("❌ 内部错误：FST_Class 列创建失败。")

if __name__ == "__main__":
    assign_fst_class()