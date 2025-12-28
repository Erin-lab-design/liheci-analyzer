# liheci_config.py
import pandas as pd

# ========================
# 统一配置
# ========================
DEFAULT_INPUT_CSV = "liheci_lexicon.csv"

def load_lexicon(csv_path: str = DEFAULT_INPUT_CSV):
    """
    读 CSV，返回 DataFrame。
    跟你 run_demo 里的逻辑一致。
    """
    try:
        df = pd.read_csv(csv_path, sep=None, engine='python')
        df.columns = [c.strip() for c in df.columns]
    except FileNotFoundError:
        print(f"Error: 找不到 {csv_path}")
        raise
    return df

def build_whole_path(df):
    """
    完全照你 run_demo 里构造 fst_whole_path 的逻辑写。
    返回 dict: surface_form -> lemma
    """
    fst_whole_path = {}

    for idx, row in df.iterrows():
        lemma = row['Lemma']
        head = row['A']
        tail = row['B']
        l_type = str(row.get('Type', ''))

        # 逻辑判断：类型分类 —— 完全照你原来的
        is_pseudo = "Pseudo" in l_type or "Simplex" in l_type
        is_mod = "Modifier" in l_type
        is_standard = not (is_pseudo or is_mod)

        # 1) 基础形式：lemma 本身
        fst_whole_path[lemma] = lemma

        # 2) 你当前版本里为“标准 VO”自动生成的形式
        # 👉 如果你日后决定某些 VO 不要 AAB / A一AB，
        #    可以在这里加条件（比如多读一列 Pattern）。
        if is_standard:
            fst_whole_path[f"{head}{head}{tail}"] = lemma        # AAB
            fst_whole_path[f"{head}{head}{tail}{tail}"] = lemma  # AABB
            fst_whole_path[f"{head}一{head}{tail}"] = lemma      # A一AB

    return fst_whole_path

def build_split_rules(df):
    """
    完全照你 run_demo 里构造 fst_split_rules 的逻辑写。
    返回一个 list[dict]，每个 dict 描述一个 lemma 的 split 规则。
    """
    fst_split_rules = []

    for idx, row in df.iterrows():
        lemma = row['Lemma']
        head = row['A']
        tail = row['B']
        l_type = str(row.get('Type', ''))

        # 类型分类逻辑：照抄你的
        is_pseudo = "Pseudo" in l_type or "Simplex" in l_type
        is_mod = "Modifier" in l_type
        is_standard = not (is_pseudo or is_mod)

        # Tag Constraint Logic：完全同你 run_demo 里的三种分支
        if is_pseudo:
            head_tags = ['VV', 'VA', 'NN']  # 幽默: 比较宽容
        elif is_mod:
            head_tags = ['NN', 'AD', 'JJ', 'VV']  # 小便/暂停: 允许名/形/动
        else:
            head_tags = ['VV']  # 吃饭/帮忙: 严格要求动词

        fst_split_rules.append({
            'lemma': lemma,
            'head': head,
            'tail': tail,
            'type': l_type,
            'allowed_head_tags': head_tags
        })

    return fst_split_rules
