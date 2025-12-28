# build_whole_fst.py
import hfst
from liheci_config import load_lexicon, build_whole_path, DEFAULT_INPUT_CSV

# 复用你之前作业里的 tokenizer 思路
tok = hfst.HfstTokenizer()
tok.add_multichar_symbol(hfst.EPSILON)

def string_to_fst(s: str) -> hfst.HfstTransducer:
    """
    把一个字符串变成 HFST acceptor。
    这里不编码输出，只要它能接受这个 surface form。
    """
    tokenized = tok.tokenize(s)
    fst = hfst.tokenized_fst(tokenized)
    return fst

def build_whole_lexicon_fst(csv_path: str = DEFAULT_INPUT_CSV,
                            out_path: str = "liheci_whole.hfst"):
    print(f"[HFST] Loading lexicon from {csv_path} ...")
    df = load_lexicon(csv_path)
    fst_whole_path = build_whole_path(df)

    print(f"[HFST] Building lexicon FST with {len(fst_whole_path)} surface forms ...")
    lexicon = hfst.HfstTransducer()
    for surf in fst_whole_path.keys():
        tr = string_to_fst(surf)
        lexicon.disjunct(tr)

    lexicon.minimize()

    print(f"[HFST] Writing to {out_path} ...")
    ostr = hfst.HfstOutputStream(filename=out_path)
    ostr.write(lexicon)
    ostr.flush()
    ostr.close()
    print("[HFST] Done.")

if __name__ == "__main__":
    build_whole_lexicon_fst()
